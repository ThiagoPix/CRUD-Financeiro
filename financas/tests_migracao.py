from datetime import date
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

ANTES = [("financas", "0002_sqlite_centavos")]
DEPOIS = [("financas", "0005_organizacao_obrigatoria")]


class MigracaoDadosDaP1Test(TransactionTestCase):
    """Prova que os dados da P1 (sem organização) sobrevivem à chegada da multi-organização."""

    def migrar(self, alvo):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(alvo)
        return executor.loader.project_state(alvo).apps

    def tearDown(self):
        self.migrar(DEPOIS + [("core", "0002_perfil_papel")])

    def test_dados_existentes_ganham_a_organizacao_padrao(self):
        apps_antigo = self.migrar(ANTES)
        Conta = apps_antigo.get_model("financas", "Conta")
        Categoria = apps_antigo.get_model("financas", "Categoria")
        Lancamento = apps_antigo.get_model("financas", "Lancamento")
        Orcamento = apps_antigo.get_model("financas", "Orcamento")
        Parcela = apps_antigo.get_model("financas", "Parcela")

        conta = Conta.objects.create(nome="Carteira", tipo="carteira")
        despesa = Categoria.objects.create(nome="Mercado", tipo="despesa")
        lancamento = Lancamento.objects.create(
            descricao="Compra da P1", conta=conta, categoria=despesa, valor_total=Decimal("90.00"),
            data=date(2026, 9, 1), primeiro_vencimento=date(2026, 9, 1), quantidade_parcelas=3,
        )
        Parcela.objects.create(lancamento=lancamento, numero=1, valor=Decimal("30.00"), vencimento=date(2026, 9, 1))
        Orcamento.objects.create(categoria=despesa, mes=9, ano=2026, limite=Decimal("500.00"))

        apps_novo = self.migrar(DEPOIS)
        Organizacao = apps_novo.get_model("core", "Organizacao")
        organizacao = Organizacao.objects.get(nome="Organização padrão")
        for nome in ("Conta", "Categoria", "Lancamento", "Orcamento"):
            modelo = apps_novo.get_model("financas", nome)
            self.assertEqual(modelo.objects.count(), 1, nome)
            self.assertEqual(modelo.objects.get().organizacao_id, organizacao.pk, nome)
        self.assertEqual(apps_novo.get_model("financas", "Parcela").objects.count(), 1)
        self.assertEqual(apps_novo.get_model("financas", "Lancamento").objects.get().valor_total, Decimal("90.00"))

    def test_banco_vazio_migra_sem_criar_dados(self):
        self.migrar(ANTES)
        apps_novo = self.migrar(DEPOIS)
        for nome in ("Conta", "Categoria", "Lancamento", "Orcamento"):
            self.assertEqual(apps_novo.get_model("financas", nome).objects.count(), 0)
