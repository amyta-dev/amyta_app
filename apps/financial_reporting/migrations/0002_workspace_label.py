from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("financial_reporting", "0001_initial")]

    operations = [
        migrations.AlterModelOptions(
            name="financialreportingworkspace",
            options={
                "managed": False,
                "verbose_name": "Generate Financial Reports",
                "verbose_name_plural": "Generate Financial Reports",
                "default_permissions": (),
            },
        ),
    ]
