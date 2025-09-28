# tracker/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler: Creates a Profile object whenever a new User object is created.
    """
    if created:
        # --- FIX #3: Change to get_or_create to prevent race conditions with the form ---
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal handler: Ensures the Profile object is saved whenever the User object is saved.
    """
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        pass