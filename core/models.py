from django.conf import settings
from django.db import models


class Organizacao(models.Model):
    nome = models.CharField("nome", max_length=120, unique=True)
    criada_em = models.DateTimeField("criada em", auto_now_add=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "organização"
        verbose_name_plural = "organizações"

    def __str__(self):
        return self.nome


class Perfil(models.Model):
    ADMIN = "admin"
    OPERADOR = "operador"
    PAPEIS = [(ADMIN, "Administrador"), (OPERADOR, "Operador")]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil", verbose_name="usuário"
    )
    organizacao = models.ForeignKey(
        Organizacao, on_delete=models.PROTECT, related_name="perfis", verbose_name="organização"
    )
    papel = models.CharField("papel", max_length=10, choices=PAPEIS, default=OPERADOR)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfis"

    @property
    def eh_admin(self):
        return self.papel == self.ADMIN

    def __str__(self):
        return f"{self.usuario} — {self.organizacao} ({self.get_papel_display()})"


class DaOrganizacao(models.Model):
    organizacao = models.ForeignKey(
        Organizacao, on_delete=models.PROTECT, verbose_name="organização"
    )

    class Meta:
        abstract = True
