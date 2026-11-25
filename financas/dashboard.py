"""Métricas do dashboard.

Critério único: tudo é calculado sobre as PARCELAS, pelo mês de vencimento (o mesmo critério dos orçamentos).
- "Recebido" e "pago" contam só parcelas marcadas como pagas.
- "A receber" e "a pagar" contam as parcelas pendentes.
Assim uma compra parcelada em 6 vezes aparece 1/6 por mês, e nada que ainda não foi pago entra no saldo realizado.
"""
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import Categoria, Conta, Orcamento, Parcela

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


def receitas_por_categoria(parcelas, limite=5):
    """Ranking: categorias de receita com maior valor no período (recebido + a receber)."""
    return list(
        parcelas.filter(RECEITA)
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


def orcamentos_do_mes(organizacao, referencia):
    """Limite x gasto de cada orçamento do mês de referência (gasto = parcelas de despesa pagas, como em Orçamentos)."""
    gastos = {
        linha["categoria"]: linha["gasto"]
        for linha in Parcela.objects.filter(
            lancamento__organizacao=organizacao, paga=True,
            vencimento__year=referencia.year, vencimento__month=referencia.month,
        )
        .filter(DESPESA)
        .values(categoria=F("lancamento__categoria_id"))
        .annotate(gasto=Sum("valor"))
    }
    orcamentos = (
        Orcamento.objects.filter(organizacao=organizacao, ano=referencia.year, mes=referencia.month)
        .select_related("categoria")
        .order_by("categoria__nome")
    )
    resultado = []
    for orcamento in orcamentos:
        gasto = gastos.get(orcamento.categoria_id, ZERO)
        resultado.append({
            "nome": orcamento.categoria.nome,
            "limite": orcamento.limite,
            "gasto": gasto,
            "percentual": (gasto / orcamento.limite * 100).quantize(Decimal("0.1")),
            "excedido": gasto > orcamento.limite,
        })
    return resultado


def metricas(organizacao, inicio=None, fim=None):
    parcelas = parcelas_do_periodo(organizacao, inicio, fim)
    referencia = fim or timezone.localdate()
    return {
        "fluxo": fluxo(parcelas),
        "ranking": ranking_despesas(parcelas),
        "receitas": receitas_por_categoria(parcelas),
        "por_conta": despesas_por_conta(parcelas),
        "serie": serie_mensal(parcelas),
        "contas": saldos_por_conta(organizacao),
        "orcamentos": orcamentos_do_mes(organizacao, referencia),
        "referencia": referencia,
    }


def _numero(valor):
    return float(valor or 0)


def dados_dos_graficos(dados, eh_admin):
    """Prepara os números para o Chart.js. A série mensal e a previsão são só do administrador."""
    graficos = {
        "despesas_categoria": [{"nome": i["nome"], "total": _numero(i["total"])} for i in dados["ranking"]],
        "receitas_categoria": [{"nome": i["nome"], "total": _numero(i["total"])} for i in dados["receitas"]],
        "despesas_conta": [{"nome": i["nome"], "total": _numero(i["total"])} for i in dados["por_conta"]],
        "contas": [{"nome": i["nome"], "saldo": _numero(i["saldo"])} for i in dados["contas"]],
        "orcamentos": [
            {"nome": i["nome"], "limite": _numero(i["limite"]), "gasto": _numero(i["gasto"])} for i in dados["orcamentos"]
        ],
    }
    if eh_admin:
        acumulado = 0.0
        fluxo_mensal = []
        for item in dados["serie"]:
            acumulado += _numero(item["recebido"]) - _numero(item["pago"])
            fluxo_mensal.append({
                "mes": item["mes"].strftime("%m/%Y"), "recebido": _numero(item["recebido"]),
                "pago": _numero(item["pago"]), "saldo_acumulado": round(acumulado, 2),
            })
        graficos["fluxo"] = fluxo_mensal
        graficos["previsao"] = [
            {"mes": item["mes"].strftime("%m/%Y"), "a_receber": _numero(item["a_receber"]), "a_pagar": _numero(item["a_pagar"])}
            for item in dados["serie"] if item["a_receber"] or item["a_pagar"]
        ]
    return graficos
