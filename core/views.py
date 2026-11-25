from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from .forms import CadastroForm, MembroForm, PapelForm, adicionar_erros
from .models import Perfil
from .organizacao import org_atual
from .permissoes import papel_requerido
from .servicos import alterar_papel, cadastrar_organizacao, criar_membro, remover_membro


@login_not_required
@require_http_methods(["GET", "POST"])
def cadastro(request):
    if request.user.is_authenticated:
        return redirect("financas:inicio")
    form = CadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            perfil = cadastrar_organizacao(
                form.cleaned_data["organizacao"], form.cleaned_data["usuario"], form.cleaned_data["senha"]
            )
        except ValidationError as erro:
            adicionar_erros(form, erro)
        else:
            login(request, perfil.usuario)
            messages.success(request, f"Organização {perfil.organizacao} criada. Você é o administrador.")
            return redirect("financas:dashboard")
    return render(request, "core/cadastro.html", {"form": form})


def _membro(request, pk):
    """Perfil sempre restrito à organização do administrador logado."""
    return get_object_or_404(Perfil.objects.select_related("usuario"), pk=pk, organizacao=org_atual(request))


def _formulario(request, form, titulo, subtitulo, botao):
    return render(request, "core/formulario.html", {
        "form": form, "titulo": titulo, "subtitulo": subtitulo, "botao": botao,
        "voltar_url": reverse("core:equipe_lista"), "secao": "equipe",
    })


@require_GET
@papel_requerido("admin")
def equipe_lista(request):
    organizacao = org_atual(request)
    perfis = Perfil.objects.filter(organizacao=organizacao).select_related("usuario").order_by("usuario__username")
    return render(request, "core/equipe.html", {
        "titulo": "Equipe", "secao": "equipe", "organizacao": organizacao, "perfis": perfis,
    })


@require_http_methods(["GET", "POST"])
@papel_requerido("admin")
def equipe_criar(request):
    form = MembroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            criar_membro(org_atual(request), form.cleaned_data["usuario"], form.cleaned_data["senha"], form.cleaned_data["papel"])
        except ValidationError as erro:
            adicionar_erros(form, erro)
        else:
            messages.success(request, "Membro adicionado à equipe.")
            return redirect("core:equipe_lista")
    return _formulario(request, form, "Novo membro", "O usuário entra com o nome e a senha definidos aqui.", "Adicionar à equipe")


@require_http_methods(["GET", "POST"])
@papel_requerido("admin")
def equipe_editar(request, pk):
    perfil = _membro(request, pk)
    form = PapelForm(request.POST or None, initial={"papel": perfil.papel})
    if request.method == "POST" and form.is_valid():
        try:
            alterar_papel(perfil, form.cleaned_data["papel"])
        except ValidationError as erro:
            adicionar_erros(form, erro)
        else:
            messages.success(request, "Papel atualizado.")
            return redirect("core:equipe_lista")
    return _formulario(
        request, form, f"Papel de {perfil.usuario.username}",
        "Administrador faz tudo; operador consulta e lança.", "Salvar papel",
    )


@require_http_methods(["GET", "POST"])
@papel_requerido("admin")
def equipe_remover(request, pk):
    perfil = _membro(request, pk)
    if request.method == "POST":
        try:
            remover_membro(perfil, request.user)
        except ValidationError as erro:
            messages.error(request, " ".join(erro.messages))
        else:
            messages.success(request, "Membro removido da equipe.")
            return redirect("core:equipe_lista")
    return render(request, "financas/confirmar_exclusao.html", {
        "objeto": perfil.usuario.username, "titulo": "Remover da equipe", "secao": "equipe",
        "voltar_url": reverse("core:equipe_lista"),
        "detalhe_exclusao": "O usuário será excluído e não poderá mais entrar. Os lançamentos da organização não são afetados.",
    })
