"""Métricas do dashboard.

Critério único: tudo é calculado sobre as PARCELAS, pelo mês de vencimento (o mesmo critério dos orçamentos).
- "Recebido" e "pago" contam só parcelas marcadas como pagas.
- "A receber" e "a pagar" contam as parcelas pendentes.
Assim uma compra parcelada em 6 vezes aparece 1/6 por mês, e nada que ainda não foi pago entra no saldo realizado.
"""
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncMonth

from .models import Categoria, Conta, Parcela

ZERO = Decimal("0.00")
RECEITA = Q(lancamento__categoria__tipo=Categoria.Tipo.RECEITA)
DESPESA = Q(lancamento__categoria__tipo=Categoria.Tipo.DESPESA)
PAGA = Q(paga=True)
PENDENTE = Q(paga=False)


def parcelas_do_periodo(organizacao, inicio=None, fim=None):
    """Base de toda métrica: parte sempre da organização e depois aplica o período (vencimento)."""
    parcelas = Parcela.objects.filter(lancamento__organizacao=organizacao)
    if inicio:
        parcelas = parcelas.filter(vencimento__gte=inicio)
    if fim:
        parcelas = parcelas.filter(vencimento__lte=fim)
    return parcelas


def _soma(filtro):
    return Sum("valor", filter=filtro)


def fluxo(parcelas):
    """KPIs: o que já aconteceu (recebido, pago) e o que ainda vai acontecer (a receber, a pagar)."""
    resultado = parcelas.aggregate(
        recebido=_soma(RECEITA & PAGA),
        a_receber=_soma(RECEITA & PENDENTE),
        pago=_soma(DESPESA & PAGA),
        a_pagar=_soma(DESPESA & PENDENTE),
        qtd_a_receber=Count("id", filter=RECEITA & PENDENTE),
        qtd_a_pagar=Count("id", filter=DESPESA & PENDENTE),
        lancamentos=Count("lancamento", distinct=True),
    )
    recebido = resultado["recebido"] or ZERO
    a_receber = resultado["a_receber"] or ZERO
    pago = resultado["pago"] or ZERO
    a_pagar = resultado["a_pagar"] or ZERO
    return {
        "recebido": recebido,
        "a_receber": a_receber,
        "pago": pago,
        "a_pagar": a_pagar,
        "qtd_a_receber": resultado["qtd_a_receber"],
        "qtd_a_pagar": resultado["qtd_a_pagar"],
        "lancamentos": resultado["lancamentos"],
        "saldo_realizado": recebido - pago,
        "saldo_previsto": recebido + a_receber - pago - a_pagar,
    }


def ranking_despesas(parcelas, limite=5):
    """Ranking: categorias de despesa com maior valor no período (pago + a pagar)."""
    return list(
        parcelas.filter(DESPESA)
        .values(nome=F("lancamento__categoria__nome"))
        .annotate(total=Sum("valor"))
        .order_by("-total", "nome")[:limite]
    )


def despesas_por_conta(parcelas):
    """Distribuição: em qual conta as despesas do período foram lançadas (pago + a pagar)."""
    return list(
        parcelas.filter(DESPESA)
        .values(nome=F("lancamento__conta__nome"))
        .annotate(total=Sum("valor"))
        .order_by("-total", "nome")
    )


def serie_mensal(parcelas):
    """Série no tempo: recebido, pago, a receber e a pagar por mês de vencimento."""
    return list(
        parcelas.annotate(mes=TruncMonth("vencimento"))
        .values("mes")
        .annotate(
            recebido=_soma(RECEITA & PAGA),
            pago=_soma(DESPESA & PAGA),
            a_receber=_soma(RECEITA & PENDENTE),
            a_pagar=_soma(DESPESA & PENDENTE),
        )
        .order_by("mes")
    )


def saldos_por_conta(organizacao):
    """Saldo atual de cada conta (acumulado, não depende do período): saldo inicial + recebido - pago."""
    return [
        {"nome": conta.nome, "tipo": conta.get_tipo_display(), "saldo": conta.saldo_atual}
        for conta in Conta.objects.filter(organizacao=organizacao).com_saldo()
    ]


def metricas(organizacao, inicio=None, fim=None):
    parcelas = parcelas_do_periodo(organizacao, inicio, fim)
    return {
        "fluxo": fluxo(parcelas),
        "ranking": ranking_despesas(parcelas),
        "por_conta": despesas_por_conta(parcelas),
        "serie": serie_mensal(parcelas),
        "contas": saldos_por_conta(organizacao),
    }
