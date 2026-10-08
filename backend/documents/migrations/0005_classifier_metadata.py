from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0004_alter_document_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="classification_confidence",
            field=models.FloatField(default=0.0, help_text="Classifier confidence from 0.0 to 1.0"),
        ),
        migrations.AddField(
            model_name="document",
            name="classifier_source",
            field=models.CharField(blank=True, help_text="rule, ml, ml_low_confidence, or none", max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="classifier_details",
            field=models.JSONField(blank=True, default=dict, help_text="Model alternatives and diagnostics", null=True),
        ),
    ]
