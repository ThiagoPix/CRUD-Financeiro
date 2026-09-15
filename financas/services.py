from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from .models import Categoria, Lancamento, Parcela


def vencimento_mensal(primeiro_vencimento, deslocamento):
    mes_absoluto = primeiro_vencimento.year * 12 + primeiro_vencimento.month - 1 + deslocamento
    ano, mes = divmod(mes_absoluto, 12)
    mes += 1
    dia = min(primeiro_vencimento.day, monthrange(ano, mes)[1])
    return date(ano, mes, dia)


@transaction.atomic
def salvar_lancamento(form):
    lancamento = form.save(commit=False)
    anterior = None
    if lancamento.pk:
        anterior = Lancamento.objects.select_for_update().get(pk=lancamento.pk)
    lancamento.full_clean()
    regenerar = anterior is None or any(
        getattr(anterior, campo) != getattr(lancamento, campo)
        for campo in ("valor_total", "primeiro_vencimento", "quantidade_parcelas")
    )
    lancamento.save()
    if regenerar:
        lancamento.parcelas.all().delete()
        centavos = int(lancamento.valor_total * 100)
        valor_base, restante = divmod(centavos, lancamento.quantidade_parcelas)
        parcelas = [
            Parcela(
                lancamento=lancamento,
                numero=indice + 1,
                valor=Decimal(valor_base + (1 if indice < restante else 0)) / 100,
                vencimento=vencimento_mensal(lancamento.primeiro_vencimento, indice),
            )
            for indice in range(lancamento.quantidade_parcelas)
        ]
        Parcela.objects.bulk_create(parcelas)
    return lancamento


@transaction.atomic
def excluir_lancamento(instance):
    lancamento = Lancamento.objects.select_for_update().get(pk=instance.pk)
    if lancamento.parcelas.filter(paga=True).exists():
        raise ValidationError("Este lançamento possui parcelas pagas. Desmarque os pagamentos antes de excluí-lo.")
    return lancamento.delete()


def totais_orcamento(orcamento):
    comprometido = Parcela.objects.filter(
        lancamento__categoria_id=orcamento.categoria_id,
        lancamento__categoria__tipo=Categoria.Tipo.DESPESA,
        vencimento__month=orcamento.mes,
        vencimento__year=orcamento.ano,
    ).aggregate(total=Sum("valor", default=Decimal("0.00")))["total"]
    disponivel = orcamento.limite - comprometido
    percentual = (comprometido / orcamento.limite * 100).quantize(Decimal("0.01"))
    return {
        "comprometido": comprometido,
        "disponivel": disponivel,
        "excedido": disponivel < 0,
        "percentual": percentual,
    }
