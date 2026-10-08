from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0006_folder_structure_metadata"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="file",
            field=models.FileField(max_length=1000, upload_to="uploads/%Y/%m/%d/"),
        ),
    ]
