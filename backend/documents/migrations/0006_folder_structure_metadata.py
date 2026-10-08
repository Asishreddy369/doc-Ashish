from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0005_classifier_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="document_year",
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="document_month",
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="organization_path",
            field=models.CharField(blank=True, db_index=True, max_length=700, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="original_relative_path",
            field=models.CharField(blank=True, max_length=700, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="folder_structure",
            field=models.JSONField(blank=True, default=dict, help_text="Folder organization mode, levels, and route diagnostics", null=True),
        ),
    ]
