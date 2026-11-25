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


class FormDaOrganizacao(forms.ModelForm):
    """A organização vem do usuário logado, nunca do formulário."""

    def __init__(self, *args, org, **kwargs):
        super().__init__(*args, **kwargs)
        self.org = org
        self.instance.organizacao = org

    def validar_nome_unico(self, nome):
        modelo = self._meta.model
        if nome and modelo.objects.filter(organizacao=self.org, nome=nome).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Já existe um registro com este nome na sua organização.")
        return nome


class ContaForm(FormDaOrganizacao):
    class Meta:
        model = Conta
        fields = ["nome", "tipo"]

    def clean_nome(self):
        return self.validar_nome_unico(self.cleaned_data.get("nome"))


class CategoriaForm(FormDaOrganizacao):
    class Meta:
        model = Categoria
        fields = ["nome", "tipo"]

    def clean_nome(self):
        return self.validar_nome_unico(self.cleaned_data.get("nome"))


class LancamentoForm(FormDaOrganizacao):
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

    def __init__(self, *args, org, **kwargs):
        super().__init__(*args, org=org, **kwargs)
        self.fields["conta"].queryset = Conta.objects.filter(organizacao=org)
        self.fields["categoria"].queryset = Categoria.objects.filter(organizacao=org)

    def clean_valor_total(self):
        valor = self.cleaned_data.get("valor_total")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor do lançamento deve ser maior que zero.")
        return valor


class OrcamentoForm(FormDaOrganizacao):
    mes = forms.TypedChoiceField(label="Mês", choices=MESES, coerce=int)

    class Meta:
        model = Orcamento
        fields = ["categoria", "mes", "ano", "limite"]
        widgets = {
            "ano": forms.NumberInput(attrs={"min": 1900, "max": 9999}),
            "limite": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        }

    def __init__(self, *args, org, **kwargs):
        super().__init__(*args, org=org, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.filter(organizacao=org, tipo=Categoria.Tipo.DESPESA)
        if not self.instance.pk:
            hoje = timezone.localdate()
            self.initial.setdefault("mes", hoje.month)
            self.initial.setdefault("ano", hoje.year)

    def clean(self):
        dados = super().clean()
        categoria, mes, ano = dados.get("categoria"), dados.get("mes"), dados.get("ano")
        if categoria and mes and ano:
            duplicado = Orcamento.objects.filter(organizacao=self.org, categoria=categoria, mes=mes, ano=ano)
            if duplicado.exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Já existe um orçamento para esta categoria neste mês e ano.")
        return dados


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
        queryset=Categoria.objects.none(),
        required=False,
        empty_label="Todas as categorias",
    )

    def __init__(self, *args, org, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.filter(organizacao=org)


class FiltroMesForm(forms.Form):
    mes = forms.TypedChoiceField(label="Mês", choices=MESES, coerce=int)
    ano = forms.IntegerField(label="Ano", min_value=1900, max_value=9999)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoje = timezone.localdate()
        self.initial.setdefault("mes", hoje.month)
        self.initial.setdefault("ano", hoje.year)
