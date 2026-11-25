from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Categoria, Conta, Lancamento, Orcamento, Parcela
from .services import gravar_lancamento, totais_orcamento


def detalhe_do_erro(erro):
    return erro.message_dict if hasattr(erro, "error_dict") else erro.messages


def validar_modelo(instance):
    try:
        instance.full_clean()
    except DjangoValidationError as erro:
        raise serializers.ValidationError(detalhe_do_erro(erro))


class NomeUnicoPorOrganizacao:
    """Valida o nome único dentro da organização do usuário (o JSON não traz a organização)."""

    def validate_nome(self, valor):
        organizacao = self.context["request"].user.perfil.organizacao
        existentes = self.Meta.model.objects.filter(organizacao=organizacao, nome=valor)
        if self.instance is not None:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise serializers.ValidationError("Já existe um registro com este nome na sua organização.")
        return valor


class ContaSerializer(NomeUnicoPorOrganizacao, serializers.ModelSerializer):
    class Meta:
        model = Conta
        fields = ["id", "nome", "tipo"]


class CategoriaSerializer(NomeUnicoPorOrganizacao, serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nome", "tipo"]

    def validate_tipo(self, valor):
        if self.instance is not None and self.instance.tipo != valor:
            if self.instance.lancamentos.exists() or self.instance.orcamentos.exists():
                raise serializers.ValidationError(
                    "O tipo não pode ser alterado porque esta categoria já possui lançamentos ou orçamentos."
                )
        return valor


class ParcelaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcela
        fields = ["id", "lancamento", "numero", "valor", "vencimento", "paga"]
        read_only_fields = ["lancamento", "numero", "valor"]

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        validar_modelo(instance)
        instance.save()
        return instance


class LancamentoSerializer(serializers.ModelSerializer):
    tipo = serializers.CharField(read_only=True)
    parcelas = ParcelaSerializer(many=True, read_only=True)

    class Meta:
        model = Lancamento
        fields = ["id", "descricao", "conta", "categoria", "tipo", "valor_total", "data",
                  "primeiro_vencimento", "quantidade_parcelas", "parcelas"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated and hasattr(request.user, "perfil"):
            organizacao = request.user.perfil.organizacao
            self.fields["conta"].queryset = Conta.objects.filter(organizacao=organizacao)
            self.fields["categoria"].queryset = Categoria.objects.filter(organizacao=organizacao)

    def validate_valor_total(self, valor):
        if valor <= 0:
            raise serializers.ValidationError("O valor do lançamento deve ser maior que zero.")
        return valor

    def create(self, validated_data):
        return self.gravar(Lancamento(**validated_data))

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        return self.gravar(instance)

    def gravar(self, lancamento):
        try:
            return gravar_lancamento(lancamento)
        except DjangoValidationError as erro:
            raise serializers.ValidationError(detalhe_do_erro(erro))


class OrcamentoSerializer(serializers.ModelSerializer):
    resumo = serializers.SerializerMethodField()

    class Meta:
        model = Orcamento
        fields = ["id", "categoria", "mes", "ano", "limite", "resumo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated and hasattr(request.user, "perfil"):
            self.fields["categoria"].queryset = Categoria.objects.filter(
                organizacao=request.user.perfil.organizacao, tipo=Categoria.Tipo.DESPESA
            )

    def get_resumo(self, orcamento):
        return {chave: valor if isinstance(valor, bool) else str(valor)
                for chave, valor in totais_orcamento(orcamento).items()}

    def validate(self, dados):
        organizacao = self.context["request"].user.perfil.organizacao
        categoria = dados.get("categoria", getattr(self.instance, "categoria", None))
        mes = dados.get("mes", getattr(self.instance, "mes", None))
        ano = dados.get("ano", getattr(self.instance, "ano", None))
        duplicados = Orcamento.objects.filter(organizacao=organizacao, categoria=categoria, mes=mes, ano=ano)
        if self.instance is not None:
            duplicados = duplicados.exclude(pk=self.instance.pk)
        if duplicados.exists():
            raise serializers.ValidationError("Já existe um orçamento para esta categoria neste mês e ano.")
        return dados
