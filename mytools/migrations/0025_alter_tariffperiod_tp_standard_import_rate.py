from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mytools", "0024_billingcycle"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tariffperiod",
            name="tp_standard_import_rate",
            field=models.DecimalField(
                decimal_places=5,
                help_text="Cost per kWh imported",
                max_digits=7,
            ),
        ),
    ]
