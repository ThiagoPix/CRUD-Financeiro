import csv

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET

from core.organizacao import org_atual
from core.permissoes import papel_requerido

from .dashboard import parcelas_do_periodo
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
    """Exporta as parcelas do período, o mesmo critério dos números do dashboard."""
    form = PeriodoForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest("Período inválido.")
    parcelas = (
        parcelas_do_periodo(org_atual(request), form.cleaned_data["inicio"], form.cleaned_data["fim"])
        .select_related("lancamento__categoria", "lancamento__conta")
        .order_by("vencimento", "pk")
    )
    resposta = HttpResponse(content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = 'attachment; filename="parcelas.csv"'
    resposta.write("﻿")
    escritor = csv.writer(resposta, delimiter=";")
    escritor.writerow(["Vencimento", "Lançamento", "Parcela", "Tipo", "Categoria", "Conta", "Valor", "Situação"])
    for parcela in parcelas:
        lancamento = parcela.lancamento
        escritor.writerow([
            parcela.vencimento.strftime("%d/%m/%Y"), neutralizar(lancamento.descricao),
            f"{parcela.numero}/{lancamento.quantidade_parcelas}", lancamento.get_tipo_display(),
            neutralizar(lancamento.categoria.nome), neutralizar(lancamento.conta.nome),
            decimal_br(parcela.valor), "Paga" if parcela.paga else "Pendente",
        ])
    return resposta
