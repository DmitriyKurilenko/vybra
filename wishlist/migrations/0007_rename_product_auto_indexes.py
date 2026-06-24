from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wishlist', '0006_product_indexes_for_compare_speed'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='product',
            old_name='wishlist_pr_categor_95277c_idx',
            new_name='wishlist_pr_categor_f6cdee_idx',
        ),
        migrations.RenameIndex(
            model_name='product',
            old_name='wishlist_pr_price_6f2049_idx',
            new_name='wishlist_pr_price_0f9db1_idx',
        ),
        migrations.RenameIndex(
            model_name='product',
            old_name='wishlist_pr_categor_e67ef3_idx',
            new_name='wishlist_pr_categor_ae07d3_idx',
        ),
    ]
