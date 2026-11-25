from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Organizacao, Perfil

SENHA = "SenhaForte#2026"


def membro(org, nome, papel, **extra):
    usuario = User.objects.create_user(nome, password=SENHA, **extra)
    return Perfil.objects.create(usuario=usuario, organizacao=org, papel=papel)


class EquipeTest(TestCase):
    def setUp(self):
        self.org = Organizacao.objects.create(nome="A")
        self.outra = Organizacao.objects.create(nome="B")
        self.admin = membro(self.org, "admin_a", "admin")
        self.operador = membro(self.org, "op_a", "operador")
        self.de_outra = membro(self.outra, "admin_b", "admin")
        self.client.force_login(self.admin.usuario)

    def rotas(self):
        return [
            reverse("core:equipe_lista"), reverse("core:equipe_criar"),
            reverse("core:equipe_editar", args=[self.operador.pk]),
            reverse("core:equipe_remover", args=[self.operador.pk]),
        ]

    # --- acesso
    def test_operador_recebe_403_em_toda_a_equipe(self):
        self.client.force_login(self.operador.usuario)
        for url in self.rotas():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_administrador_acessa(self):
        for url in self.rotas():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_anonimo_vai_para_o_login(self):
        self.client.logout()
        resposta = self.client.get(reverse("core:equipe_lista"))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/entrar/", resposta["Location"])

    def test_link_no_menu_so_para_administrador(self):
        self.assertContains(self.client.get(reverse("financas:dashboard")), reverse("core:equipe_lista"))
        self.client.force_login(self.operador.usuario)
        self.assertNotContains(self.client.get(reverse("financas:dashboard")), reverse("core:equipe_lista"))

    # --- lista
    def test_lista_mostra_so_a_propria_organizacao(self):
        resposta = self.client.get(reverse("core:equipe_lista"))
        self.assertContains(resposta, "op_a")
        self.assertNotContains(resposta, "admin_b")
        self.assertContains(resposta, "(você)")

    # --- criar
    def test_cria_membro_na_organizacao_do_administrador(self):
        resposta = self.client.post(reverse("core:equipe_criar"), {"usuario": "novo", "senha": SENHA, "papel": "operador"})
        self.assertRedirects(resposta, reverse("core:equipe_lista"))
        perfil = Perfil.objects.get(usuario__username="novo")
        self.assertEqual(perfil.organizacao, self.org)
        self.assertEqual(perfil.papel, "operador")

    def test_organizacao_enviada_no_formulario_e_ignorada(self):
        self.client.post(reverse("core:equipe_criar"), {
            "usuario": "invasor", "senha": SENHA, "papel": "admin", "organizacao": self.outra.pk,
        })
        self.assertEqual(Perfil.objects.get(usuario__username="invasor").organizacao, self.org)

    def test_membro_novo_consegue_entrar(self):
        self.client.post(reverse("core:equipe_criar"), {"usuario": "novo", "senha": SENHA, "papel": "operador"})
        self.client.logout()
        self.assertTrue(self.client.login(username="novo", password=SENHA))

    def test_criar_recusa_senha_fraca_usuario_repetido_e_papel_invalido(self):
        casos = [
            {"usuario": "novo", "senha": "12345678", "papel": "operador"},
            {"usuario": "op_a", "senha": SENHA, "papel": "operador"},
            {"usuario": "novo", "senha": SENHA, "papel": "dono"},
        ]
        for dados in casos:
            with self.subTest(dados=dados):
                resposta = self.client.post(reverse("core:equipe_criar"), dados)
                self.assertEqual(resposta.status_code, 200)
        self.assertFalse(User.objects.filter(username="novo").exists())

    # --- editar
    def test_altera_papel(self):
        resposta = self.client.post(reverse("core:equipe_editar", args=[self.operador.pk]), {"papel": "admin"})
        self.assertRedirects(resposta, reverse("core:equipe_lista"))
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.papel, "admin")

    def test_nao_rebaixa_o_ultimo_administrador(self):
        resposta = self.client.post(reverse("core:equipe_editar", args=[self.admin.pk]), {"papel": "operador"})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "pelo menos um administrador")
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.papel, "admin")

    def test_rebaixa_administrador_quando_ha_outro(self):
        membro(self.org, "admin_2", "admin")
        self.client.post(reverse("core:equipe_editar", args=[self.admin.pk]), {"papel": "operador"})
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.papel, "operador")

    def test_editar_perfil_de_outra_organizacao_retorna_404(self):
        self.assertEqual(self.client.get(reverse("core:equipe_editar", args=[self.de_outra.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("core:equipe_editar", args=[self.de_outra.pk]), {"papel": "operador"}).status_code, 404)
        self.de_outra.refresh_from_db()
        self.assertEqual(self.de_outra.papel, "admin")

    def test_superusuario_nao_e_alterado_pela_equipe(self):
        super_perfil = membro(self.org, "super", "admin", is_superuser=True)
        self.client.post(reverse("core:equipe_editar", args=[super_perfil.pk]), {"papel": "operador"})
        super_perfil.refresh_from_db()
        self.assertEqual(super_perfil.papel, "admin")

    # --- remover
    def test_remove_membro_e_o_usuario_deixa_de_existir(self):
        resposta = self.client.post(reverse("core:equipe_remover", args=[self.operador.pk]))
        self.assertRedirects(resposta, reverse("core:equipe_lista"))
        self.assertFalse(User.objects.filter(username="op_a").exists())

    def test_nao_remove_a_si_mesmo(self):
        resposta = self.client.post(reverse("core:equipe_remover", args=[self.admin.pk]), follow=True)
        self.assertContains(resposta, "não pode remover o seu próprio usuário")
        self.assertTrue(User.objects.filter(username="admin_a").exists())

    def test_nao_remove_o_ultimo_administrador(self):
        # o administrador logado e outro usuario administrador: remover o outro e permitido; o unico nao
        segundo = membro(self.org, "admin_2", "admin")
        self.client.force_login(segundo.usuario)
        self.client.post(reverse("core:equipe_remover", args=[self.admin.pk]))
        self.assertFalse(User.objects.filter(username="admin_a").exists())
        self.assertTrue(User.objects.filter(username="admin_2").exists())

    def test_remover_perfil_de_outra_organizacao_retorna_404(self):
        self.assertEqual(self.client.post(reverse("core:equipe_remover", args=[self.de_outra.pk])).status_code, 404)
        self.assertTrue(User.objects.filter(username="admin_b").exists())

    def test_nao_remove_superusuario(self):
        super_perfil = membro(self.org, "super", "operador", is_superuser=True)
        self.client.post(reverse("core:equipe_remover", args=[super_perfil.pk]))
        self.assertTrue(User.objects.filter(username="super").exists())

    def test_tela_de_remocao_pede_confirmacao(self):
        resposta = self.client.get(reverse("core:equipe_remover", args=[self.operador.pk]))
        self.assertContains(resposta, "Remover da equipe")
        self.assertTrue(User.objects.filter(username="op_a").exists())
