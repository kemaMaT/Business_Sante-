# Generated by Django 5.2 on 2025-04-13 11:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_customuser_solde'),
    ]

    operations = [
        migrations.AddField(
            model_name='produit',
            name='gain',
            field=models.DecimalField(decimal_places=2, default=1, max_digits=10),
            preserve_default=False,
        ),
    ]
