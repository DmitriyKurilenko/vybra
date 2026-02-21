from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('wishlist', '0005_rename_wishlist_im_user_id_36fef0_idx_wishlist_im_user_id_819db7_idx_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category', 'price'], name='wishlist_pr_categor_95277c_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['price'], name='wishlist_pr_price_6f2049_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category'], name='wishlist_pr_categor_e67ef3_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(condition=Q(price__isnull=False), fields=['price'], name='wishlist_pr_valid_price_idx'),
        ),
    ]
