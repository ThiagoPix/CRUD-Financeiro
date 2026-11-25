from functools import wraps

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied


def papel_requerido(*papeis):
    """Libera a view só para usuários cujo perfil tenha um dos papéis informados."""

    def decorador(view):
        @wraps(view)
        def envolvida(request, *args, **kwargs):
            try:
                papel = request.user.perfil.papel
            except ObjectDoesNotExist:
                raise PermissionDenied("Seu usuário não está vinculado a uma organização.")
            if papel not in papeis:
                raise PermissionDenied("Seu papel não permite acessar esta página.")
            return view(request, *args, **kwargs)

        return envolvida

    return decorador
