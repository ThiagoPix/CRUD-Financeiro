"""Regras de organização, usuários e papéis. Formulários e API chamam estas funções, sem duplicar regra."""
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Organizacao, Perfil


def _validar_usuario(usuario, senha):
    """Valida o nome de usuário (formato e unicidade) e a senha (validadores do Django)."""
    novo = User(username=usuario or "")
    erros = {}
    try:
        novo.full_clean(exclude=["password"])
    except ValidationError as erro:
        erros["usuario"] = erro.message_dict.get("username", [])
    try:
        password_validation.validate_password(senha or "", novo)
    except ValidationError as erro:
        erros["senha"] = erro.messages
    if erros:
        raise ValidationError({campo: mensagens for campo, mensagens in erros.items() if mensagens})
    return novo


@transaction.atomic
def cadastrar_organizacao(nome_organizacao, usuario, senha):
    """Cria a organização e o seu primeiro usuário, já como administrador."""
    erros = {}
    nome = (nome_organizacao or "").strip()
    if not nome:
        erros["organizacao"] = ["Informe o nome da organização."]
    elif Organizacao.objects.filter(nome__iexact=nome).exists():
        erros["organizacao"] = ["Já existe uma organização com este nome."]
    novo = None
    try:
        novo = _validar_usuario(usuario, senha)
    except ValidationError as erro:
        erros.update(erro.message_dict)
    if erros:
        raise ValidationError(erros)
    organizacao = Organizacao.objects.create(nome=nome)
    novo.set_password(senha)
    novo.save()
    return Perfil.objects.create(usuario=novo, organizacao=organizacao, papel=Perfil.ADMIN)
