# Generated by Django 4.2.4 on 2023-11-24 13:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bridge", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="omerouser",
            name="omero_password",
            field=models.CharField(
                default="ff",
                help_text="The password for the omero user",
                max_length=2000,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="omerouser",
            name="omero_username",
            field=models.CharField(
                default="ff",
                help_text="The username for the omero user",
                max_length=2000,
            ),
            preserve_default=False,
        ),
    ]
