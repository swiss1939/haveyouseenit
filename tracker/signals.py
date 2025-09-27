# tracker/models.py (Add this section at the very bottom)

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
# The other imports (Profile, etc.) are already at the top of the file

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler: Creates a Profile object whenever a new User object is created.
    This ensures that built-in users (like superusers) also get a Profile.
    """
    if created:
        # Check if a profile already exists for safety, then create it
        if not hasattr(instance, 'profile'):
            Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal handler: Ensures the Profile object is saved whenever the User object is saved.
    """
    # Use try-except because the signal is fired during superuser creation before the profile exists
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        # If the Profile hasn't been created yet (e.g., in a race condition), ignore or handle gracefully.
        pass
