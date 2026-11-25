from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Conta
from .tests_dashboard import lancar, montar


class SaldoDaContaTest(TestCase):
    def setUp(self):
        self.a = montar("A")
        self.conta = self.a["conta"]
        self.conta.saldo_inicial = Decimal("1000.00")
        self.conta.save()
        self.client.force_login(self.a["user"])

    def saldo(self):
        return Conta.objects.com_saldo().get(pk=self.conta.pk).saldo_atual

    def test_saldo_e_o_inicial_quando_nao_ha_movimento(self):
        self.assertEqual(self.saldo(), Decimal("1000.00"))

    def test_so_parcelas_pagas_mexem_no_saldo(self):
        lancar(self.a, "receita", "500.00", date(2026, 1, 10), pagas=1)
        lancar(self.a, "despesa", "200.00", date(2026, 1, 15), pagas=1)
        lancar(self.a, "despesa", "999.00", date(2026, 1, 20))  # pendente: nao conta
        lancar(self.a, "receita", "777.00", date(2026, 1, 25))  # pendente: nao conta
        self.assertEqual(self.saldo(), Decimal("1300.00"))

    def test_compra_parcelada_so_desconta_a_parcela_paga(self):
        lancar(self.a, "despesa", "300.00", date(2026, 1, 10), parcelas=3, pagas=2)
        self.assertEqual(self.saldo(), Decimal("800.00"))

    def test_saldo_pode_ficar_negativo(self):
        lancar(self.a, "despesa", "1500.00", date(2026, 1, 10), pagas=1)
        self.assertEqual(self.saldo(), Decimal("-500.00"))

    def test_saldo_nao_mistura_contas_nem_organizacoes(self):
        outra_conta = Conta.objects.create(organizacao=self.a["org"], nome="Caixa", tipo="carteira")
        outra_org = montar("B")
        lancar(self.a, "despesa", "100.00", date(2026, 1, 10), pagas=1)
        lancar(outra_org, "despesa", "999.00", date(2026, 1, 10), pagas=1)
        self.assertEqual(self.saldo(), Decimal("900.00"))
        self.assertEqual(Conta.objects.com_saldo().get(pk=outra_conta.pk).saldo_atual, Decimal("0.00"))

    def test_propriedade_funciona_sem_anotacao(self):
        lancar(self.a, "receita", "50.00", date(2026, 1, 10), pagas=1)
        self.assertEqual(Conta.objects.get(pk=self.conta.pk).saldo_atual, Decimal("1050.00"))


class ContaNasTelasTest(TestCase):
    def setUp(self):
        self.a = montar("A")
        self.a["conta"].saldo_inicial = Decimal("250.00")
        self.a["conta"].save()
        lancar(self.a, "receita", "100.00", date(2026, 1, 10), pagas=1)
        self.client.force_login(self.a["user"])

    def test_lista_de_contas_mostra_o_saldo_atual(self):
        resposta = self.client.get(reverse("financas:conta_lista"))
        self.assertContains(resposta, "Saldo atual")
        self.assertContains(resposta, "R$ 350,00")

    def test_lista_de_contas_tem_numero_fixo_de_consultas(self):
        for indice in range(10):
            from .models import Conta as ContaModelo
            ContaModelo.objects.create(organizacao=self.a["org"], nome=f"Extra {indice}", tipo="carteira")
        # sessao + usuario + perfil + organizacao + contas (anotadas) = 5
        with self.assertNumQueries(5):
            self.client.get(reverse("financas:conta_lista"))

    def test_formulario_grava_saldo_inicial(self):
        resposta = self.client.post(reverse("financas:conta_criar"), {"nome": "Poupanca", "tipo": "poupanca", "saldo_inicial": "1200.50"})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(Conta.objects.get(nome="Poupanca").saldo_inicial, Decimal("1200.50"))

    def test_formulario_sem_saldo_inicial_assume_zero(self):
        self.client.post(reverse("financas:conta_criar"), {"nome": "Sem saldo", "tipo": "carteira", "saldo_inicial": ""})
        self.assertEqual(Conta.objects.get(nome="Sem saldo").saldo_inicial, Decimal("0.00"))

    def test_dashboard_mostra_saldo_por_conta(self):
        contexto = self.client.get(reverse("financas:dashboard")).context
        self.assertEqual(contexto["contas"], [{"nome": "Banco", "tipo": "Conta corrente", "saldo": Decimal("350.00")}])

    def test_api_devolve_saldo_inicial_e_saldo_atual(self):
        dados = self.client.get(reverse("api_conta_lista")).json()
        self.assertEqual(dados[0]["saldo_inicial"], "250.00")
        self.assertEqual(dados[0]["saldo_atual"], "350.00")

    def test_api_cria_conta_com_saldo_inicial(self):
        resposta = self.client.post(
            reverse("api_conta_lista"), {"nome": "Nova", "tipo": "carteira", "saldo_inicial": "80.00"}, content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 201, resposta.content)
        self.assertEqual(resposta.json()["saldo_atual"], "80.00")
