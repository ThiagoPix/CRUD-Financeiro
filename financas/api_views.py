from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError, Q
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from core.api import AdminEscreveOperadorLe, AdminExcluiOperadorEscreve, OrganizacaoMixin, TemPerfil

from .models import Categoria, Conta, Lancamento, Orcamento, Parcela
from .serializers import (
    CategoriaSerializer, ContaSerializer, LancamentoSerializer, OrcamentoSerializer, ParcelaSerializer,
    detalhe_do_erro,
)
from .services import excluir_lancamento


class ProtegidoContraExclusao:
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Este registro está vinculado a lançamentos ou orçamentos e não pode ser excluído.")


class ContaListCreate(OrganizacaoMixin, generics.ListCreateAPIView):
    queryset = Conta.objects.com_saldo()
    serializer_class = ContaSerializer
    permission_classes = [AdminEscreveOperadorLe]


class ContaDetail(OrganizacaoMixin, ProtegidoContraExclusao, generics.RetrieveUpdateDestroyAPIView):
    queryset = Conta.objects.com_saldo()
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


class LancamentoQuerysetMixin(OrganizacaoMixin):
    queryset = Lancamento.objects.select_related("conta", "categoria").prefetch_related("parcelas")
    serializer_class = LancamentoSerializer
    permission_classes = [AdminExcluiOperadorEscreve]


class LancamentoListCreate(LancamentoQuerysetMixin, generics.ListCreateAPIView):
    def get_queryset(self):
        lancamentos = super().get_queryset()
        busca = self.request.query_params.get("q", "").strip()
        categoria = self.request.query_params.get("categoria", "").strip()
        criterios = Q()
        if busca:
            criterios &= Q(descricao__icontains=busca)
        if categoria.isdigit():
            criterios &= Q(categoria_id=int(categoria))
        return lancamentos.filter(criterios)


class LancamentoDetail(LancamentoQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    def perform_destroy(self, instance):
        try:
            excluir_lancamento(instance)
        except DjangoValidationError as erro:
            raise ValidationError(detalhe_do_erro(erro))


class OrcamentoListCreate(OrganizacaoMixin, generics.ListCreateAPIView):
    queryset = Orcamento.objects.select_related("categoria")
    serializer_class = OrcamentoSerializer
    permission_classes = [AdminEscreveOperadorLe]

    def get_queryset(self):
        orcamentos = super().get_queryset()
        for campo in ("mes", "ano"):
            valor = self.request.query_params.get(campo, "")
            if valor.isdigit():
                orcamentos = orcamentos.filter(**{campo: int(valor)})
        return orcamentos


class OrcamentoDetail(OrganizacaoMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Orcamento.objects.select_related("categoria")
    serializer_class = OrcamentoSerializer
    permission_classes = [AdminEscreveOperadorLe]


class ParcelaDetail(generics.RetrieveUpdateAPIView):
    serializer_class = ParcelaSerializer
    permission_classes = [TemPerfil]

    def get_queryset(self):
        return Parcela.objects.select_related("lancamento").filter(
            lancamento__organizacao=self.request.user.perfil.organizacao
        )
