from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("Stock", "0005_auto_20261010_1537"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Payment",
        ),
    ]
