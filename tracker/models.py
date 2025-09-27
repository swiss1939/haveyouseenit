from django.db import models
from django.contrib.auth.models import User

# --- 1. Supporting Tables (For Stats) ---

class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
class Actor(models.Model):
    name = models.CharField(max_length=255, unique=True)
    imdb_id = models.CharField(max_length=15, unique=True, null=True, blank=True)
    tmdb_id = models.IntegerField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.name

class Cinematographer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    imdb_id = models.CharField(max_length=15, unique=True, null=True, blank=True)
    tmdb_id = models.IntegerField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.name
    
class Director(models.Model):
    name = models.CharField(max_length=255, unique=True)
    imdb_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    tmdb_id = models.IntegerField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.name

class Producer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    imdb_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    tmdb_id = models.IntegerField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.name


# --- 2. Core Tables ---

class Movie(models.Model):
    title = models.CharField(max_length=255)
    release_year = models.IntegerField()
    runtime_minutes = models.IntegerField(null=True, blank=True)
    revenue = models.BigIntegerField(default=0)
    plot_summary = models.TextField(null=True, blank=True)
    imdb_id = models.CharField(max_length=15, unique=True, null=True, blank=True)
    tmdb_id = models.IntegerField(unique=True, null=True, blank=True)
    poster_url = models.URLField(max_length=500, null=True, blank=True)

    # Relationships
    genre = models.ManyToManyField(Genre)
    actors = models.ManyToManyField(Actor)
    cinematographers = models.ManyToManyField(Cinematographer)
    directors = models.ManyToManyField(Director)
    producers = models.ManyToManyField(Producer)


    def __str__(self):
        return f"{self.title} ({self.release_year})"
    
    def get_decade(self):
        """Calculates the movie's release decade."""
        return (self.release_year // 10) * 10
    
class UserMovieView(models.Model):
    """Tracks a user's seen/unseen choice for a specific movie."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    
    # The core data point
    has_seen = models.BooleanField(default=False) 
    
    date_recorded = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Enforces that a user can only have one viewing record per movie
        unique_together = ('user', 'movie')
        
    def __str__(self):
        status = "Seen" if self.has_seen else "Unseen"
        return f"{self.user.username} - {self.movie.title} ({status})"

class Profile(models.Model):
    """Extends the default Django User model and stores additional user data."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # --- NEW FIELDS FOR SIGNUP ---
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Cached Stats
    join_date = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"
