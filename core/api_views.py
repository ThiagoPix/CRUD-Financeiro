from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .api import SomenteAdmin, TemPerfil, erro_da_api
from .models import Perfil
from .serializers import (
    CadastroSerializer, MembroCriarSerializer, MembroSerializer, OrganizacaoSerializer, PapelSerializer,
)
from .servicos import alterar_papel, cadastrar_organizacao, criar_membro, remover_membro


class OrganizacaoApi(generics.RetrieveAPIView):
    """Dados da organização do usuário logado."""

    serializer_class = OrganizacaoSerializer
    permission_classes = [TemPerfil]

    def get_object(self):
        return self.request.user.perfil.organizacao


class EquipeQuerysetMixin:
    permission_classes = [SomenteAdmin]

    def get_queryset(self):
        return Perfil.objects.filter(organizacao=self.request.user.perfil.organizacao).select_related("usuario").order_by("usuario__username")


class EquipeListCreate(EquipeQuerysetMixin, generics.ListCreateAPIView):
    serializer_class = MembroSerializer

    def create(self, request, *args, **kwargs):
        entrada = MembroCriarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            perfil = criar_membro(request.user.perfil.organizacao, **entrada.validated_data)
        except DjangoValidationError as erro:
            raise erro_da_api(erro)
        return Response(MembroSerializer(perfil).data, status=status.HTTP_201_CREATED)


class EquipeDetail(EquipeQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MembroSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def partial_update(self, request, *args, **kwargs):
        perfil = self.get_object()
        entrada = PapelSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            alterar_papel(perfil, entrada.validated_data["papel"])
        except DjangoValidationError as erro:
            raise erro_da_api(erro)
        return Response(MembroSerializer(perfil).data)

    def perform_destroy(self, instance):
        try:
            remover_membro(instance, self.request.user)
        except DjangoValidationError as erro:
            raise erro_da_api(erro)


class CadastroApi(APIView):
    """Cria uma organização nova com o seu primeiro administrador. Aberta, com limite de tentativas."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "cadastro"

    def post(self, request):
        entrada = CadastroSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            dados = entrada.validated_data
            perfil = cadastrar_organizacao(dados["organizacao"], dados["usuario"], dados["senha"])
        except DjangoValidationError as erro:
            raise erro_da_api(erro)
        return Response(
            {"organizacao": perfil.organizacao.nome, "usuario": perfil.usuario.username, "papel": perfil.papel},
            status=status.HTTP_201_CREATED,
        )
