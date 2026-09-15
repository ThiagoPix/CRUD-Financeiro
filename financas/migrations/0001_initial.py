import django.core.validators
import django.db.models.deletion
import django.db.models.expressions
import django.utils.timezone
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, unique=True, verbose_name='nome')),
                ('tipo', models.CharField(choices=[('receita', 'Receita'), ('despesa', 'Despesa')], max_length=7, verbose_name='tipo')),
            ],
            options={
                'verbose_name': 'categoria',
                'verbose_name_plural': 'categorias',
                'ordering': ['nome'],
                'constraints': [models.CheckConstraint(condition=models.Q(('tipo__in', ['receita', 'despesa'])), name='categoria_tipo_valido')],
            },
        ),
        migrations.CreateModel(
            name='Conta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, unique=True, verbose_name='nome')),
                ('tipo', models.CharField(choices=[('carteira', 'Carteira'), ('corrente', 'Conta corrente'), ('poupanca', 'Poupança')], max_length=10, verbose_name='tipo')),
            ],
            options={
                'verbose_name': 'conta',
                'verbose_name_plural': 'contas',
                'ordering': ['nome'],
                'constraints': [models.CheckConstraint(condition=models.Q(('tipo__in', ['carteira', 'corrente', 'poupanca'])), name='conta_tipo_valido')],
            },
        ),
        migrations.CreateModel(
            name='Lancamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=200, verbose_name='descrição')),
                ('valor_total', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='valor total')),
                ('data', models.DateField(default=django.utils.timezone.localdate, verbose_name='data do lançamento')),
                ('primeiro_vencimento', models.DateField(default=django.utils.timezone.localdate, verbose_name='primeiro vencimento')),
                ('quantidade_parcelas', models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(120)], verbose_name='quantidade de parcelas')),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='lancamentos', to='financas.categoria', verbose_name='categoria')),
                ('conta', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='lancamentos', to='financas.conta', verbose_name='conta')),
            ],
            options={
                'verbose_name': 'lançamento',
                'verbose_name_plural': 'lançamentos',
                'ordering': ['-data', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='Orcamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mes', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(12)], verbose_name='mês')),
                ('ano', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1900), django.core.validators.MaxValueValidator(9999)], verbose_name='ano')),
                ('limite', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='limite')),
                ('categoria', models.ForeignKey(limit_choices_to={'tipo': 'despesa'}, on_delete=django.db.models.deletion.PROTECT, related_name='orcamentos', to='financas.categoria', verbose_name='categoria')),
            ],
            options={
                'verbose_name': 'orçamento',
                'verbose_name_plural': 'orçamentos',
                'ordering': ['-ano', '-mes', 'categoria__nome'],
            },
        ),
        migrations.CreateModel(
            name='Parcela',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(120)], verbose_name='número')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='valor')),
                ('vencimento', models.DateField(verbose_name='vencimento')),
                ('paga', models.BooleanField(default=False, verbose_name='parcela paga')),
                ('lancamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parcelas', to='financas.lancamento', verbose_name='lançamento')),
            ],
            options={
                'verbose_name': 'parcela',
                'verbose_name_plural': 'parcelas',
                'ordering': ['numero'],
            },
        ),
        migrations.AddConstraint(
            model_name='lancamento',
            constraint=models.CheckConstraint(condition=models.Q(('valor_total__gt', 0)), name='lancamento_valor_positivo'),
        ),
        migrations.AddConstraint(
            model_name='lancamento',
            constraint=models.CheckConstraint(condition=models.Q(('quantidade_parcelas__gte', 1), ('quantidade_parcelas__lte', 120)), name='lancamento_quantidade_valida'),
        ),
        migrations.AddConstraint(
            model_name='lancamento',
            constraint=models.CheckConstraint(condition=models.Q(('primeiro_vencimento__gte', models.F('data'))), name='lancamento_vencimento_valido'),
        ),
        migrations.AddConstraint(
            model_name='lancamento',
            constraint=models.CheckConstraint(condition=models.Q(('valor_total__gte', django.db.models.expressions.CombinedExpression(models.F('quantidade_parcelas'), '*', models.Value(Decimal('0.01'))))), name='lancamento_minimo_por_parcela'),
        ),
        migrations.AddConstraint(
            model_name='orcamento',
            constraint=models.UniqueConstraint(fields=('categoria', 'mes', 'ano'), name='orcamento_categoria_mes_ano_unico'),
        ),
        migrations.AddConstraint(
            model_name='orcamento',
            constraint=models.CheckConstraint(condition=models.Q(('mes__gte', 1), ('mes__lte', 12)), name='orcamento_mes_valido'),
        ),
        migrations.AddConstraint(
            model_name='orcamento',
            constraint=models.CheckConstraint(condition=models.Q(('ano__gte', 1900), ('ano__lte', 9999)), name='orcamento_ano_valido'),
        ),
        migrations.AddConstraint(
            model_name='orcamento',
            constraint=models.CheckConstraint(condition=models.Q(('limite__gt', 0)), name='orcamento_limite_positivo'),
        ),
        migrations.AddConstraint(
            model_name='parcela',
            constraint=models.UniqueConstraint(fields=('lancamento', 'numero'), name='parcela_lancamento_numero_unico'),
        ),
        migrations.AddConstraint(
            model_name='parcela',
            constraint=models.CheckConstraint(condition=models.Q(('valor__gt', 0)), name='parcela_valor_positivo'),
        ),
        migrations.AddConstraint(
            model_name='parcela',
            constraint=models.CheckConstraint(condition=models.Q(('numero__gte', 1), ('numero__lte', 120)), name='parcela_numero_valido'),
        ),
    ]
