from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions, serializers


class TemPerfil(permissions.BasePermission):
    """Autenticado e vinculado a uma organização."""

    message = "Seu usuário não está vinculado a uma organização."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        try:
            request.user.perfil
        except ObjectDoesNotExist:
            return False
        return True


class AdminEscreveOperadorLe(TemPerfil):
    """Qualquer perfil lê; só o administrador cria, altera e exclui."""

    message = "Seu papel permite apenas consultar este recurso."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.method in permissions.SAFE_METHODS or request.user.perfil.eh_admin


class OrganizacaoMixin:
    """Toda consulta parte da organização do usuário; a organização nunca vem do JSON."""

    def get_queryset(self):
        return super().get_queryset().filter(organizacao=self.request.user.perfil.organizacao)

    def perform_create(self, serializer):
        serializer.save(organizacao=self.request.user.perfil.organizacao)


class AdminExcluiOperadorEscreve(TemPerfil):
    """Qualquer perfil lê, cria e altera; só o administrador exclui."""

    message = "Somente o administrador pode excluir este recurso."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.method != "DELETE" or request.user.perfil.eh_admin


class SomenteAdmin(TemPerfil):
    """Só o administrador da organização, para qualquer método."""

    message = "Somente o administrador pode acessar este recurso."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.perfil.eh_admin


def erro_da_api(erro):
    """Converte a ValidationError das regras (servicos.py) em erro 400 da API."""
    detalhe = erro.message_dict if hasattr(erro, "error_dict") else erro.messages
    return serializers.ValidationError(detalhe)
