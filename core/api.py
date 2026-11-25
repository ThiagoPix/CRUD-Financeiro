from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions


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
