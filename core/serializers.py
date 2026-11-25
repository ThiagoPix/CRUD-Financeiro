from rest_framework import serializers

from .models import Organizacao, Perfil


class OrganizacaoSerializer(serializers.ModelSerializer):
    membros = serializers.SerializerMethodField()

    class Meta:
        model = Organizacao
        fields = ["id", "nome", "criada_em", "membros"]

    def get_membros(self, organizacao):
        return organizacao.perfis.count()


class MembroSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username", read_only=True)

    class Meta:
        model = Perfil
        fields = ["id", "usuario", "papel"]


class PapelSerializer(serializers.Serializer):
    papel = serializers.ChoiceField(choices=Perfil.PAPEIS)


class MembroCriarSerializer(serializers.Serializer):
    usuario = serializers.CharField(max_length=150)
    senha = serializers.CharField(write_only=True, trim_whitespace=False)
    papel = serializers.ChoiceField(choices=Perfil.PAPEIS, default=Perfil.OPERADOR)


class CadastroSerializer(serializers.Serializer):
    organizacao = serializers.CharField(max_length=120)
    usuario = serializers.CharField(max_length=150)
    senha = serializers.CharField(write_only=True, trim_whitespace=False)
