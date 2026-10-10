from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("access_id", models.CharField(db_index=True, max_length=64)),
                ("razorpay_order_id", models.CharField(max_length=64, unique=True)),
                ("razorpay_payment_id", models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ("amount", models.PositiveIntegerField(default=49900)),
                ("currency", models.CharField(default="INR", max_length=3)),
                ("status", models.CharField(choices=[("created", "Created"), ("captured", "Captured")], default="created", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("captured_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
    ]
