from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Organizacao, Perfil

from .exportacao import neutralizar
from .models import Categoria, Conta, Lancamento
from .services import gravar_lancamento


def montar(nome, papel="admin"):
    org = Organizacao.objects.create(nome=nome)
    user = User.objects.create_user(f"u_{nome}", password="senha-teste-123")
    Perfil.objects.create(usuario=user, organizacao=org, papel=papel)
    conta = Conta.objects.create(organizacao=org, nome="Banco", tipo="corrente")
    receita = Categoria.objects.create(organizacao=org, nome="Vendas", tipo="receita")
    despesa = Categoria.objects.create(organizacao=org, nome="Fornecedor", tipo="despesa")
    return {"org": org, "user": user, "conta": conta, "receita": receita, "despesa": despesa}


def lancar(dados, categoria, valor, dia, descricao="Item", parcelas=1, pagas=0):
    """Cria o lançamento com suas parcelas e marca as `pagas` primeiras como pagas."""
    lancamento = gravar_lancamento(Lancamento(
        organizacao=dados["org"], descricao=descricao, conta=dados["conta"], categoria=dados[categoria],
        valor_total=Decimal(valor), data=dia, primeiro_vencimento=dia, quantidade_parcelas=parcelas,
    ))
    for parcela in lancamento.parcelas.all()[:pagas]:
        parcela.paga = True
        parcela.save(update_fields=["paga"])
    return lancamento


class DashboardTest(TestCase):
    def setUp(self):
        # Dados fáceis de conferir à mão.
        # A: receita 1000 paga (jan), despesa 300 paga (jan), despesa 200 pendente (fev). B: 5 x 50 pendentes.
        self.a = montar("A")
        self.b = montar("B")
        lancar(self.a, "receita", "1000.00", date(2026, 1, 10), pagas=1)
        lancar(self.a, "despesa", "300.00", date(2026, 1, 20), pagas=1)
        lancar(self.a, "despesa", "200.00", date(2026, 2, 5))
        for _ in range(5):
            lancar(self.b, "despesa", "50.00", date(2026, 1, 15))
        self.client.force_login(self.a["user"])

    def contexto(self, **parametros):
        return self.client.get(reverse("financas:dashboard"), parametros).context

    def test_fluxo_so_da_organizacao(self):
        fluxo = self.contexto()["fluxo"]
        self.assertEqual(fluxo["recebido"], Decimal("1000.00"))
        self.assertEqual(fluxo["pago"], Decimal("300.00"))
        self.assertEqual(fluxo["a_pagar"], Decimal("200.00"))
        self.assertEqual(fluxo["a_receber"], Decimal("0.00"))
        self.assertEqual(fluxo["lancamentos"], 3)

    def test_saldo_realizado_ignora_o_que_nao_foi_pago(self):
        fluxo = self.contexto()["fluxo"]
        self.assertEqual(fluxo["saldo_realizado"], Decimal("700.00"))
        self.assertEqual(fluxo["saldo_previsto"], Decimal("500.00"))

    def test_compra_parcelada_aparece_parcela_a_parcela(self):
        lancar(self.a, "despesa", "300.00", date(2026, 3, 1), descricao="Parcelada", parcelas=3, pagas=1)
        fluxo = self.contexto(inicio="2026-03-01", fim="2026-03-31")["fluxo"]
        self.assertEqual(fluxo["pago"], Decimal("100.00"))
        self.assertEqual(fluxo["a_pagar"], Decimal("0.00"))
        abril = self.contexto(inicio="2026-04-01", fim="2026-04-30")["fluxo"]
        self.assertEqual(abril["pago"], Decimal("0.00"))
        self.assertEqual(abril["a_pagar"], Decimal("100.00"))

    def test_ranking_e_distribuicao_so_da_organizacao(self):
        contexto = self.contexto()
        self.assertEqual(contexto["ranking"], [{"nome": "Fornecedor", "total": Decimal("500.00")}])
        self.assertEqual(contexto["por_conta"], [{"nome": "Banco", "total": Decimal("500.00")}])

    def test_periodo_filtra_por_vencimento(self):
        fluxo = self.contexto(inicio="2026-02-01", fim="2026-02-28")["fluxo"]
        self.assertEqual(fluxo["pago"], Decimal("0.00"))
        self.assertEqual(fluxo["a_pagar"], Decimal("200.00"))
        self.assertEqual(fluxo["lancamentos"], 1)

    def test_serie_mensal_ordenada_com_os_quatro_valores(self):
        serie = self.contexto()["serie"]
        meses = [item["mes"] for item in serie]
        self.assertEqual(meses, sorted(meses))
        self.assertEqual(len(serie), 2)
        self.assertEqual(serie[0]["recebido"], Decimal("1000.00"))
        self.assertEqual(serie[0]["pago"], Decimal("300.00"))
        self.assertEqual(serie[1]["a_pagar"], Decimal("200.00"))

    def test_periodo_invalido_nao_gera_erro_500(self):
        resposta = self.client.get(reverse("financas:dashboard"), {"inicio": "abc"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["fluxo"]["lancamentos"], 3)

    def test_fim_antes_do_inicio_mostra_erro(self):
        resposta = self.client.get(reverse("financas:dashboard"), {"inicio": "2026-03-01", "fim": "2026-01-01"})
        self.assertContains(resposta, "não pode ser anterior")

    def test_dashboard_vazio_funciona(self):
        vazia = montar("Vazia")
        self.client.force_login(vazia["user"])
        resposta = self.client.get(reverse("financas:dashboard"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["fluxo"]["lancamentos"], 0)
        self.assertContains(resposta, "Sem despesas no período.")

    def test_numero_de_consultas_nao_cresce_com_os_dados(self):
        # 4 de sessão/usuário/perfil/organização + 8 métricas (fluxo, 2 rankings, por conta, série, saldos, 2 de orçamento) + 1 da equipe (só administrador); não depende da quantidade de lançamentos
        with self.assertNumQueries(13):
            self.client.get(reverse("financas:dashboard"))
        for _ in range(20):
            lancar(self.a, "despesa", "10.00", date(2026, 4, 1))
        with self.assertNumQueries(13):
            self.client.get(reverse("financas:dashboard"))

    def test_operador_nao_ve_serie_nem_grafico(self):
        operador = User.objects.create_user("op_a", password="senha-teste-123")
        Perfil.objects.create(usuario=operador, organizacao=self.a["org"], papel="operador")
        self.client.force_login(operador)
        resposta = self.client.get(reverse("financas:dashboard"))
        self.assertNotContains(resposta, "Mês a mês")
        self.assertNotContains(resposta, "grafico-fluxo")
        self.assertNotContains(resposta, "grafico-previsao")
        self.assertNotContains(resposta, "saldo_acumulado")

    def test_administrador_ve_o_grafico(self):
        resposta = self.client.get(reverse("financas:dashboard"))
        self.assertContains(resposta, "grafico-fluxo")
        self.assertContains(resposta, 'id="dados-graficos"')


class GraficosDoDashboardTest(TestCase):
    def setUp(self):
        self.a = montar("A")
        self.client.force_login(self.a["user"])
        lancar(self.a, "receita", "1000.00", date(2026, 1, 10), pagas=1)
        lancar(self.a, "despesa", "300.00", date(2026, 1, 20), pagas=1)
        lancar(self.a, "despesa", "200.00", date(2026, 2, 5))
        lancar(self.a, "receita", "400.00", date(2026, 2, 6))

    def graficos(self, **parametros):
        return self.client.get(reverse("financas:dashboard"), parametros).context["graficos"]

    def test_administrador_recebe_os_sete_conjuntos_de_dados(self):
        graficos = self.graficos()
        for chave in ("fluxo", "previsao", "despesas_categoria", "receitas_categoria", "despesas_conta", "contas", "orcamentos"):
            self.assertIn(chave, graficos)

    def test_operador_nao_recebe_fluxo_nem_previsao(self):
        operador = User.objects.create_user("op_g", password="senha-teste-123")
        Perfil.objects.create(usuario=operador, organizacao=self.a["org"], papel="operador")
        self.client.force_login(operador)
        graficos = self.graficos()
        self.assertNotIn("fluxo", graficos)
        self.assertNotIn("previsao", graficos)
        self.assertIn("despesas_categoria", graficos)

    def test_fluxo_tem_saldo_realizado_acumulado(self):
        fluxo = self.graficos()["fluxo"]
        self.assertEqual([i["mes"] for i in fluxo], ["01/2026", "02/2026"])
        self.assertEqual(fluxo[0]["saldo_acumulado"], 700.0)
        self.assertEqual(fluxo[1]["saldo_acumulado"], 700.0)  # fevereiro nao tem nada pago

    def test_previsao_so_tem_meses_com_pendencia(self):
        previsao = self.graficos()["previsao"]
        self.assertEqual(previsao, [{"mes": "02/2026", "a_receber": 400.0, "a_pagar": 200.0}])

    def test_ranking_de_receitas_soma_recebido_e_a_receber(self):
        receitas = self.client.get(reverse("financas:dashboard")).context["receitas"]
        self.assertEqual(receitas, [{"nome": "Vendas", "total": Decimal("1400.00")}])

    def test_orcamento_do_mes_usa_so_parcelas_pagas(self):
        from .models import Orcamento
        despesa = self.a["despesa"]
        Orcamento.objects.create(organizacao=self.a["org"], categoria=despesa, mes=1, ano=2026, limite=Decimal("250.00"))
        contexto = self.client.get(reverse("financas:dashboard"), {"fim": "2026-01-31"}).context
        item = contexto["orcamentos"][0]
        self.assertEqual(item["gasto"], Decimal("300.00"))
        self.assertTrue(item["excedido"])
        self.assertEqual(item["percentual"], Decimal("120.0"))
        self.assertEqual(self.graficos(fim="2026-01-31")["orcamentos"], [{"nome": "Fornecedor", "limite": 250.0, "gasto": 300.0}])

    def test_orcamentos_de_outra_organizacao_nao_aparecem(self):
        from .models import Orcamento
        outra = montar("B")
        Orcamento.objects.create(organizacao=outra["org"], categoria=outra["despesa"], mes=1, ano=2026, limite=Decimal("10.00"))
        self.assertEqual(self.client.get(reverse("financas:dashboard"), {"fim": "2026-01-31"}).context["orcamentos"], [])

    def test_pagina_do_administrador_tem_todos_os_canvases(self):
        from django.utils import timezone

        from .models import Orcamento
        hoje = timezone.localdate()
        Orcamento.objects.create(organizacao=self.a["org"], categoria=self.a["despesa"], mes=hoje.month, ano=hoje.year, limite=Decimal("250.00"))
        pagina = self.client.get(reverse("financas:dashboard"))
        for canvas in ("grafico-fluxo", "grafico-previsao", "grafico-despesas-categoria", "grafico-receitas-categoria",
                       "grafico-despesas-conta", "grafico-saldo-contas", "grafico-orcamentos"):
            self.assertContains(pagina, f'id="{canvas}"')

    def test_nenhum_grafico_de_pizza(self):
        import pathlib
        codigo = (pathlib.Path(__file__).parent / "static" / "financas" / "dashboard.js").read_text(encoding="utf-8")
        for proibido in ('"pie"', '"doughnut"', '"polarArea"'):
            self.assertNotIn(proibido, codigo)


class ExportacaoCsvTest(TestCase):
    def setUp(self):
        self.a = montar("A")
        lancar(self.a, "despesa", "300.00", date(2026, 1, 20), descricao="=HYPERLINK(1)", pagas=1)
        lancar(self.a, "receita", "100.00", date(2026, 3, 1), descricao="Normal")
        self.client.force_login(self.a["user"])

    def test_admin_baixa_csv_de_parcelas_com_formula_neutralizada(self):
        resposta = self.client.get(reverse("financas:dashboard_exportar"))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("text/csv", resposta["Content-Type"])
        texto = resposta.content.decode("utf-8")
        self.assertIn("'=HYPERLINK(1)", texto)
        self.assertIn("300,00", texto)
        self.assertIn("Paga", texto)
        self.assertIn("Pendente", texto)
        self.assertIn("1/1", texto)

    def test_csv_respeita_periodo_e_organizacao(self):
        outra = montar("Outra")
        lancar(outra, "despesa", "999.00", date(2026, 3, 1), descricao="Da outra org")
        texto = self.client.get(reverse("financas:dashboard_exportar"), {"inicio": "2026-03-01"}).content.decode("utf-8")
        self.assertIn("Normal", texto)
        self.assertNotIn("HYPERLINK", texto)
        self.assertNotIn("Da outra org", texto)

    def test_operador_recebe_403(self):
        operador = User.objects.create_user("op_csv", password="senha-teste-123")
        Perfil.objects.create(usuario=operador, organizacao=self.a["org"], papel="operador")
        self.client.force_login(operador)
        self.assertEqual(self.client.get(reverse("financas:dashboard_exportar")).status_code, 403)

    def test_periodo_invalido_retorna_400(self):
        self.assertEqual(self.client.get(reverse("financas:dashboard_exportar"), {"inicio": "abc"}).status_code, 400)

    def test_neutralizar(self):
        for perigoso in ("=1+1", "+1", "-1", "@SOMA"):
            self.assertEqual(neutralizar(perigoso), "'" + perigoso)
        self.assertEqual(neutralizar("Mercado"), "Mercado")


class ApiDashboardTest(TestCase):
    def setUp(self):
        self.a = montar("A")
        self.b = montar("B")
        lancar(self.a, "receita", "1000.00", date(2026, 1, 10), pagas=1)
        lancar(self.b, "despesa", "50.00", date(2026, 1, 15))

    def test_anonimo_recebe_403(self):
        self.assertEqual(self.client.get(reverse("api_dashboard")).status_code, 403)

    def test_fluxo_so_da_organizacao(self):
        self.client.force_login(self.a["user"])
        fluxo = self.client.get(reverse("api_dashboard")).json()["fluxo"]
        self.assertEqual(fluxo["lancamentos"], 1)
        self.assertEqual(fluxo["recebido"], 1000.0)
        self.assertEqual(fluxo["pago"], 0)
        self.assertEqual(fluxo["a_pagar"], 0)

    def test_operador_nao_recebe_serie(self):
        operador = User.objects.create_user("op_api", password="senha-teste-123")
        Perfil.objects.create(usuario=operador, organizacao=self.a["org"], papel="operador")
        self.client.force_login(operador)
        dados = self.client.get(reverse("api_dashboard")).json()
        self.assertNotIn("serie", dados)
        self.client.force_login(self.a["user"])
        self.assertIn("serie", self.client.get(reverse("api_dashboard")).json())

    def test_periodo_invalido_retorna_400(self):
        self.client.force_login(self.a["user"])
        self.assertEqual(self.client.get(reverse("api_dashboard"), {"inicio": "abc"}).status_code, 400)
