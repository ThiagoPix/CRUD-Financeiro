from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("cadastro/", views.cadastro, name="cadastro"),
    path("equipe/", views.equipe_lista, name="equipe_lista"),
    path("equipe/novo/", views.equipe_criar, name="equipe_criar"),
    path("equipe/<int:pk>/editar/", views.equipe_editar, name="equipe_editar"),
    path("equipe/<int:pk>/remover/", views.equipe_remover, name="equipe_remover"),
]
