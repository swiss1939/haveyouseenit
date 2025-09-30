# In tracker/migrations/0012_enable_trigram_extension.py

from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('tracker', '0011_invitecode_friendship'), # Make sure this matches your previous migration
    ]

    operations = [
        TrigramExtension(),
    ]