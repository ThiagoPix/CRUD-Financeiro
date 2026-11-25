from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Organizacao, Perfil

from .models import Categoria, Conta, Lancamento, Orcamento


def criar_org(nome, usuario, papel="admin"):
    org = Organizacao.objects.create(nome=nome)
    user = User.objects.create_user(usuario, password="senha-teste-123")
    Perfil.objects.create(usuario=user, organizacao=org, papel=papel)
    conta = Conta.objects.create(organizacao=org, nome="Carteira", tipo="carteira")
    despesa = Categoria.objects.create(organizacao=org, nome="Mercado", tipo="despesa")
    lancamento = Lancamento.objects.create(
        organizacao=org, descricao=f"Compra {nome}", conta=conta, categoria=despesa,
        valor_total=Decimal("100.00"), data=date(2026, 1, 10), primeiro_vencimento=date(2026, 1, 10),
        quantidade_parcelas=1,
    )
    orcamento = Orcamento.objects.create(organizacao=org, categoria=despesa, mes=1, ano=2026, limite=Decimal("500.00"))
    return {"org": org, "user": user, "conta": conta, "categoria": despesa, "lancamento": lancamento, "orcamento": orcamento}


class IsolamentoTest(TestCase):
    def setUp(self):
        self.a = criar_org("Org A", "ana")
        self.b = criar_org("Org B", "bruno")
        self.client.force_login(self.a["user"])

    def test_lista_mostra_so_a_propria_organizacao(self):
        resposta = self.client.get(reverse("financas:lancamento_lista"))
        self.assertContains(resposta, "Compra Org A")
        self.assertNotContains(resposta, "Compra Org B")

    def test_id_de_outra_organizacao_retorna_404(self):
        for nome, objeto in (("lancamento_detalhe", "lancamento"), ("lancamento_editar", "lancamento"),
                             ("conta_editar", "conta"), ("categoria_excluir", "categoria"),
                             ("orcamento_editar", "orcamento")):
            with self.subTest(rota=nome):
                url = reverse(f"financas:{nome}", args=[self.b[objeto].pk])
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_parcela_de_outra_organizacao_retorna_404(self):
        from .services import salvar_lancamento  # noqa: F401
        parcela = self.b["lancamento"].parcelas.first()
        if parcela is None:
            from .models import Parcela
            parcela = Parcela.objects.create(
                lancamento=self.b["lancamento"], numero=1, valor=Decimal("100.00"), vencimento=date(2026, 1, 10)
            )
        resposta = self.client.get(reverse("financas:parcela_editar", args=[parcela.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_criacao_grava_a_organizacao_do_usuario(self):
        resposta = self.client.post(reverse("financas:conta_criar"), {"nome": "Banco", "tipo": "corrente"})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(Conta.objects.get(nome="Banco").organizacao, self.a["org"])

    def test_formulario_nao_aceita_organizacao_enviada_pelo_usuario(self):
        self.client.post(reverse("financas:conta_criar"), {
            "nome": "Invasora", "tipo": "corrente", "organizacao": self.b["org"].pk,
        })
        self.assertEqual(Conta.objects.get(nome="Invasora").organizacao, self.a["org"])

    def test_selects_do_formulario_so_tem_opcoes_da_propria_organizacao(self):
        resposta = self.client.get(reverse("financas:lancamento_criar"))
        form = resposta.context["form"]
        self.assertEqual(list(form.fields["conta"].queryset), [self.a["conta"]])
        self.assertEqual(list(form.fields["categoria"].queryset), [self.a["categoria"]])

    def test_lancamento_com_conta_de_outra_organizacao_e_recusado(self):
        resposta = self.client.post(reverse("financas:lancamento_criar"), {
            "descricao": "Fraude", "conta": self.b["conta"].pk, "categoria": self.a["categoria"].pk,
            "valor_total": "10.00", "data": "2026-02-01", "primeiro_vencimento": "2026-02-01",
            "quantidade_parcelas": 1,
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Lancamento.objects.filter(descricao="Fraude").exists())

    def test_nome_pode_repetir_em_outra_organizacao_mas_nao_na_mesma(self):
        # "Carteira" ja existe nas duas organizacoes (criado no setUp)
        resposta = self.client.post(reverse("financas:conta_criar"), {"nome": "Carteira", "tipo": "carteira"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Conta.objects.filter(organizacao=self.a["org"], nome="Carteira").count(), 1)
        self.assertEqual(Conta.objects.filter(nome="Carteira").count(), 2)

    def test_orcamento_duplicado_na_mesma_organizacao_e_recusado(self):
        resposta = self.client.post(reverse("financas:orcamento_criar"), {
            "categoria": self.a["categoria"].pk, "mes": 1, "ano": 2026, "limite": "10.00",
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Orcamento.objects.filter(organizacao=self.a["org"]).count(), 1)

    def test_usuario_sem_perfil_recebe_403(self):
        sem_perfil = User.objects.create_user("solto", password="senha-teste-123")
        self.client.force_login(sem_perfil)
        self.assertEqual(self.client.get(reverse("financas:lancamento_lista")).status_code, 403)

    def test_anonimo_vai_para_o_login(self):
        self.client.logout()
        resposta = self.client.get(reverse("financas:lancamento_lista"))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/entrar/", resposta["Location"])


class PapeisTest(TestCase):
    def setUp(self):
        self.admin = criar_org("Org Papeis", "adm")
        self.operador = User.objects.create_user("op", password="senha-teste-123")
        Perfil.objects.create(usuario=self.operador, organizacao=self.admin["org"], papel="operador")

    def rotas_restritas(self):
        a = self.admin
        return [
            reverse("financas:conta_criar"), reverse("financas:conta_editar", args=[a["conta"].pk]),
            reverse("financas:conta_excluir", args=[a["conta"].pk]),
            reverse("financas:categoria_criar"), reverse("financas:categoria_editar", args=[a["categoria"].pk]),
            reverse("financas:categoria_excluir", args=[a["categoria"].pk]),
            reverse("financas:orcamento_criar"), reverse("financas:orcamento_editar", args=[a["orcamento"].pk]),
            reverse("financas:orcamento_excluir", args=[a["orcamento"].pk]),
            reverse("financas:lancamento_excluir", args=[a["lancamento"].pk]),
        ]

    def test_operador_recebe_403_nas_rotas_de_administrador(self):
        self.client.force_login(self.operador)
        for url in self.rotas_restritas():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_administrador_acessa_as_rotas_restritas(self):
        self.client.force_login(self.admin["user"])
        for url in self.rotas_restritas():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_operador_cria_lancamento(self):
        self.client.force_login(self.operador)
        resposta = self.client.post(reverse("financas:lancamento_criar"), {
            "descricao": "Feito pelo operador", "conta": self.admin["conta"].pk,
            "categoria": self.admin["categoria"].pk, "valor_total": "30.00", "data": "2026-02-01",
            "primeiro_vencimento": "2026-02-01", "quantidade_parcelas": 1,
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Lancamento.objects.filter(descricao="Feito pelo operador", organizacao=self.admin["org"]).exists())

    def test_operador_nao_ve_botoes_de_administrador(self):
        self.client.force_login(self.operador)
        self.assertNotContains(self.client.get(reverse("financas:conta_lista")), "Nova conta")
        self.assertNotContains(self.client.get(reverse("financas:lancamento_lista")), "Excluir")

    def test_administrador_ve_os_botoes(self):
        self.client.force_login(self.admin["user"])
        self.assertContains(self.client.get(reverse("financas:conta_lista")), "Nova conta")
