from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("financial_reporting", "0002_workspace_label")]

    operations = [
        migrations.DeleteModel(name="FinancialReportingWorkspace"),
        migrations.CreateModel(
            name="GenerateFinancialReportWorkspace",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))],
            options={
                "verbose_name": "Generate Financial Reports",
                "verbose_name_plural": "Generate Financial Reports",
                "managed": False,
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="DepreciationScheduleWorkspace",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))],
            options={
                "verbose_name": "Depreciation Schedule",
                "verbose_name_plural": "Depreciation Schedule",
                "managed": False,
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="BankStatementWorkspace",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))],
            options={
                "verbose_name": "Bank Statement PDF Parsing",
                "verbose_name_plural": "Bank Statement PDF Parsing",
                "managed": False,
                "default_permissions": (),
            },
        ),
    ]
