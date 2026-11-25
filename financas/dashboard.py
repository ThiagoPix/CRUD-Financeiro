from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth

from .models import Categoria, Lancamento, Parcela

ZERO = Decimal("0.00")
RECEITA = Q(categoria__tipo=Categoria.Tipo.RECEITA)
DESPESA = Q(categoria__tipo=Categoria.Tipo.DESPESA)


def lancamentos_do_periodo(organizacao, inicio=None, fim=None):
    """Base de toda métrica: parte sempre da organização e depois aplica o período."""
    lancamentos = Lancamento.objects.filter(organizacao=organizacao)
    if inicio:
        lancamentos = lancamentos.filter(data__gte=inicio)
    if fim:
        lancamentos = lancamentos.filter(data__lte=fim)
    return lancamentos


def totais(base):
    """KPIs: receitas, despesas, saldo e quantidade de lançamentos."""
    resultado = base.aggregate(
        receitas=Sum("valor_total", filter=RECEITA),
        despesas=Sum("valor_total", filter=DESPESA),
        quantidade=Count("id"),
    )
    receitas = resultado["receitas"] or ZERO
    despesas = resultado["despesas"] or ZERO
    return {"receitas": receitas, "despesas": despesas, "saldo": receitas - despesas, "quantidade": resultado["quantidade"]}


def parcelas_a_pagar(organizacao, inicio=None, fim=None):
    """KPI: parcelas de despesa ainda não pagas, com vencimento no período."""
    parcelas = Parcela.objects.filter(
        lancamento__organizacao=organizacao, lancamento__categoria__tipo=Categoria.Tipo.DESPESA, paga=False
    )
    if inicio:
        parcelas = parcelas.filter(vencimento__gte=inicio)
    if fim:
        parcelas = parcelas.filter(vencimento__lte=fim)
    resultado = parcelas.aggregate(valor=Sum("valor"), quantidade=Count("id"))
    return {"valor": resultado["valor"] or ZERO, "quantidade": resultado["quantidade"]}


def ranking_despesas(base, limite=5):
    """Ranking: as categorias de despesa em que mais se gasta."""
    return list(
        base.filter(DESPESA)
        .values("categoria__nome")
        .annotate(total=Sum("valor_total"))
        .order_by("-total")[:limite]
    )


def despesas_por_conta(base):
    """Distribuição: de onde saiu o dinheiro."""
    return list(
        base.filter(DESPESA)
        .values("conta__nome")
        .annotate(total=Sum("valor_total"))
        .order_by("-total")
    )


def serie_mensal(base):
    """Série no tempo: receitas e despesas por mês."""
    return list(
        base.annotate(mes=TruncMonth("data"))
        .values("mes")
        .annotate(
            receitas=Sum("valor_total", filter=RECEITA),
            despesas=Sum("valor_total", filter=DESPESA),
        )
        .order_by("mes")
    )


def metricas(organizacao, inicio=None, fim=None):
    base = lancamentos_do_periodo(organizacao, inicio, fim)
    return {
        "totais": totais(base),
        "a_pagar": parcelas_a_pagar(organizacao, inicio, fim),
        "ranking": ranking_despesas(base),
        "por_conta": despesas_por_conta(base),
        "serie": serie_mensal(base),
    }
