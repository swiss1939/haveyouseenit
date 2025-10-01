# tracker/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
# **MODIFICATION**: Added MovieCastCredit
from .models import (
    Profile, Movie, Genre, Actor, Cinematographer,
    Director, Producer, UserMovieView, InviteCode, Friendship, MovieCastCredit
)

# --- User and Profile Admin (No changes here) ---
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


# --- Movie and Person Admin ---

# **NEW CLASS**
# This defines the inline editor for the cast on the Movie admin page.
class MovieCastCreditInline(admin.TabularInline):
    model = MovieCastCredit
    fields = ('actor', 'order')
    autocomplete_fields = ('actor',)
    extra = 1 # Provides one extra slot for adding an actor.


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


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'release_year', 'runtime_minutes', 'revenue')
    list_filter = ('release_year', 'genre')
    search_fields = ('title',)
    
    # **MODIFICATION**: Removed 'actors'
    autocomplete_fields = ('cinematographers', 'directors', 'producers')
    filter_horizontal = ('genre',)
    
    fieldsets = (
        ('Core Information', {'fields': ('title', 'release_year', 'plot_summary')}),
        ('Statistics & Metadata', {'fields': ('runtime_minutes', 'revenue', 'poster_url', 'collection_id', 'collection_name')}),
        ('External IDs (Read-Only)', {'classes': ('collapse',), 'fields': ('imdb_id', 'tmdb_id')}),
        # **MODIFICATION**: Removed 'actors'
        ('Personnel & Genre', {'fields': ('genre', 'directors', 'producers', 'cinematographers')}),
    )
    readonly_fields = ('imdb_id', 'tmdb_id')
    
    # **MODIFICATION**: Added the new inline class
    inlines = [MovieCastCreditInline]


# --- Admin Interfaces for Invite Codes and Friendships ---

@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    """Admin interface for managing invite codes."""
    list_display = ('code', 'generated_by', 'used_by', 'created_at', 'used_at')
    list_filter = ('generated_by', 'used_by')
    search_fields = ('code', 'generated_by__username', 'used_by__username')
    readonly_fields = ('code', 'used_by', 'created_at', 'used_at')

@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    """Admin interface for managing friendships."""
    list_display = ('from_user', 'to_user', 'status', 'created_at', 'accepted_at')
    list_filter = ('status',)
    search_fields = ('from_user__username', 'to_user__username')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            try:
                reciprocal_friendship = Friendship.objects.get(
                    from_user=obj.to_user,
                    to_user=obj.from_user
                )
                reciprocal_friendship.status = obj.status
                reciprocal_friendship.accepted_at = obj.accepted_at
                reciprocal_friendship.save()
            except Friendship.DoesNotExist:
                pass


# Register remaining models
admin.site.register(Genre)
admin.site.register(UserMovieView)