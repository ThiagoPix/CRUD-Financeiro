import django.db.models.expressions
import django.db.models.functions.math
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financas', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='lancamento',
            name='lancamento_minimo_por_parcela',
        ),
        migrations.AddConstraint(
            model_name='lancamento',
            constraint=models.CheckConstraint(condition=models.Q(('valor_total__gte', django.db.models.functions.math.Round(django.db.models.expressions.CombinedExpression(models.F('quantidade_parcelas'), '*', models.Value(Decimal('0.01'))), precision=2))), name='lancamento_minimo_por_parcela'),
        ),
    ]
