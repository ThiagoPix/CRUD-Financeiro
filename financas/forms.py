from django import forms
from django.utils import timezone

from .models import Categoria, Conta, Lancamento, Orcamento, Parcela


MESES = [
    (1, "Janeiro"),
    (2, "Fevereiro"),
    (3, "Março"),
    (4, "Abril"),
    (5, "Maio"),
    (6, "Junho"),
    (7, "Julho"),
    (8, "Agosto"),
    (9, "Setembro"),
    (10, "Outubro"),
    (11, "Novembro"),
    (12, "Dezembro"),
]


class DataInput(forms.DateInput):
    input_type = "date"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%Y-%m-%d")


class ContaForm(forms.ModelForm):
    class Meta:
        model = Conta
        fields = ["nome", "tipo"]


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nome", "tipo"]


class LancamentoForm(forms.ModelForm):
    class Meta:
        model = Lancamento
        fields = ["descricao", "conta", "categoria", "valor_total", "data", "primeiro_vencimento", "quantidade_parcelas"]
        widgets = {
            "data": DataInput(),
            "primeiro_vencimento": DataInput(),
            "valor_total": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "quantidade_parcelas": forms.NumberInput(attrs={"min": 1, "max": 120}),
        }
        help_texts = {
            "valor_total": "Informe o valor completo, maior que zero. As parcelas serão calculadas automaticamente.",
            "primeiro_vencimento": "As próximas parcelas vencerão mensalmente, no mesmo dia quando possível.",
            "quantidade_parcelas": "Use 1 para pagamento único. Máximo de 120 parcelas.",
        }

    def clean_valor_total(self):
        valor = self.cleaned_data.get("valor_total")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor do lançamento deve ser maior que zero.")
        return valor


class OrcamentoForm(forms.ModelForm):
    mes = forms.TypedChoiceField(label="Mês", choices=MESES, coerce=int)

    class Meta:
        model = Orcamento
        fields = ["categoria", "mes", "ano", "limite"]
        widgets = {
            "ano": forms.NumberInput(attrs={"min": 1900, "max": 9999}),
            "limite": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.filter(tipo=Categoria.Tipo.DESPESA)
        if not self.instance.pk:
            hoje = timezone.localdate()
            self.initial.setdefault("mes", hoje.month)
            self.initial.setdefault("ano", hoje.year)


class ParcelaForm(forms.ModelForm):
    class Meta:
        model = Parcela
        fields = ["vencimento", "paga"]
        widgets = {"vencimento": DataInput()}


class FiltroLancamentoForm(forms.Form):
    q = forms.CharField(
        label="Buscar por descrição",
        required=False,
        max_length=200,
        widget=forms.SearchInput(attrs={"placeholder": "Ex.: mercado, aluguel..."}),
    )
    categoria = forms.ModelChoiceField(
        label="Categoria",
        queryset=Categoria.objects.all(),
        required=False,
        empty_label="Todas as categorias",
    )


class FiltroMesForm(forms.Form):
    mes = forms.TypedChoiceField(label="Mês", choices=MESES, coerce=int)
    ano = forms.IntegerField(label="Ano", min_value=1900, max_value=9999)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoje = timezone.localdate()
        self.initial.setdefault("mes", hoje.month)
        self.initial.setdefault("ano", hoje.year)
