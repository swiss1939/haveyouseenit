# tracker/views.py

import random
import json
from django.db.models import Q
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from .models import Movie, UserMovieView, Profile, Genre, InviteCode, Friendship, MovieCastCredit, Actor, Director, Producer, Cinematographer
from .forms import CustomUserCreationForm, ProfileUpdateForm
from .signals import milestone_reached
from django.http import JsonResponse, HttpResponseBadRequest, Http404
from django.template.loader import render_to_string
from django.contrib.auth import login, logout
from django.contrib import messages


def get_weighted_random_movie(unseen_movies):
    tiers = { "tentpole": (300_000_000, None), "major": (75_000_000, 300_000_000), "mid": (10_000_000, 75_000_000), "low": (1_000_000, 10_000_000), "micro": (None, 1_000_000), }
    tier_weights = {"tentpole": 45, "major": 30, "mid": 15, "low": 7, "micro": 3}
    if not unseen_movies.exists(): return None
    chosen_tier_name = random.choices(list(tiers.keys()), weights=list(tier_weights.values()), k=1)[0]
    min_rev, max_rev = tiers[chosen_tier_name]
    movie_query = unseen_movies
    if min_rev is not None: movie_query = movie_query.filter(revenue__gte=min_rev)
    if max_rev is not None: movie_query = movie_query.filter(revenue__lt=max_rev)
    return movie_query.order_by('?').first()

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('next_movie')
    template_name = 'registration/signup.html'

    def get_initial(self):
        initial = super().get_initial()
        invite_code = self.kwargs.get('invite_code')
        if invite_code:
            initial['invite_code'] = invite_code.upper()
        return initial

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        inactive_user = User.objects.filter(email__iexact=email, is_active=False).first()
        if inactive_user:
            user = inactive_user
            user.username = form.cleaned_data['username']
            user.set_password(form.cleaned_data['password2'])
            user.is_active = True
            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.profile.date_of_birth = form.cleaned_data.get('date_of_birth')
            user.save()
            user.profile.save()
            messages.success(self.request, "Welcome back! Your account has been reactivated.")
            login(self.request, user)
            return redirect('next_movie')
        else:
            response = super().form_valid(form)
            login(self.request, self.object)
            return response

@login_required
def next_movie_view(request):
    user = request.user
    if request.method == 'POST':
        movie_id = request.POST.get('movie_id'); has_seen_status = request.POST.get('has_seen') == 'True'; movie = get_object_or_404(Movie, id=movie_id)
        try:
            with transaction.atomic():
                _, created = UserMovieView.objects.get_or_create(user=user, movie=movie, defaults={'has_seen': has_seen_status})
                if created:
                    total_rated = UserMovieView.objects.filter(user=user).count()
                    if total_rated == 250 or (total_rated > 250 and (total_rated - 250) % 100 == 0):
                        milestone_reached.send(sender=user.__class__, user=user, total_rated=total_rated, request=request)
                profile = user.profile; profile.last_activity = timezone.now(); profile.save()
        except IntegrityError: pass
        redirect_url = reverse('next_movie')
        genre_id = request.POST.get('genre'); person_query = request.POST.get('person_query', '').strip(); params = []
        if genre_id: params.append(f'genre={genre_id}')
        if person_query: params.append(f'person_query={person_query}')
        if params: redirect_url += '?' + '&'.join(params)
        return redirect(redirect_url)
    viewed_movie_ids = UserMovieView.objects.filter(user=user).values_list('movie_id', flat=True); unseen_movies = Movie.objects.exclude(id__in=viewed_movie_ids)
    genre_id = request.GET.get('genre'); person_query = request.GET.get('person_query', '').strip()
    if genre_id: unseen_movies = unseen_movies.filter(genre__id=genre_id)
    if person_query: unseen_movies = unseen_movies.filter(Q(actors__name__icontains=person_query) | Q(directors__name__icontains=person_query) | Q(producers__name__icontains=person_query) | Q(cinematographers__name__icontains=person_query)).distinct()
    next_movie = get_weighted_random_movie(unseen_movies)
    if not next_movie: next_movie = unseen_movies.order_by('?').first()
    total_seen_movies = UserMovieView.objects.filter(user=user, has_seen=True).count()
    context = { 'page_context': 'rating', 'total_seen_movies': total_seen_movies, 'all_genres': Genre.objects.all().order_by('name'), 'active_genre_id': int(genre_id) if genre_id else None, 'active_person_query': person_query, }
    if next_movie: context['movie'] = next_movie
    else: context['no_movies_left'] = True
    return render(request, 'tracker/movie_display.html', context)

@login_required
def profile_view(request, username=None):
    current_user = request.user
    profile_owner = get_object_or_404(User, username=username, is_active=True) if username else current_user
    is_self = (current_user == profile_owner)
    if request.method == 'POST':
        next_url = request.POST.get('next_url', reverse('my_profile'))
        if 'add_friend' in request.POST:
            user_id = request.POST.get('user_id'); to_user = get_object_or_404(User, id=user_id); Friendship.objects.get_or_create(from_user=current_user, to_user=to_user)
            return redirect(next_url)
        elif 'accept_request' in request.POST:
            request_id = request.POST.get('request_id'); friend_request = get_object_or_404(Friendship, id=request_id, to_user=current_user)
            with transaction.atomic():
                friend_request.status = Friendship.Status.ACCEPTED; friend_request.accepted_at = timezone.now(); friend_request.save()
                Friendship.objects.update_or_create(from_user=current_user, to_user=friend_request.from_user, defaults={'status': Friendship.Status.ACCEPTED, 'accepted_at': timezone.now()})
            return redirect(next_url)
        elif 'decline_request' in request.POST:
            request_id = request.POST.get('request_id'); friend_request = get_object_or_404(Friendship, id=request_id, to_user=current_user); friend_request.delete()
            return redirect(next_url)
        elif 'cancel_request' in request.POST:
            request_id = request.POST.get('request_id'); friend_request = get_object_or_404(Friendship, id=request_id, from_user=current_user); friend_request.delete()
            return redirect(next_url)
        elif 'remove_friend' in request.POST:
            friend_id_to_remove = request.POST.get('remove_friend_id')
            if friend_id_to_remove:
                friend_to_remove = get_object_or_404(User, id=friend_id_to_remove)
                Friendship.objects.filter((Q(from_user=current_user) & Q(to_user=friend_to_remove)) | (Q(from_user=friend_to_remove) & Q(to_user=current_user))).delete()
            return redirect(next_url)
    context = { 'profile_owner': profile_owner, 'profile': profile_owner.profile, 'is_self': is_self, 'total_seen_movies': UserMovieView.objects.filter(user=profile_owner, has_seen=True).count(), 'friendship_status': None, }
    if not is_self:
        if Friendship.objects.filter(from_user=current_user, to_user=profile_owner, status='ACCEPTED').exists(): context['friendship_status'] = 'FRIENDS'
        else:
            received_request = Friendship.objects.filter(from_user=profile_owner, to_user=current_user, status='PENDING').first()
            if received_request: context['friendship_status'] = 'REQUEST_RECEIVED'; context['request_obj'] = received_request
            elif Friendship.objects.filter(from_user=current_user, to_user=profile_owner, status='PENDING').exists(): context['friendship_status'] = 'REQUEST_SENT'
            else: context['friendship_status'] = 'NOT_FRIENDS'
    if is_self or context['friendship_status'] == 'FRIENDS' or context['friendship_status'] == 'REQUEST_RECEIVED':
        context['total_rated_movies'] = UserMovieView.objects.filter(user=profile_owner).count()
    if is_self or context['friendship_status'] == 'FRIENDS':
        seen_movies_query = UserMovieView.objects.filter(user=profile_owner, has_seen=True).select_related('movie').order_by('-date_recorded');
        context['seen_movies_list'] = seen_movies_query[:12]; context['total_seen_for_paging'] = seen_movies_query.count()
        # If viewing a friend's profile, get the current user's seen movies to compare
        if not is_self:
            context['viewer_seen_movie_ids'] = set(UserMovieView.objects.filter(user=current_user, has_seen=True).values_list('movie_id', flat=True))
    if is_self:
        last_rated = UserMovieView.objects.filter(user=current_user).select_related('movie').order_by('-date_recorded');
        context['last_rated_movies'] = last_rated[:10]; context['total_last_rated'] = min(last_rated.count(), 20)
        invited_friend_ids = set(InviteCode.objects.filter(generated_by=current_user, used_by__isnull=False).values_list('used_by_id', flat=True))
        context.update({ 'available_codes': InviteCode.objects.filter(generated_by=current_user, used_by__isnull=True), 'friends_list': Friendship.objects.filter(from_user=current_user, status='ACCEPTED', to_user__is_active=True).select_related('to_user'), 'incoming_requests': Friendship.objects.filter(to_user=current_user, status='PENDING', from_user__is_active=True).select_related('from_user'), 'sent_requests': Friendship.objects.filter(from_user=current_user, status='PENDING', to_user__is_active=True).select_related('to_user'), 'invited_friend_ids': invited_friend_ids, })
    return render(request, 'tracker/profile_dashboard.html', context)

@login_required
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user; user.is_active = False; user.save(); logout(request)
        messages.success(request, "Your account has been successfully disabled. You can reactivate it by signing up again with the same email.")
        return redirect('login')
    return redirect('my_profile')

@login_required
def get_seen_movies_page(request, username, page):
    page_size = 12; start_index = (page - 1) * page_size; end_index = start_index + page_size
    user_to_fetch = get_object_or_404(User, username=username, is_active=True)
    is_self = request.user == user_to_fetch
    is_friend = Friendship.objects.filter(from_user=request.user, to_user=user_to_fetch, status='ACCEPTED').exists()
    if not (is_self or is_friend): return JsonResponse({'error': 'Unauthorized'}, status=403)
    seen_movies = UserMovieView.objects.filter(user=user_to_fetch, has_seen=True).select_related('movie').order_by('-date_recorded')[start_index:end_index]
    
    template_context = {'seen_movies_list': seen_movies}
    if not is_self and is_friend:
        template_context['viewer_seen_movie_ids'] = set(UserMovieView.objects.filter(user=request.user, has_seen=True).values_list('movie_id', flat=True))
        
    html = render_to_string('tracker/partials/seen_movies_grid.html', template_context)
    return JsonResponse({'html': html})

@login_required
def movie_detail_view(request, movie_id):
    movie = get_object_or_404(Movie.objects.prefetch_related('directors', 'producers', 'cinematographers', 'genre'), id=movie_id)
    crew = []
    top_cast = MovieCastCredit.objects.filter(movie=movie).select_related('actor').order_by('order')[:10]
    for d in movie.directors.all(): crew.append({'role': 'Director', 'name': d.name, 'id': d.id, 'role_slug': 'director'})
    for p in movie.producers.all(): crew.append({'role': 'Producer', 'name': p.name, 'id': p.id, 'role_slug': 'producer'})
    for c in movie.cinematographers.all(): crew.append({'role': 'Cinematography', 'name': c.name, 'id': c.id, 'role_slug': 'cinematographer'})
    context = {'movie': movie, 'crew': crew, 'cast': top_cast}

    if request.GET.get('from') == 'profile':
        context['show_back_link'] = True

    return render(request, 'tracker/movie_detail.html', context)

@login_required
def get_last_rated_page(request, page):
    page_size = 10; start_index = (page - 1) * page_size; end_index = start_index + page_size
    if start_index >= 20: return JsonResponse({'html': ''})
    last_rated = UserMovieView.objects.filter(user=request.user).select_related('movie').order_by('-date_recorded')[start_index:end_index]
    html = render_to_string('tracker/partials/last_rated_list.html', {'last_rated_movies': last_rated})
    return JsonResponse({'html': html})

@login_required
def update_rating(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            view_id = data.get('view_id'); new_status = data.get('new_status')
            if view_id is None or new_status is None: return HttpResponseBadRequest("Missing data")
            view = get_object_or_404(UserMovieView, id=view_id, user=request.user)
            view.has_seen = new_status; view.save()
            total_seen = UserMovieView.objects.filter(user=request.user, has_seen=True).count()
            return JsonResponse({'success': True, 'total_seen_movies': total_seen})
        except (json.JSONDecodeError, KeyError): return HttpResponseBadRequest("Invalid request")
    return HttpResponseBadRequest("Only POST method is allowed")

# --- NEW VIEWS FOR ACCOUNT DETAILS EDITING ---
@login_required
def get_account_details_form(request):
    form = ProfileUpdateForm(instance=request.user)
    html = render_to_string('tracker/partials/account_details_edit.html', {'form': form}, request=request)
    return JsonResponse({'html': html})

@login_required
def update_account_details(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            html = render_to_string('tracker/partials/account_details_display.html', {'user': request.user, 'profile': request.user.profile}, request=request)
            return JsonResponse({'success': True, 'html': html})
        else:
            html = render_to_string('tracker/partials/account_details_edit.html', {'form': form}, request=request)
            return JsonResponse({'success': False, 'html': html})
    return HttpResponseBadRequest()
# --- END NEW VIEWS ---

# --- NEW VIEW FOR PERSON DETAILS ---
@login_required
def person_detail_view(request, person_id, role):
    MODELS = {
        'actor': Actor,
        'director': Director,
        'producer': Producer,
        'cinematographer': Cinematographer,
    }
    FILTER_NAMES = {
        'actor': 'actors',
        'director': 'directors',
        'producer': 'producers',
        'cinematographer': 'cinematographers',
    }
    
    model_class = MODELS.get(role)
    if not model_class:
        raise Http404("Invalid role specified.")
        
    person = get_object_or_404(model_class, id=person_id)
    
    filter_name = FILTER_NAMES.get(role)
    movies = Movie.objects.filter(**{filter_name: person}).distinct().order_by('-release_year')

    viewer_seen_movie_ids = set(UserMovieView.objects.filter(
        user=request.user, has_seen=True
    ).values_list('movie_id', flat=True))

    context = {
        'person': person,
        'movies': movies,
        'role': role.replace('_', ' '),
        'viewer_seen_movie_ids': viewer_seen_movie_ids
    }
    
    if request.GET.get('from') == 'profile':
        context['show_back_link'] = True
    
    return render(request, 'tracker/person_detail.html', context)
# --- END NEW VIEW ---

def about_view(request):
    return render(request, 'tracker/about.html')