from django.contrib import admin

from .forms import CategoriaForm, ContaForm, OrcamentoForm
from .models import Categoria, Conta, Lancamento, Orcamento, Parcela


class SemExclusaoEmLoteAdmin(admin.ModelAdmin):
    actions = None


@admin.register(Conta)
class ContaAdmin(SemExclusaoEmLoteAdmin):
    form = ContaForm
    list_display = ("nome", "tipo")
    search_fields = ("nome",)
    list_filter = ("tipo",)


@admin.register(Categoria)
class CategoriaAdmin(SemExclusaoEmLoteAdmin):
    form = CategoriaForm
    list_display = ("nome", "tipo")
    search_fields = ("nome",)
    list_filter = ("tipo",)


@admin.register(Orcamento)
class OrcamentoAdmin(SemExclusaoEmLoteAdmin):
    form = OrcamentoForm
    list_display = ("categoria", "mes", "ano", "limite")
    list_filter = ("ano", "mes", "categoria")


class ConsultaAdmin(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Lancamento)
class LancamentoAdmin(ConsultaAdmin):
    list_display = ("descricao", "conta", "categoria", "valor_total", "data", "quantidade_parcelas")
    list_filter = ("categoria__tipo", "conta", "categoria")
    search_fields = ("descricao",)


@admin.register(Parcela)
class ParcelaAdmin(ConsultaAdmin):
    list_display = ("lancamento", "numero", "valor", "vencimento", "paga")
    list_filter = ("paga", "vencimento")
    search_fields = ("lancamento__descricao",)
