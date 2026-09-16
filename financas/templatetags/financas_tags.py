from decimal import Decimal

from django import template


register = template.Library()


@register.filter
def dinheiro(valor):
    valor = Decimal(valor or 0)
    formatado = f"{abs(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {formatado}"
