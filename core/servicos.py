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


def _validar_papel(papel):
    if papel not in dict(Perfil.PAPEIS):
        raise ValidationError({"papel": ["Papel inválido."]})


def _e_o_ultimo_admin(perfil):
    return not Perfil.objects.filter(
        organizacao_id=perfil.organizacao_id, papel=Perfil.ADMIN
    ).exclude(pk=perfil.pk).exists()


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


@transaction.atomic
def criar_membro(organizacao, usuario, senha, papel):
    """Cria um usuário já vinculado à organização, com o papel escolhido."""
    erros = {}
    try:
        _validar_papel(papel)
    except ValidationError as erro:
        erros.update(erro.message_dict)
    novo = None
    try:
        novo = _validar_usuario(usuario, senha)
    except ValidationError as erro:
        erros.update(erro.message_dict)
    if erros:
        raise ValidationError(erros)
    novo.set_password(senha)
    novo.save()
    return Perfil.objects.create(usuario=novo, organizacao=organizacao, papel=papel)


@transaction.atomic
def alterar_papel(perfil, papel):
    _validar_papel(papel)
    if perfil.usuario.is_superuser:
        raise ValidationError("Superusuários só podem ser alterados pelo admin do Django.")
    if perfil.papel == Perfil.ADMIN and papel != Perfil.ADMIN and _e_o_ultimo_admin(perfil):
        raise ValidationError({"papel": ["A organização precisa de pelo menos um administrador."]})
    perfil.papel = papel
    perfil.save(update_fields=["papel"])
    return perfil


@transaction.atomic
def remover_membro(perfil, removido_por):
    if perfil.usuario_id == removido_por.pk:
        raise ValidationError("Você não pode remover o seu próprio usuário.")
    if perfil.usuario.is_superuser:
        raise ValidationError("Superusuários só podem ser removidos pelo admin do Django.")
    if perfil.papel == Perfil.ADMIN and _e_o_ultimo_admin(perfil):
        raise ValidationError("A organização precisa de pelo menos um administrador.")
    perfil.usuario.delete()
