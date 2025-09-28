# tracker/views.py

import random
from django.db.models import Q
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.db import transaction, IntegrityError
from django.utils import timezone
from .models import Movie, UserMovieView, Profile, Genre
from .forms import CustomUserCreationForm


def get_weighted_random_movie(unseen_movies):
    # This function is correct and does not need changes
    tiers = {
        "tentpole": (300_000_000, None), "major": (75_000_000, 300_000_000),
        "mid": (10_000_000, 75_000_000), "low": (1_000_000, 10_000_000),
        "micro": (None, 1_000_000),
    }
    tier_weights = {"tentpole": 45, "major": 30, "mid": 15, "low": 7, "micro": 3}
    if not unseen_movies.exists():
        return None
    chosen_tier_name = random.choices(list(tiers.keys()), weights=list(tier_weights.values()), k=1)[0]
    min_rev, max_rev = tiers[chosen_tier_name]
    movie_query = unseen_movies
    if min_rev is not None:
        movie_query = movie_query.filter(revenue__gte=min_rev)
    if max_rev is not None:
        movie_query = movie_query.filter(revenue__lt=max_rev)
    return movie_query.order_by('?').first()


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'


@login_required
def next_movie_view(request):
    user = request.user

    if request.method == 'POST':
        movie_id = request.POST.get('movie_id')
        has_seen_status = request.POST.get('has_seen') == 'True'

        # --- FIX #1: Record BOTH "seen" and "unseen" ratings ---
        # This now creates a UserMovieView record for every swipe.
        movie = get_object_or_404(Movie, id=movie_id)
        try:
            with transaction.atomic():
                UserMovieView.objects.get_or_create(
                    user=user, 
                    movie=movie, 
                    defaults={'has_seen': has_seen_status}
                )
                profile = user.profile
                profile.last_activity = timezone.now()
                profile.save()
        except IntegrityError:
            # User has already rated this movie, do nothing.
            pass
        
        # Preserve filters after a swipe
        redirect_url = reverse('next_movie')
        genre_id = request.POST.get('genre')
        person_query = request.POST.get('person_query', '').strip()
        params = []
        if genre_id:
            params.append(f'genre={genre_id}')
        if person_query:
            params.append(f'person_query={person_query}')
        if params:
            redirect_url += '?' + '&'.join(params)
        
        return redirect(redirect_url)

    # --- GET LOGIC (No changes needed here) ---
    viewed_movie_ids = UserMovieView.objects.filter(user=user).values_list('movie_id', flat=True)
    unseen_movies = Movie.objects.exclude(id__in=viewed_movie_ids)
    
    genre_id = request.GET.get('genre')
    person_query = request.GET.get('person_query', '').strip()

    if genre_id:
        unseen_movies = unseen_movies.filter(genre__id=genre_id)
    if person_query:
        unseen_movies = unseen_movies.filter(
            Q(actors__name__icontains=person_query) |
            Q(directors__name__icontains=person_query) |
            Q(producers__name__icontains=person_query) |
            Q(cinematographers__name__icontains=person_query)
        ).distinct()
    
    next_movie = get_weighted_random_movie(unseen_movies)
    if not next_movie:
        next_movie = unseen_movies.order_by('?').first()

    total_seen_movies = UserMovieView.objects.filter(user=user, has_seen=True).count()
    
    context = {
        'page_context': 'rating',
        'total_seen_movies': total_seen_movies,
        'all_genres': Genre.objects.all().order_by('name'),
        'active_genre_id': int(genre_id) if genre_id else None,
        'active_person_query': person_query,
    }

    if next_movie:
        context['movie'] = next_movie
    else:
        context['no_movies_left'] = True
        
    return render(request, 'tracker/movie_display.html', context)


@login_required
def profile_view(request):
    user = request.user
    profile = user.profile

    # --- FIX #2: Calculate both "seen" and "total rated" counts ---
    seen_movies_count = UserMovieView.objects.filter(user=user, has_seen=True).count()
    total_rated_count = UserMovieView.objects.filter(user=user).count()

    context = {
        'user': user,
        'profile': profile,
        'total_seen_movies': seen_movies_count,
        'total_rated_movies': total_rated_count, # Pass the new count to the template
    }
    
    return render(request, 'tracker/profile_dashboard.html', context)

def about_view(request):
    return render(request, 'tracker/about.html')