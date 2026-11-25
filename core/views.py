from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import CadastroForm, adicionar_erros
from .servicos import cadastrar_organizacao


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
