from rest_framework import serializers

from .models import Categoria, Conta


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
