from django.contrib.auth.decorators import login_not_required
from django.urls import path

from . import api_views

urlpatterns = [
    path("contas/", login_not_required(api_views.ContaListCreate.as_view()), name="api_conta_lista"),
    path("contas/<int:pk>/", login_not_required(api_views.ContaDetail.as_view()), name="api_conta_detalhe"),
    path("categorias/", login_not_required(api_views.CategoriaListCreate.as_view()), name="api_categoria_lista"),
    path("categorias/<int:pk>/", login_not_required(api_views.CategoriaDetail.as_view()), name="api_categoria_detalhe"),
]
