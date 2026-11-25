from django.db import migrations


MODELOS = ["Conta", "Categoria", "Lancamento", "Orcamento"]


def preencher(apps, schema_editor):
    Organizacao = apps.get_model("core", "Organizacao")
    organizacao, _ = Organizacao.objects.get_or_create(nome="Organização padrão")
    for nome in MODELOS:
        apps.get_model("financas", nome).objects.filter(organizacao__isnull=True).update(organizacao=organizacao)


class Migration(migrations.Migration):
    dependencies = [
        ("financas", "0003_organizacao_opcional"),
    ]

    operations = [
        migrations.RunPython(preencher, migrations.RunPython.noop),
    ]
