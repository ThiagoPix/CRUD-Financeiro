from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Organizacao, Perfil

from .exportacao import neutralizar
from .models import Categoria, Conta, Lancamento


def montar(nome, papel="admin"):
    org = Organizacao.objects.create(nome=nome)
    user = User.objects.create_user(f"u_{nome}", password="senha-teste-123")
    Perfil.objects.create(usuario=user, organizacao=org, papel=papel)
    conta = Conta.objects.create(organizacao=org, nome="Banco", tipo="corrente")
    receita = Categoria.objects.create(organizacao=org, nome="Vendas", tipo="receita")
    despesa = Categoria.objects.create(organizacao=org, nome="Fornecedor", tipo="despesa")
    return {"org": org, "user": user, "conta": conta, "receita": receita, "despesa": despesa}


def lancar(dados, categoria, valor, dia, descricao="Item"):
    return Lancamento.objects.create(
        organizacao=dados["org"], descricao=descricao, conta=dados["conta"], categoria=dados[categoria],
        valor_total=Decimal(valor), data=dia, primeiro_vencimento=dia, quantidade_parcelas=1,
    )


class DashboardTest(TestCase):
    def setUp(self):
        # dados faceis de conferir a mao: A tem 3 lancamentos, B tem 5
        self.a = montar("A")
        self.b = montar("B")
        lancar(self.a, "receita", "1000.00", date(2026, 1, 10))
        lancar(self.a, "despesa", "300.00", date(2026, 1, 20))
        lancar(self.a, "despesa", "200.00", date(2026, 2, 5))
        for _ in range(5):
            lancar(self.b, "despesa", "50.00", date(2026, 1, 15))
        self.client.force_login(self.a["user"])

    def test_totais_so_da_organizacao(self):
        contexto = self.client.get(reverse("financas:dashboard")).context
        self.assertEqual(contexto["totais"]["quantidade"], 3)
        self.assertEqual(contexto["totais"]["receitas"], Decimal("1000.00"))
        self.assertEqual(contexto["totais"]["despesas"], Decimal("500.00"))
        self.assertEqual(contexto["totais"]["saldo"], Decimal("500.00"))

    def test_ranking_e_distribuicao_so_da_organizacao(self):
        contexto = self.client.get(reverse("financas:dashboard")).context
        self.assertEqual(contexto["ranking"], [{"categoria__nome": "Fornecedor", "total": Decimal("500.00")}])
        self.assertEqual(contexto["por_conta"], [{"conta__nome": "Banco", "total": Decimal("500.00")}])

    def test_periodo_filtra(self):
        contexto = self.client.get(reverse("financas:dashboard"), {"inicio": "2026-02-01", "fim": "2026-02-28"}).context
        self.assertEqual(contexto["totais"]["quantidade"], 1)
        self.assertEqual(contexto["totais"]["despesas"], Decimal("200.00"))

    def test_serie_mensal_ordenada(self):
        meses = [item["mes"] for item in self.client.get(reverse("financas:dashboard")).context["serie"]]
        self.assertEqual(meses, sorted(meses))
        self.assertEqual(len(meses), 2)

    def test_periodo_invalido_nao_gera_erro_500(self):
        resposta = self.client.get(reverse("financas:dashboard"), {"inicio": "abc"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["totais"]["quantidade"], 3)

    def test_fim_antes_do_inicio_mostra_erro(self):
        resposta = self.client.get(reverse("financas:dashboard"), {"inicio": "2026-03-01", "fim": "2026-01-01"})
        self.assertContains(resposta, "não pode ser anterior")

    def test_dashboard_vazio_funciona(self):
        vazia = montar("Vazia")
        self.client.force_login(vazia["user"])
        resposta = self.client.get(reverse("financas:dashboard"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["totais"]["quantidade"], 0)
        self.assertContains(resposta, "Sem despesas no período.")

    def test_numero_de_consultas_nao_cresce_com_os_dados(self):
        # 4 de sessao/usuario/perfil/organizacao + 5 metricas; nao depende da quantidade de lancamentos
        with self.assertNumQueries(9):
            self.client.get(reverse("financas:dashboard"))
        for _ in range(20):
            lancar(self.a, "despesa", "10.00", date(2026, 4, 1))
        with self.assertNumQueries(9):
            self.client.get(reverse("financas:dashboard"))

    def test_operador_nao_ve_serie_nem_grafico(self):
        operador = User.objects.create_user("op_a", password="senha-teste-123")
        Perfil.objects.create(usuario=operador, organizacao=self.a["org"], papel="operador")
        self.client.force_login(operador)
        resposta = self.client.get(reverse("financas:dashboard"))
        self.assertNotContains(resposta, "Mês a mês")
        self.assertNotContains(resposta, "grafico-mensal")

    def test_administrador_ve_o_grafico(self):
        resposta = self.client.get(reverse("financas:dashboard"))
        self.assertContains(resposta, "grafico-mensal")
        self.assertContains(resposta, 'id="dados-mensais"')


class ExportacaoCsvTest(TestCase):
    def setUp(self):
        self.a = montar("A")
        lancar(self.a, "despesa", "300.00", date(2026, 1, 20), descricao="=HYPERLINK(1)")
        lancar(self.a, "receita", "100.00", date(2026, 3, 1), descricao="Normal")
        self.client.force_login(self.a["user"])

    def test_admin_baixa_csv_com_formula_neutralizada(self):
        resposta = self.client.get(reverse("financas:dashboard_exportar"))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("text/csv", resposta["Content-Type"])
        texto = resposta.content.decode("utf-8")
        self.assertIn("'=HYPERLINK(1)", texto)
        self.assertIn("300,00", texto)

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
        lancar(self.a, "receita", "1000.00", date(2026, 1, 10))
        lancar(self.b, "despesa", "50.00", date(2026, 1, 15))

    def test_anonimo_recebe_403(self):
        self.assertEqual(self.client.get(reverse("api_dashboard")).status_code, 403)

    def test_totais_so_da_organizacao(self):
        self.client.force_login(self.a["user"])
        dados = self.client.get(reverse("api_dashboard")).json()
        self.assertEqual(dados["totais"]["quantidade"], 1)
        self.assertEqual(dados["totais"]["receitas"], 1000.0)
        self.assertEqual(dados["totais"]["despesas"], 0)

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
