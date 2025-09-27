# tracker/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    Profile, Movie, Genre, Actor, Cinematographer, 
    Director, Producer, UserMovieView
)

# User and Profile admin classes remain the same...
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ('date_of_birth', 'join_date', 'last_activity',)
    readonly_fields = ('join_date', 'last_activity',)
    max_num = 1
    min_num = 1

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# --- STEP 1: CREATE ADMIN CLASSES FOR THE MODELS YOU WANT TO SEARCH ---
# These tell the autocomplete widget WHICH field to search on (the 'name' field).

@admin.register(Actor)
class ActorAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(Director)
class DirectorAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(Producer)
class ProducerAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(Cinematographer)
class CinematographerAdmin(admin.ModelAdmin):
    search_fields = ('name',)


# --- STEP 2: UPDATE THE MOVIEADMIN TO USE AUTOCOMPLETE ---
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'release_year', 'runtime_minutes', 'revenue')
    list_filter = ('release_year', 'genre')
    search_fields = ('title',)
    
    # Replace raw_id_fields with autocomplete_fields
    autocomplete_fields = ('actors', 'cinematographers', 'directors', 'producers')

    filter_horizontal = ('genre',)

    fieldsets = (
        ('Core Information', {
            'fields': ('title', 'release_year', 'plot_summary')
        }),
        ('Statistics & Metadata', {
            'fields': ('runtime_minutes', 'revenue', 'poster_url')
        }),
        ('External IDs (Read-Only)', {
            'classes': ('collapse',),
            'fields': ('imdb_id', 'tmdb_id'),
        }),
        ('Personnel & Genre', {
            'fields': ('genre', 'directors', 'producers', 'actors', 'cinematographers')
        }),
    )

    readonly_fields = ('imdb_id', 'tmdb_id')


# Register the remaining models that don't need custom admins
admin.site.register(Genre)
admin.site.register(UserMovieView)
