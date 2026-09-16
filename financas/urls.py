from django.urls import path

from . import views


app_name = "financas"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("contas/", views.conta_lista, name="conta_lista"),
    path("contas/nova/", views.conta_criar, name="conta_criar"),
    path("contas/<int:pk>/editar/", views.conta_editar, name="conta_editar"),
    path("contas/<int:pk>/excluir/", views.conta_excluir, name="conta_excluir"),
    path("categorias/", views.categoria_lista, name="categoria_lista"),
    path("categorias/nova/", views.categoria_criar, name="categoria_criar"),
    path("categorias/<int:pk>/editar/", views.categoria_editar, name="categoria_editar"),
    path("categorias/<int:pk>/excluir/", views.categoria_excluir, name="categoria_excluir"),
    path("lancamentos/", views.lancamento_lista, name="lancamento_lista"),
    path("lancamentos/novo/", views.lancamento_criar, name="lancamento_criar"),
    path("lancamentos/<int:pk>/", views.lancamento_detalhe, name="lancamento_detalhe"),
    path("lancamentos/<int:pk>/editar/", views.lancamento_editar, name="lancamento_editar"),
    path("lancamentos/<int:pk>/excluir/", views.lancamento_excluir, name="lancamento_excluir"),
    path("orcamentos/", views.orcamento_lista, name="orcamento_lista"),
    path("orcamentos/novo/", views.orcamento_criar, name="orcamento_criar"),
    path("orcamentos/<int:pk>/editar/", views.orcamento_editar, name="orcamento_editar"),
    path("orcamentos/<int:pk>/excluir/", views.orcamento_excluir, name="orcamento_excluir"),
    path("parcelas/<int:pk>/editar/", views.parcela_editar, name="parcela_editar"),
]
