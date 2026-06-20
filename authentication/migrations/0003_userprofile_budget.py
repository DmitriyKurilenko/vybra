from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_auth_user_email_ci_unique_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='budget',
            field=models.PositiveIntegerField(default=15000),
        ),
    ]
