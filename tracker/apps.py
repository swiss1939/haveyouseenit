from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracker'
    # --- NEW CODE: Signal loading ---
    def ready(self):
        import tracker.signals  # noqa
    # ------------------------------
