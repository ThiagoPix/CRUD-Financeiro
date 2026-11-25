from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Organizacao, Perfil

from .models import Categoria, Conta, Lancamento, Orcamento


def montar(nome, papel="admin"):
    org = Organizacao.objects.create(nome=nome)
    user = User.objects.create_user(f"user_{nome}", password="senha-teste-123")
    Perfil.objects.create(usuario=user, organizacao=org, papel=papel)
    conta = Conta.objects.create(organizacao=org, nome="Carteira", tipo="carteira")
    despesa = Categoria.objects.create(organizacao=org, nome="Mercado", tipo="despesa")
    return org, user, conta, despesa


def corpo(conta, categoria, **extra):
    dados = {
        "descricao": "Compra", "conta": conta.pk, "categoria": categoria.pk, "valor_total": "90.00",
        "data": "2026-03-01", "primeiro_vencimento": "2026-03-01", "quantidade_parcelas": 3,
    }
    dados.update(extra)
    return dados


class ApiLancamentosTest(TestCase):
    def setUp(self):
        self.org_a, self.admin_a, self.conta_a, self.cat_a = montar("A")
        self.org_b, self.admin_b, self.conta_b, self.cat_b = montar("B")
        self.operador = User.objects.create_user("op_a", password="senha-teste-123")
        Perfil.objects.create(usuario=self.operador, organizacao=self.org_a, papel="operador")
        self.client.force_login(self.admin_a)

    def criar(self, **extra):
        return self.client.post(reverse("api_lancamento_lista"), corpo(self.conta_a, self.cat_a, **extra), content_type="application/json")

    def test_cria_lancamento_e_gera_parcelas(self):
        resposta = self.criar()
        self.assertEqual(resposta.status_code, 201, resposta.content)
        dados = resposta.json()
        self.assertEqual(len(dados["parcelas"]), 3)
        self.assertEqual(sum(Decimal(p["valor"]) for p in dados["parcelas"]), Decimal("90.00"))
        self.assertEqual(Lancamento.objects.get().organizacao, self.org_a)

    def test_valor_zero_retorna_400(self):
        resposta = self.criar(valor_total="0")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("valor_total", resposta.json())

    def test_conta_de_outra_organizacao_retorna_400(self):
        resposta = self.client.post(reverse("api_lancamento_lista"), corpo(self.conta_b, self.cat_a), content_type="application/json")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("conta", resposta.json())

    def test_vencimento_antes_da_data_retorna_400(self):
        resposta = self.criar(primeiro_vencimento="2026-02-01")
        self.assertEqual(resposta.status_code, 400)

    def test_lista_so_da_propria_organizacao_e_busca(self):
        self.criar(descricao="Mercado do mes")
        self.criar(descricao="Aluguel")
        Lancamento.objects.create(
            organizacao=self.org_b, descricao="Mercado de B", conta=self.conta_b, categoria=self.cat_b,
            valor_total=Decimal("10"), data=date(2026, 1, 1), primeiro_vencimento=date(2026, 1, 1),
        )
        todos = self.client.get(reverse("api_lancamento_lista")).json()
        self.assertEqual(len(todos), 2)
        achados = self.client.get(reverse("api_lancamento_lista"), {"q": "mercado"}).json()
        self.assertEqual([i["descricao"] for i in achados], ["Mercado do mes"])

    def test_detalhe_de_outra_organizacao_retorna_404(self):
        outro = Lancamento.objects.create(
            organizacao=self.org_b, descricao="De B", conta=self.conta_b, categoria=self.cat_b,
            valor_total=Decimal("10"), data=date(2026, 1, 1), primeiro_vencimento=date(2026, 1, 1),
        )
        self.assertEqual(self.client.get(reverse("api_lancamento_detalhe", args=[outro.pk])).status_code, 404)

    def test_operador_cria_mas_nao_exclui(self):
        self.client.force_login(self.operador)
        resposta = self.criar()
        self.assertEqual(resposta.status_code, 201)
        url = reverse("api_lancamento_detalhe", args=[resposta.json()["id"]])
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_marcar_parcela_como_paga_e_bloquear_exclusao(self):
        criado = self.criar().json()
        parcela_id = criado["parcelas"][0]["id"]
        resposta = self.client.patch(reverse("api_parcela_detalhe", args=[parcela_id]), {"paga": True}, content_type="application/json")
        self.assertEqual(resposta.status_code, 200)
        excluir = self.client.delete(reverse("api_lancamento_detalhe", args=[criado["id"]]))
        self.assertEqual(excluir.status_code, 400)

    def test_parcela_de_outra_organizacao_retorna_404(self):
        self.client.force_login(self.admin_b)
        criado = self.client.post(reverse("api_lancamento_lista"), corpo(self.conta_b, self.cat_b), content_type="application/json").json()
        self.client.force_login(self.admin_a)
        url = reverse("api_parcela_detalhe", args=[criado["parcelas"][0]["id"]])
        self.assertEqual(self.client.get(url).status_code, 404)


class ApiOrcamentosTest(TestCase):
    def setUp(self):
        self.org, self.admin, self.conta, self.despesa = montar("O")
        self.receita = Categoria.objects.create(organizacao=self.org, nome="Salario", tipo="receita")
        self.operador = User.objects.create_user("op_o", password="senha-teste-123")
        Perfil.objects.create(usuario=self.operador, organizacao=self.org, papel="operador")
        self.client.force_login(self.admin)

    def post(self, **extra):
        dados = {"categoria": self.despesa.pk, "mes": 3, "ano": 2026, "limite": "500.00"}
        dados.update(extra)
        return self.client.post(reverse("api_orcamento_lista"), dados, content_type="application/json")

    def test_admin_cria_orcamento_com_resumo(self):
        resposta = self.post()
        self.assertEqual(resposta.status_code, 201, resposta.content)
        self.assertEqual(resposta.json()["resumo"]["disponivel"], "500.00")
        self.assertEqual(Orcamento.objects.get().organizacao, self.org)

    def test_categoria_de_receita_retorna_400(self):
        self.assertEqual(self.post(categoria=self.receita.pk).status_code, 400)

    def test_duplicado_retorna_400(self):
        self.post()
        self.assertEqual(self.post().status_code, 400)

    def test_operador_so_le(self):
        self.client.force_login(self.operador)
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(self.client.get(reverse("api_orcamento_lista")).status_code, 200)
