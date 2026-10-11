from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Stock", "0007_registration_phone_otp_email_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="loginotp",
            name="pending_phone",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
    ]
