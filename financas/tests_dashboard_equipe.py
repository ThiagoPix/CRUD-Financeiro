import pathlib
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Perfil

from .tests_dashboard import lancar, montar


class EquipeNoDashboardTest(TestCase):
    def setUp(self):
        self.a = montar("A")
        self.b = montar("B")
        self.operador = User.objects.create_user("op_a", password="senha-teste-123")
        Perfil.objects.create(usuario=self.operador, organizacao=self.a["org"], papel="operador")

    def pagina(self, usuario):
        self.client.force_login(usuario)
        return self.client.get(reverse("financas:dashboard"))

    def test_administrador_ve_a_propria_equipe(self):
        resposta = self.pagina(self.a["user"])
        self.assertContains(resposta, "Gerenciar equipe")
        self.assertContains(resposta, "op_a")
        self.assertEqual([p.usuario.username for p in resposta.context["equipe"]], ["op_a", "u_A"])

    def test_equipe_de_outra_organizacao_nao_aparece(self):
        self.assertNotContains(self.pagina(self.a["user"]), "u_B")

    def test_operador_nao_ve_a_equipe(self):
        resposta = self.pagina(self.operador)
        self.assertNotContains(resposta, "Gerenciar equipe")
        self.assertIsNone(resposta.context["equipe"])

    def test_dashboard_continua_funcionando_com_dados(self):
        lancar(self.a, "receita", "100.00", date(2026, 1, 10), pagas=1)
        resposta = self.pagina(self.a["user"])
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["fluxo"]["recebido"], Decimal("100.00"))


class CartoesDoDashboardTest(TestCase):
    def test_os_cartoes_cabem_numa_linha_em_tela_larga(self):
        css = (pathlib.Path(__file__).parent / "static" / "financas" / "estilo.css").read_text(encoding="utf-8")
        self.assertIn(".cartoes { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr))", css)
        self.assertNotIn("minmax(210px, 1fr)); gap: 18px", css)
