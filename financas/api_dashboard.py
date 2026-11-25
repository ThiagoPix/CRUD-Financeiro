from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import TemPerfil

from .dashboard import metricas
from .forms import PeriodoForm


class DashboardApi(APIView):
    """As mesmas métricas da tela, em JSON. A série mensal é só do administrador, como na tela."""

    permission_classes = [TemPerfil]

    def get(self, request):
        form = PeriodoForm(request.query_params)
        if not form.is_valid():
            return Response(form.errors, status=400)
        perfil = request.user.perfil
        dados = metricas(perfil.organizacao, form.cleaned_data["inicio"], form.cleaned_data["fim"])
        if not perfil.eh_admin:
            dados.pop("serie")
        return Response(dados)
