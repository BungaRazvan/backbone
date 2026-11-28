from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mytools", "0038_alter_vehiclesession_distance_split_source_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="vehiclesession",
            name="route_points",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="GPS points with provider-neutral route signals and per-signal timestamps.",
            ),
        ),
    ]
