"""
One-off: requests accepted before this change get their first reference photo as the item's
picture too (new acceptances do it in services.use_reference_photo). Safe to run on any data.
"""

from django.db import migrations


def link_reference_photos(apps, schema_editor):
    CustomRequest = apps.get_model("custom_requests", "CustomRequest")
    ProductImage = apps.get_model("catalog", "ProductImage")
    accepted = CustomRequest.objects.filter(status="accepted", product__isnull=False)
    for req in accepted:
        first = req.images.order_by("position").first()
        if first and not ProductImage.objects.filter(product_id=req.product_id).exists():
            ProductImage.objects.create(product_id=req.product_id, image=first.image.name, position=0)


class Migration(migrations.Migration):
    dependencies = [
        ("custom_requests", "0002_customrequest_product_customrequest_responded_at"),
        ("catalog", "0002_product_is_custom"),
    ]

    # Going back leaves the pictures in place: harmless, and nothing else depends on them.
    operations = [migrations.RunPython(link_reference_photos, migrations.RunPython.noop)]
