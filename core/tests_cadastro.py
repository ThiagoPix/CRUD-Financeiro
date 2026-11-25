from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Organizacao, Perfil
from core.servicos import cadastrar_organizacao


DADOS = {
    "organizacao": "Padaria Central", "usuario": "dona_ana",
    "senha": "SenhaForte#2026", "confirmar_senha": "SenhaForte#2026",
}


class CadastroDeOrganizacaoTest(TestCase):
    def enviar(self, **alterar):
        dados = {**DADOS, **alterar}
        return self.client.post(reverse("core:cadastro"), dados)

    def test_pagina_abre_sem_login_e_tem_link_na_tela_de_entrada(self):
        self.assertEqual(self.client.get(reverse("core:cadastro")).status_code, 200)
        self.assertContains(self.client.get(reverse("login")), reverse("core:cadastro"))

    def test_cria_organizacao_usuario_e_perfil_de_administrador(self):
        resposta = self.enviar()
        self.assertRedirects(resposta, reverse("financas:dashboard"), fetch_redirect_response=False)
        organizacao = Organizacao.objects.get(nome="Padaria Central")
        perfil = Perfil.objects.get(usuario__username="dona_ana")
        self.assertEqual(perfil.organizacao, organizacao)
        self.assertTrue(perfil.eh_admin)

    def test_usuario_novo_ja_entra_logado_e_ve_o_dashboard_vazio(self):
        self.enviar()
        resposta = self.client.get(reverse("financas:dashboard"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["fluxo"]["lancamentos"], 0)
        self.assertEqual(self.client.get(reverse("financas:conta_lista")).status_code, 200)

    def test_organizacao_nova_nao_enxerga_dados_de_outra(self):
        from datetime import date
        from decimal import Decimal

        from financas.models import Categoria, Conta, Lancamento
        outra = Organizacao.objects.create(nome="Outra")
        conta = Conta.objects.create(organizacao=outra, nome="Caixa", tipo="carteira")
        categoria = Categoria.objects.create(organizacao=outra, nome="Vendas", tipo="receita")
        Lancamento.objects.create(
            organizacao=outra, descricao="Segredo", conta=conta, categoria=categoria, valor_total=Decimal("10"),
            data=date(2026, 1, 1), primeiro_vencimento=date(2026, 1, 1),
        )
        self.enviar()
        self.assertNotContains(self.client.get(reverse("financas:lancamento_lista")), "Segredo")

    def test_senhas_diferentes_nao_criam_nada(self):
        resposta = self.enviar(confirmar_senha="outra")
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "As senhas não conferem.")
        self.assertFalse(Organizacao.objects.filter(nome="Padaria Central").exists())
        self.assertFalse(User.objects.filter(username="dona_ana").exists())

    def test_senha_fraca_e_recusada(self):
        resposta = self.enviar(senha="12345678", confirmar_senha="12345678")
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(User.objects.filter(username="dona_ana").exists())
        self.assertFalse(Organizacao.objects.filter(nome="Padaria Central").exists())

    def test_usuario_repetido_e_recusado_sem_criar_a_organizacao(self):
        User.objects.create_user("dona_ana", password="SenhaForte#2026")
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Organizacao.objects.filter(nome="Padaria Central").exists())

    def test_nome_de_organizacao_repetido_ignora_maiusculas(self):
        Organizacao.objects.create(nome="padaria central")
        resposta = self.enviar()
        self.assertContains(resposta, "Já existe uma organização com este nome.")
        self.assertFalse(User.objects.filter(username="dona_ana").exists())

    def test_usuario_com_caracteres_invalidos_e_recusado(self):
        resposta = self.enviar(usuario="com espaco")
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Organizacao.objects.filter(nome="Padaria Central").exists())

    def test_quem_ja_esta_logado_e_redirecionado(self):
        self.enviar()
        resposta = self.client.get(reverse("core:cadastro"))
        self.assertEqual(resposta.status_code, 302)

    def test_servico_exige_nome_da_organizacao(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as contexto:
            cadastrar_organizacao("   ", "alguem", "SenhaForte#2026")
        self.assertIn("organizacao", contexto.exception.message_dict)
