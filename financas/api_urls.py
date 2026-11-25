from django.contrib.auth.decorators import login_not_required
from django.urls import path

from . import api_dashboard, api_views

urlpatterns = [
    path("contas/", login_not_required(api_views.ContaListCreate.as_view()), name="api_conta_lista"),
    path("contas/<int:pk>/", login_not_required(api_views.ContaDetail.as_view()), name="api_conta_detalhe"),
    path("categorias/", login_not_required(api_views.CategoriaListCreate.as_view()), name="api_categoria_lista"),
    path("categorias/<int:pk>/", login_not_required(api_views.CategoriaDetail.as_view()), name="api_categoria_detalhe"),
    path("lancamentos/", login_not_required(api_views.LancamentoListCreate.as_view()), name="api_lancamento_lista"),
    path("lancamentos/<int:pk>/", login_not_required(api_views.LancamentoDetail.as_view()), name="api_lancamento_detalhe"),
    path("orcamentos/", login_not_required(api_views.OrcamentoListCreate.as_view()), name="api_orcamento_lista"),
    path("orcamentos/<int:pk>/", login_not_required(api_views.OrcamentoDetail.as_view()), name="api_orcamento_detalhe"),
    path("parcelas/<int:pk>/", login_not_required(api_views.ParcelaDetail.as_view()), name="api_parcela_detalhe"),
    path("dashboard/", login_not_required(api_dashboard.DashboardApi.as_view()), name="api_dashboard"),
]
