from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Conta(models.Model):
    class Tipo(models.TextChoices):
        CARTEIRA = "carteira", "Carteira"
        CORRENTE = "corrente", "Conta corrente"
        POUPANCA = "poupanca", "Poupança"

    nome = models.CharField("nome", max_length=100, unique=True)
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices)

    class Meta:
        ordering = ["nome"]
        verbose_name = "conta"
        verbose_name_plural = "contas"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tipo__in=["carteira", "corrente", "poupanca"]),
                name="conta_tipo_valido",
            )
        ]

    def __str__(self):
        return self.nome


class Categoria(models.Model):
    class Tipo(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"

    nome = models.CharField("nome", max_length=100, unique=True)
    tipo = models.CharField("tipo", max_length=7, choices=Tipo.choices)

    class Meta:
        ordering = ["nome"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tipo__in=["receita", "despesa"]),
                name="categoria_tipo_valido",
            )
        ]

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    def clean(self):
        super().clean()
        if self.pk:
            anterior = Categoria.objects.filter(pk=self.pk).first()
            if anterior and anterior.tipo != self.tipo:
                if self.lancamentos.exists() or self.orcamentos.exists():
                    raise ValidationError(
                        {
                            "tipo": "O tipo não pode ser alterado porque esta categoria já possui lançamentos ou orçamentos."
                        }
                    )


class Lancamento(models.Model):
    descricao = models.CharField("descrição", max_length=200)
    conta = models.ForeignKey(
        Conta, on_delete=models.PROTECT, related_name="lancamentos", verbose_name="conta"
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="lancamentos",
        verbose_name="categoria",
    )
    valor_total = models.DecimalField(
        "valor total", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    data = models.DateField("data do lançamento", default=timezone.localdate)
    primeiro_vencimento = models.DateField("primeiro vencimento", default=timezone.localdate)
    quantidade_parcelas = models.PositiveSmallIntegerField(
        "quantidade de parcelas", default=1, validators=[MinValueValidator(1), MaxValueValidator(120)]
    )

    class Meta:
        ordering = ["-data", "-pk"]
        verbose_name = "lançamento"
        verbose_name_plural = "lançamentos"
        constraints = [
            models.CheckConstraint(condition=models.Q(valor_total__gt=0), name="lancamento_valor_positivo"),
            models.CheckConstraint(
                condition=models.Q(quantidade_parcelas__gte=1, quantidade_parcelas__lte=120),
                name="lancamento_quantidade_valida",
            ),
            models.CheckConstraint(
                condition=models.Q(primeiro_vencimento__gte=models.F("data")),
                name="lancamento_vencimento_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(valor_total__gte=models.F("quantidade_parcelas") * Decimal("0.01")),
                name="lancamento_minimo_por_parcela",
            ),
        ]

    def __str__(self):
        return self.descricao

    @property
    def tipo(self):
        return self.categoria.tipo

    def get_tipo_display(self):
        return self.categoria.get_tipo_display()

    def clean(self):
        super().clean()
        erros = {}
        if self.data and self.primeiro_vencimento and self.primeiro_vencimento < self.data:
            erros["primeiro_vencimento"] = "O primeiro vencimento deve ser igual ou posterior à data do lançamento."
        if self.valor_total is not None and self.quantidade_parcelas:
            if self.valor_total < Decimal("0.01") * self.quantidade_parcelas:
                erros["quantidade_parcelas"] = "Cada parcela deve ter pelo menos R$ 0,01. Reduza a quantidade de parcelas."
        if self.primeiro_vencimento and self.quantidade_parcelas:
            ultimo_mes = self.primeiro_vencimento.year * 12 + self.primeiro_vencimento.month - 1 + self.quantidade_parcelas - 1
            if ultimo_mes // 12 > 9999:
                erros["primeiro_vencimento"] = "As parcelas devem vencer até o ano 9999."
        if self.pk:
            anterior = Lancamento.objects.filter(pk=self.pk).first()
            campos = ("conta_id", "categoria_id", "valor_total", "data", "primeiro_vencimento", "quantidade_parcelas")
            if anterior and any(getattr(anterior, campo) != getattr(self, campo) for campo in campos):
                if self.parcelas.filter(paga=True).exists():
                    erros["__all__"] = "Este lançamento possui parcelas pagas. Desmarque os pagamentos antes de alterar seus dados financeiros."
            if anterior and self.data:
                regenerar = any(
                    getattr(anterior, campo) != getattr(self, campo)
                    for campo in ("valor_total", "primeiro_vencimento", "quantidade_parcelas")
                )
                if not regenerar and self.parcelas.filter(vencimento__lt=self.data).exists():
                    erros["data"] = "A data do lançamento não pode ser posterior ao vencimento de uma de suas parcelas."
        if erros:
            raise ValidationError(erros)


class Orcamento(models.Model):
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="orcamentos",
        verbose_name="categoria",
        limit_choices_to={"tipo": Categoria.Tipo.DESPESA},
    )
    mes = models.PositiveSmallIntegerField("mês", validators=[MinValueValidator(1), MaxValueValidator(12)])
    ano = models.PositiveSmallIntegerField("ano", validators=[MinValueValidator(1900), MaxValueValidator(9999)])
    limite = models.DecimalField(
        "limite", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )

    class Meta:
        ordering = ["-ano", "-mes", "categoria__nome"]
        verbose_name = "orçamento"
        verbose_name_plural = "orçamentos"
        constraints = [
            models.UniqueConstraint(fields=["categoria", "mes", "ano"], name="orcamento_categoria_mes_ano_unico"),
            models.CheckConstraint(condition=models.Q(mes__gte=1, mes__lte=12), name="orcamento_mes_valido"),
            models.CheckConstraint(condition=models.Q(ano__gte=1900, ano__lte=9999), name="orcamento_ano_valido"),
            models.CheckConstraint(condition=models.Q(limite__gt=0), name="orcamento_limite_positivo"),
        ]

    def __str__(self):
        return f"{self.categoria.nome} — {self.mes:02d}/{self.ano}"

    def clean(self):
        super().clean()
        if self.categoria_id and self.categoria.tipo != Categoria.Tipo.DESPESA:
            raise ValidationError({"categoria": "O orçamento deve utilizar uma categoria de despesa."})


class Parcela(models.Model):
    lancamento = models.ForeignKey(
        Lancamento,
        on_delete=models.CASCADE,
        related_name="parcelas",
        verbose_name="lançamento",
    )
    numero = models.PositiveSmallIntegerField("número", validators=[MinValueValidator(1), MaxValueValidator(120)])
    valor = models.DecimalField(
        "valor", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    vencimento = models.DateField("vencimento")
    paga = models.BooleanField("parcela paga", default=False)

    class Meta:
        ordering = ["numero"]
        verbose_name = "parcela"
        verbose_name_plural = "parcelas"
        constraints = [
            models.UniqueConstraint(fields=["lancamento", "numero"], name="parcela_lancamento_numero_unico"),
            models.CheckConstraint(condition=models.Q(valor__gt=0), name="parcela_valor_positivo"),
            models.CheckConstraint(condition=models.Q(numero__gte=1, numero__lte=120), name="parcela_numero_valido"),
        ]

    def __str__(self):
        return f"{self.lancamento.descricao} — {self.numero}/{self.lancamento.quantidade_parcelas}"

    def clean(self):
        super().clean()
        if self.lancamento_id:
            if self.vencimento and self.vencimento < self.lancamento.data:
                raise ValidationError({"vencimento": "O vencimento deve ser igual ou posterior à data do lançamento."})
            if self.numero and self.numero > self.lancamento.quantidade_parcelas:
                raise ValidationError("O número da parcela excede a quantidade definida no lançamento.")
