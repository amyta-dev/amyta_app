from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="DepreciationWorkspace",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ],
            options={
                "verbose_name": "Generate Depreciation Schedule",
                "verbose_name_plural": "Depreciation Schedule",
                "managed": False,
                "default_permissions": (),
            },
        ),
    ]
