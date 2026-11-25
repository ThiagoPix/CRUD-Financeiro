from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import Organizacao, Perfil

SENHA = "SenhaForte#2026"


def membro(org, nome, papel):
    usuario = User.objects.create_user(nome, password=SENHA)
    return Perfil.objects.create(usuario=usuario, organizacao=org, papel=papel)


def json(cliente, metodo, url, dados=None):
    return getattr(cliente, metodo)(url, dados, content_type="application/json") if dados is not None else getattr(cliente, metodo)(url)


class ApiOrganizacaoEEquipeTest(TestCase):
    def setUp(self):
        self.org = Organizacao.objects.create(nome="A")
        self.outra = Organizacao.objects.create(nome="B")
        self.admin = membro(self.org, "admin_a", "admin")
        self.operador = membro(self.org, "op_a", "operador")
        self.de_outra = membro(self.outra, "admin_b", "admin")
        self.client.force_login(self.admin.usuario)

    # --- organizacao
    def test_organizacao_devolve_a_propria_com_numero_de_membros(self):
        dados = self.client.get(reverse("api_organizacao")).json()
        self.assertEqual(dados["nome"], "A")
        self.assertEqual(dados["membros"], 2)

    def test_operador_ve_a_organizacao_mas_anonimo_nao(self):
        self.client.force_login(self.operador.usuario)
        self.assertEqual(self.client.get(reverse("api_organizacao")).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("api_organizacao")).status_code, 403)

    # --- equipe: acesso
    def test_equipe_so_para_administrador(self):
        self.client.force_login(self.operador.usuario)
        self.assertEqual(self.client.get(reverse("api_equipe_lista")).status_code, 403)
        self.assertEqual(json(self.client, "post", reverse("api_equipe_lista"), {"usuario": "x", "senha": SENHA}).status_code, 403)
        self.assertEqual(self.client.get(reverse("api_equipe_detalhe", args=[self.admin.pk])).status_code, 403)

    def test_lista_so_a_propria_equipe_sem_expor_senha(self):
        dados = self.client.get(reverse("api_equipe_lista")).json()
        self.assertEqual([m["usuario"] for m in dados], ["admin_a", "op_a"])
        self.assertTrue(all(set(m) == {"id", "usuario", "papel"} for m in dados))

    # --- equipe: criar
    def test_cria_membro_na_organizacao_do_administrador(self):
        resposta = json(self.client, "post", reverse("api_equipe_lista"), {"usuario": "novo", "senha": SENHA, "papel": "operador", "organizacao": self.outra.pk})
        self.assertEqual(resposta.status_code, 201, resposta.content)
        self.assertEqual(resposta.json()["usuario"], "novo")
        self.assertNotIn("senha", resposta.json())
        self.assertEqual(Perfil.objects.get(usuario__username="novo").organizacao, self.org)

    def test_papel_padrao_e_operador(self):
        json(self.client, "post", reverse("api_equipe_lista"), {"usuario": "novo", "senha": SENHA})
        self.assertEqual(Perfil.objects.get(usuario__username="novo").papel, "operador")

    def test_criar_recusa_senha_fraca_e_usuario_repetido(self):
        fraca = json(self.client, "post", reverse("api_equipe_lista"), {"usuario": "novo", "senha": "12345678"})
        repetido = json(self.client, "post", reverse("api_equipe_lista"), {"usuario": "op_a", "senha": SENHA})
        self.assertEqual(fraca.status_code, 400)
        self.assertIn("senha", fraca.json())
        self.assertEqual(repetido.status_code, 400)
        self.assertIn("usuario", repetido.json())

    def test_criar_recusa_papel_invalido(self):
        resposta = json(self.client, "post", reverse("api_equipe_lista"), {"usuario": "novo", "senha": SENHA, "papel": "dono"})
        self.assertEqual(resposta.status_code, 400)

    # --- equipe: detalhe
    def test_altera_papel_por_patch(self):
        resposta = json(self.client, "patch", reverse("api_equipe_detalhe", args=[self.operador.pk]), {"papel": "admin"})
        self.assertEqual(resposta.status_code, 200)
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.papel, "admin")

    def test_nao_rebaixa_o_ultimo_administrador(self):
        resposta = json(self.client, "patch", reverse("api_equipe_detalhe", args=[self.admin.pk]), {"papel": "operador"})
        self.assertEqual(resposta.status_code, 400)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.papel, "admin")

    def test_put_nao_e_permitido(self):
        resposta = json(self.client, "put", reverse("api_equipe_detalhe", args=[self.operador.pk]), {"papel": "admin"})
        self.assertEqual(resposta.status_code, 405)

    def test_detalhe_de_outra_organizacao_retorna_404(self):
        url = reverse("api_equipe_detalhe", args=[self.de_outra.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(json(self.client, "patch", url, {"papel": "operador"}).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertTrue(User.objects.filter(username="admin_b").exists())

    def test_remove_membro(self):
        resposta = self.client.delete(reverse("api_equipe_detalhe", args=[self.operador.pk]))
        self.assertEqual(resposta.status_code, 204)
        self.assertFalse(User.objects.filter(username="op_a").exists())

    def test_nao_remove_a_si_mesmo(self):
        resposta = self.client.delete(reverse("api_equipe_detalhe", args=[self.admin.pk]))
        self.assertEqual(resposta.status_code, 400)
        self.assertTrue(User.objects.filter(username="admin_a").exists())


class ApiCadastroTest(TestCase):
    def setUp(self):
        cache.clear()  # o limite de tentativas usa o cache

    def cadastrar(self, **extra):
        dados = {"organizacao": "Padaria", "usuario": "dono", "senha": SENHA}
        dados.update(extra)
        return json(self.client, "post", reverse("api_cadastro"), dados)

    def test_cria_organizacao_e_administrador_sem_login(self):
        resposta = self.cadastrar()
        self.assertEqual(resposta.status_code, 201, resposta.content)
        self.assertEqual(resposta.json(), {"organizacao": "Padaria", "usuario": "dono", "papel": "admin"})
        self.assertTrue(Perfil.objects.get(usuario__username="dono").eh_admin)
        self.assertNotIn("senha", resposta.json())

    def test_recusa_nome_repetido_senha_fraca_e_campos_faltando(self):
        Organizacao.objects.create(nome="padaria")
        self.assertEqual(self.cadastrar().status_code, 400)
        self.assertEqual(self.cadastrar(organizacao="Outra", senha="12345678").status_code, 400)
        self.assertEqual(json(self.client, "post", reverse("api_cadastro"), {"usuario": "x"}).status_code, 400)
        self.assertFalse(User.objects.filter(username__in=["dono", "x"]).exists())

    def test_limite_de_tentativas(self):
        codigos = [self.cadastrar(organizacao=f"Org {i}", usuario=f"u{i}").status_code for i in range(12)]
        self.assertEqual(codigos[:10], [201] * 10)
        self.assertEqual(codigos[10:], [429, 429])
