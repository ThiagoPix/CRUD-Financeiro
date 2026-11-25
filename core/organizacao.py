from django.core.exceptions import ObjectDoesNotExist, PermissionDenied


def org_atual(request):
    """Organização do usuário logado. Única fonte da organização em todo o sistema."""
    try:
        return request.user.perfil.organizacao
    except ObjectDoesNotExist:
        raise PermissionDenied("Seu usuário não está vinculado a uma organização.")
