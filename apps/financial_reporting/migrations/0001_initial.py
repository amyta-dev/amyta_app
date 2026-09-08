from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="FinancialReportingWorkspace",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ],
            options={
                "verbose_name": "Generate Financial Reports",
                "verbose_name_plural": "Financial Report Generator",
                "managed": False,
                "default_permissions": (),
            },
        ),
    ]
