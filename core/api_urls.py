from django.contrib.auth.decorators import login_not_required
from django.urls import path

from . import api_views

urlpatterns = [
    path("organizacao/", login_not_required(api_views.OrganizacaoApi.as_view()), name="api_organizacao"),
    path("equipe/", login_not_required(api_views.EquipeListCreate.as_view()), name="api_equipe_lista"),
    path("equipe/<int:pk>/", login_not_required(api_views.EquipeDetail.as_view()), name="api_equipe_detalhe"),
    path("cadastro/", login_not_required(api_views.CadastroApi.as_view()), name="api_cadastro"),
]
