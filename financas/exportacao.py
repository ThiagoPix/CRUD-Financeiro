import csv

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET

from core.organizacao import org_atual
from core.permissoes import papel_requerido

from .dashboard import lancamentos_do_periodo
from .forms import PeriodoForm

PREFIXOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def neutralizar(texto):
    """O Excel interpreta células iniciadas por = + - @ como fórmula; o apóstrofo evita isso."""
    texto = "" if texto is None else str(texto)
    return "'" + texto if texto.startswith(PREFIXOS_DE_FORMULA) else texto


def decimal_br(valor):
    return str(valor).replace(".", ",")


@require_GET
@papel_requerido("admin")
def exportar_lancamentos_csv(request):
    form = PeriodoForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest("Período inválido.")
    lancamentos = (
        lancamentos_do_periodo(org_atual(request), form.cleaned_data["inicio"], form.cleaned_data["fim"])
        .select_related("conta", "categoria")
        .order_by("data", "pk")
    )
    resposta = HttpResponse(content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = 'attachment; filename="lancamentos.csv"'
    resposta.write("﻿")
    escritor = csv.writer(resposta, delimiter=";")
    escritor.writerow(["Data", "Descrição", "Tipo", "Categoria", "Conta", "Valor total", "Parcelas"])
    for item in lancamentos:
        escritor.writerow([
            item.data.strftime("%d/%m/%Y"), neutralizar(item.descricao), item.get_tipo_display(),
            neutralizar(item.categoria.nome), neutralizar(item.conta.nome), decimal_br(item.valor_total),
            item.quantidade_parcelas,
        ])
    return resposta
