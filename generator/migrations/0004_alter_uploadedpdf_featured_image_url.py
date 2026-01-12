# Generated manually to fix NOT NULL constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('generator', '0003_uploadedpdf_domain_uploadedpdf_featured_image_url_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uploadedpdf',
            name='featured_image_url',
            field=models.URLField(blank=True, max_length=2000, null=True),
        ),
    ]


