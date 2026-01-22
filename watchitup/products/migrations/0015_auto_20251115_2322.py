from django.db import migrations
import uuid

def generate_unique_uuids(apps, schema_editor):
    Cart = apps.get_model('products', 'Cart')  # <-- Cart model from products app
    for cart in Cart.objects.all():
        cart.uuid = uuid.uuid4()
        cart.save()

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0014_alter_orderreturn_status'),
    ]

    operations = [
        migrations.RunPython(generate_unique_uuids),
    ]
