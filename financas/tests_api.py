from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Organizacao, Perfil

from .models import Categoria, Conta


def usuario(org, nome, papel):
    user = User.objects.create_user(nome, password="senha-teste-123")
    Perfil.objects.create(usuario=user, organizacao=org, papel=papel)
    return user


class ApiContasCategoriasTest(TestCase):
    def setUp(self):
        self.org_a = Organizacao.objects.create(nome="A")
        self.org_b = Organizacao.objects.create(nome="B")
        self.admin_a = usuario(self.org_a, "admin_a", "admin")
        self.operador_a = usuario(self.org_a, "op_a", "operador")
        self.conta_a = Conta.objects.create(organizacao=self.org_a, nome="Carteira", tipo="carteira")
        self.conta_b = Conta.objects.create(organizacao=self.org_b, nome="Banco B", tipo="corrente")
        self.categoria_a = Categoria.objects.create(organizacao=self.org_a, nome="Mercado", tipo="despesa")

    def test_anonimo_recebe_403(self):
        self.assertEqual(self.client.get(reverse("api_conta_lista")).status_code, 403)

    def test_lista_so_da_propria_organizacao(self):
        self.client.force_login(self.operador_a)
        resposta = self.client.get(reverse("api_conta_lista"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([c["nome"] for c in resposta.json()], ["Carteira"])

    def test_detalhe_de_outra_organizacao_retorna_404(self):
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.get(reverse("api_conta_detalhe", args=[self.conta_b.pk])).status_code, 404)

    def test_admin_cria_com_a_organizacao_do_usuario(self):
        self.client.force_login(self.admin_a)
        resposta = self.client.post(reverse("api_conta_lista"), {"nome": "Poupanca", "tipo": "poupanca"}, content_type="application/json")
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(Conta.objects.get(nome="Poupanca").organizacao, self.org_a)

    def test_organizacao_enviada_no_json_e_ignorada(self):
        self.client.force_login(self.admin_a)
        self.client.post(reverse("api_conta_lista"), {"nome": "X", "tipo": "carteira", "organizacao": self.org_b.pk}, content_type="application/json")
        self.assertEqual(Conta.objects.get(nome="X").organizacao, self.org_a)

    def test_operador_nao_escreve(self):
        self.client.force_login(self.operador_a)
        resposta = self.client.post(reverse("api_conta_lista"), {"nome": "Y", "tipo": "carteira"}, content_type="application/json")
        self.assertEqual(resposta.status_code, 403)

    def test_nome_duplicado_na_organizacao_retorna_400(self):
        self.client.force_login(self.admin_a)
        resposta = self.client.post(reverse("api_conta_lista"), {"nome": "Carteira", "tipo": "carteira"}, content_type="application/json")
        self.assertEqual(resposta.status_code, 400)

    def test_mesmo_nome_em_outra_organizacao_e_permitido(self):
        self.client.force_login(self.admin_a)
        resposta = self.client.post(reverse("api_conta_lista"), {"nome": "Banco B", "tipo": "corrente"}, content_type="application/json")
        self.assertEqual(resposta.status_code, 201)

    def test_nao_troca_tipo_de_categoria_com_lancamentos(self):
        from datetime import date
        from decimal import Decimal
        from .models import Lancamento
        Lancamento.objects.create(
            organizacao=self.org_a, descricao="x", conta=self.conta_a, categoria=self.categoria_a,
            valor_total=Decimal("10"), data=date(2026, 1, 1), primeiro_vencimento=date(2026, 1, 1),
        )
        self.client.force_login(self.admin_a)
        resposta = self.client.patch(reverse("api_categoria_detalhe", args=[self.categoria_a.pk]), {"tipo": "receita"}, content_type="application/json")
        self.assertEqual(resposta.status_code, 400)

    def test_exclusao_de_categoria_em_uso_retorna_400(self):
        from datetime import date
        from decimal import Decimal
        from .models import Lancamento
        Lancamento.objects.create(
            organizacao=self.org_a, descricao="x", conta=self.conta_a, categoria=self.categoria_a,
            valor_total=Decimal("10"), data=date(2026, 1, 1), primeiro_vencimento=date(2026, 1, 1),
        )
        self.client.force_login(self.admin_a)
        resposta = self.client.delete(reverse("api_categoria_detalhe", args=[self.categoria_a.pk]))
        self.assertEqual(resposta.status_code, 400)
