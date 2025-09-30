# tracker/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Profile, InviteCode

# 1. Define the custom signal
milestone_reached = Signal()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler: Creates a Profile object whenever a new User object is created.
    """
    if created:
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

# 2. Create the receiver for the custom signal (replaces the previous UserMovieView signal)
@receiver(milestone_reached)
def grant_invite_codes_and_message(sender, user, total_rated, **kwargs):
    """
    Listens for the custom milestone_reached signal to grant codes and create a message.
    """
    request = kwargs.get('request')
    if not request:
        return

    # Milestone 1: Grant 5 codes for the first 250 movies rated.
    if total_rated == 250:
        for _ in range(5):
            InviteCode.objects.create(generated_by=user)
        messages.success(request, "Congratulations! You've rated 250 movies and earned 5 invite codes!")

    # Milestone 2: Grant 1 code for every 100 movies rated after 250.
    elif total_rated > 250 and (total_rated - 250) % 100 == 0:
        InviteCode.objects.create(generated_by=user)
        messages.success(request, f"Congratulations! You've rated {total_rated} movies and earned a new invite code!")