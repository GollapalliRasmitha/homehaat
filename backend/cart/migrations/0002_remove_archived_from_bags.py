"""
One-off: products archived before the fix stayed in bags (flagged "unavailable"). Archiving now removes them
from every bag (catalog.views.MyProductDetail.destroy), so clean up the ones archived earlier. Safe to re-run.
"""

from django.db import migrations


def remove_archived(apps, schema_editor):
    CartItem = apps.get_model("cart", "CartItem")
    CartItem.objects.filter(product__is_archived=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cart", "0001_initial"),
        ("catalog", "0003_product_is_archived"),
    ]

    operations = [migrations.RunPython(remove_archived, migrations.RunPython.noop)]
