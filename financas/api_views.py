from django.db.models import ProtectedError
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from core.api import AdminEscreveOperadorLe, OrganizacaoMixin

from .models import Categoria, Conta
from .serializers import CategoriaSerializer, ContaSerializer


class ProtegidoContraExclusao:
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Este registro está vinculado a lançamentos ou orçamentos e não pode ser excluído.")


class ContaListCreate(OrganizacaoMixin, generics.ListCreateAPIView):
    queryset = Conta.objects.all()
    serializer_class = ContaSerializer
    permission_classes = [AdminEscreveOperadorLe]


class ContaDetail(OrganizacaoMixin, ProtegidoContraExclusao, generics.RetrieveUpdateDestroyAPIView):
    queryset = Conta.objects.all()
    serializer_class = ContaSerializer
    permission_classes = [AdminEscreveOperadorLe]


class CategoriaListCreate(OrganizacaoMixin, generics.ListCreateAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [AdminEscreveOperadorLe]


class CategoriaDetail(OrganizacaoMixin, ProtegidoContraExclusao, generics.RetrieveUpdateDestroyAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [AdminEscreveOperadorLe]
