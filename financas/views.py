from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from .forms import CategoriaForm, ContaForm, FiltroMesForm, LancamentoForm, OrcamentoForm, ParcelaForm
from .models import Categoria, Conta, Lancamento, Orcamento, Parcela
from .services import excluir_lancamento, salvar_lancamento, totais_orcamento
from .templatetags.financas_tags import dinheiro


def acoes(objeto, nome):
    return {
        "editar_url": reverse(f"financas:{nome}_editar", args=[objeto.pk]),
        "excluir_url": reverse(f"financas:{nome}_excluir", args=[objeto.pk]),
    }


def formulario(request, classe_form, titulo, secao, voltar_url, instance=None, salvar=None, subtitulo=""):
    form = classe_form(request.POST if request.method == "POST" else None, instance=instance)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                objeto = salvar(form) if salvar else form.save()
        except ValidationError as erro:
            form.add_error(None, erro)
        except IntegrityError:
            form.add_error(None, "Já existe um registro com esses dados. Confira o formulário.")
        else:
            messages.success(request, "Registro salvo com sucesso.")
            if isinstance(objeto, Lancamento):
                return redirect("financas:lancamento_detalhe", pk=objeto.pk)
            if isinstance(objeto, Orcamento):
                return redirect(f"{voltar_url}?mes={objeto.mes}&ano={objeto.ano}")
            return redirect(voltar_url)
    return render(request, "financas/formulario.html", {
        "form": form,
        "titulo": titulo,
        "subtitulo": subtitulo,
        "secao": secao,
        "voltar_url": voltar_url,
    })


def confirmar_exclusao(request, objeto, titulo, secao, voltar_url, excluir=None, detalhe=""):
    if request.method == "POST":
        try:
            with transaction.atomic():
                excluir(objeto) if excluir else objeto.delete()
        except ProtectedError:
            messages.error(request, "Este registro está vinculado a lançamentos ou orçamentos e não pode ser excluído.")
        except ValidationError as erro:
            messages.error(request, " ".join(erro.messages))
        else:
            messages.success(request, "Registro excluído com sucesso.")
            return redirect(voltar_url)
    return render(request, "financas/confirmar_exclusao.html", {
        "objeto": objeto,
        "titulo": titulo,
        "secao": secao,
        "voltar_url": voltar_url,
        "detalhe_exclusao": detalhe,
    })


@require_GET
def inicio(request):
    return redirect("financas:lancamento_lista")


@require_GET
def conta_lista(request):
    linhas = [{"celulas": [conta.nome, conta.get_tipo_display()], **acoes(conta, "conta")} for conta in Conta.objects.all()]
    return render(request, "financas/lista.html", {
        "titulo": "Contas", "subtitulo": "Organize onde seu dinheiro entra e sai.",
        "secao": "contas", "colunas": ["Nome", "Tipo"], "linhas": linhas,
        "criar_url": reverse("financas:conta_criar"), "vazio": "Cadastre sua primeira conta para começar a registrar movimentações.",
    })


@require_http_methods(["GET", "POST"])
def conta_criar(request):
    return formulario(request, ContaForm, "Nova conta", "contas", reverse("financas:conta_lista"))


@require_http_methods(["GET", "POST"])
def conta_editar(request, pk):
    return formulario(request, ContaForm, "Editar conta", "contas", reverse("financas:conta_lista"), get_object_or_404(Conta, pk=pk))


@require_http_methods(["GET", "POST"])
def conta_excluir(request, pk):
    return confirmar_exclusao(request, get_object_or_404(Conta, pk=pk), "Excluir conta", "contas", reverse("financas:conta_lista"))


@require_GET
def categoria_lista(request):
    linhas = [{"celulas": [categoria.nome, categoria.get_tipo_display()], **acoes(categoria, "categoria")} for categoria in Categoria.objects.all()]
    return render(request, "financas/lista.html", {
        "titulo": "Categorias", "subtitulo": "Dê um destino claro a cada receita e despesa.",
        "secao": "categorias", "colunas": ["Nome", "Tipo"], "linhas": linhas,
        "criar_url": reverse("financas:categoria_criar"), "vazio": "Cadastre categorias de receita e despesa para classificar seus lançamentos.",
    })


@require_http_methods(["GET", "POST"])
def categoria_criar(request):
    return formulario(request, CategoriaForm, "Nova categoria", "categorias", reverse("financas:categoria_lista"))


@require_http_methods(["GET", "POST"])
def categoria_editar(request, pk):
    return formulario(request, CategoriaForm, "Editar categoria", "categorias", reverse("financas:categoria_lista"), get_object_or_404(Categoria, pk=pk))


@require_http_methods(["GET", "POST"])
def categoria_excluir(request, pk):
    return confirmar_exclusao(request, get_object_or_404(Categoria, pk=pk), "Excluir categoria", "categorias", reverse("financas:categoria_lista"))


@require_GET
def lancamento_lista(request):
    lancamentos = Lancamento.objects.select_related("conta", "categoria")
    linhas = [{
        "celulas": [item.descricao, item.get_tipo_display(), item.conta.nome, item.categoria.nome, dinheiro(item.valor_total), item.data.strftime("%d/%m/%Y"), str(item.quantidade_parcelas)],
        "detalhe_url": reverse("financas:lancamento_detalhe", args=[item.pk]),
        **acoes(item, "lancamento"),
    } for item in lancamentos]
    return render(request, "financas/lista.html", {
        "titulo": "Lançamentos", "subtitulo": "Suas receitas e despesas, com cada parcela no lugar.",
        "secao": "lancamentos", "colunas": ["Descrição", "Tipo", "Conta", "Categoria", "Valor total", "Data", "Parcelas"],
        "linhas": linhas, "criar_url": reverse("financas:lancamento_criar"),
        "vazio": "Comece cadastrando uma conta e uma categoria. Depois, registre seu primeiro lançamento.",
    })


@require_http_methods(["GET", "POST"])
def lancamento_criar(request):
    return formulario(request, LancamentoForm, "Novo lançamento", "lancamentos", reverse("financas:lancamento_lista"), salvar=salvar_lancamento, subtitulo="O tipo de movimentação é definido pela categoria escolhida.")


@require_http_methods(["GET", "POST"])
def lancamento_editar(request, pk):
    return formulario(request, LancamentoForm, "Editar lançamento", "lancamentos", reverse("financas:lancamento_detalhe", args=[pk]), get_object_or_404(Lancamento, pk=pk), salvar_lancamento, "Alterar o valor, a quantidade ou o primeiro vencimento recalcula todas as parcelas pendentes e seus vencimentos.")


@require_GET
def lancamento_detalhe(request, pk):
    lancamento = get_object_or_404(Lancamento.objects.select_related("conta", "categoria"), pk=pk)
    parcelas = list(lancamento.parcelas.all())
    total_pago = sum((parcela.valor for parcela in parcelas if parcela.paga), Decimal("0.00"))
    total_pendente = sum((parcela.valor for parcela in parcelas if not parcela.paga), Decimal("0.00"))
    return render(request, "financas/lancamento_detalhe.html", {
        "lancamento": lancamento, "parcelas": parcelas, "total_pago": total_pago,
        "total_pendente": total_pendente, "secao": "lancamentos", "titulo": lancamento.descricao,
    })


@require_http_methods(["GET", "POST"])
def lancamento_excluir(request, pk):
    return confirmar_exclusao(request, get_object_or_404(Lancamento, pk=pk), "Excluir lançamento", "lancamentos", reverse("financas:lancamento_lista"), excluir_lancamento, "Todas as parcelas deste lançamento também serão excluídas. Lançamentos com parcelas pagas precisam ter os pagamentos desmarcados primeiro.")


@require_GET
def orcamento_lista(request):
    hoje = timezone.localdate()
    filtro = FiltroMesForm(request.GET if request.GET else {"mes": hoje.month, "ano": hoje.year})
    resumos = []
    if filtro.is_valid():
        orcamentos = Orcamento.objects.select_related("categoria").filter(**filtro.cleaned_data)
        resumos = [{"orcamento": orcamento, **totais_orcamento(orcamento)} for orcamento in orcamentos]
    return render(request, "financas/orcamentos.html", {
        "titulo": "Orçamentos", "secao": "orcamentos", "filtro": filtro, "resumos": resumos,
    })


@require_http_methods(["GET", "POST"])
def orcamento_criar(request):
    return formulario(request, OrcamentoForm, "Novo orçamento", "orcamentos", reverse("financas:orcamento_lista"), subtitulo="Defina um limite mensal para uma categoria de despesa.")


@require_http_methods(["GET", "POST"])
def orcamento_editar(request, pk):
    return formulario(request, OrcamentoForm, "Editar orçamento", "orcamentos", reverse("financas:orcamento_lista"), get_object_or_404(Orcamento, pk=pk))


@require_http_methods(["GET", "POST"])
def orcamento_excluir(request, pk):
    orcamento = get_object_or_404(Orcamento, pk=pk)
    voltar_url = f"{reverse('financas:orcamento_lista')}?mes={orcamento.mes}&ano={orcamento.ano}"
    return confirmar_exclusao(request, orcamento, "Excluir orçamento", "orcamentos", voltar_url, detalhe="Os lançamentos e suas parcelas serão preservados.")


@require_http_methods(["GET", "POST"])
def parcela_editar(request, pk):
    parcela = get_object_or_404(Parcela.objects.select_related("lancamento"), pk=pk)
    if request.method == "POST":
        with transaction.atomic():
            get_object_or_404(Lancamento.objects.select_for_update(), pk=parcela.lancamento_id)
            parcela = get_object_or_404(Parcela.objects.select_related("lancamento"), pk=pk)
            form = ParcelaForm(request.POST, instance=parcela)
            if form.is_valid():
                form.save()
                messages.success(request, "Parcela atualizada com sucesso.")
                return redirect("financas:lancamento_detalhe", pk=parcela.lancamento_id)
    else:
        form = ParcelaForm(instance=parcela)
    return render(request, "financas/formulario.html", {
        "titulo": f"Editar parcela {parcela.numero}", "secao": "lancamentos", "form": form,
        "subtitulo": f"{parcela.lancamento.descricao} · {dinheiro(parcela.valor)}. Atualize o vencimento ou a situação de pagamento.",
        "voltar_url": reverse("financas:lancamento_detalhe", args=[parcela.lancamento_id]),
    })
