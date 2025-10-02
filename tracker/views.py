import random
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
from .models import Movie, UserMovieView, Profile, Genre, InviteCode, Friendship
from .forms import CustomUserCreationForm
from .signals import milestone_reached


def get_weighted_random_movie(unseen_movies):
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

    def get_initial(self):
        initial = super().get_initial()
        invite_code = self.kwargs.get('invite_code')
        if invite_code:
            initial['invite_code'] = invite_code.upper()
        return initial


@login_required
def next_movie_view(request):
    user = request.user
    if request.method == 'POST':
        movie_id = request.POST.get('movie_id')
        has_seen_status = request.POST.get('has_seen') == 'True'
        movie = get_object_or_404(Movie, id=movie_id)
        
        try:
            with transaction.atomic():
                _, created = UserMovieView.objects.get_or_create(
                    user=user, movie=movie, defaults={'has_seen': has_seen_status}
                )
                
                if created:
                    total_rated = UserMovieView.objects.filter(user=user).count()
                    if total_rated == 250 or (total_rated > 250 and (total_rated - 250) % 100 == 0):
                        milestone_reached.send(
                            sender=user.__class__, 
                            user=user, 
                            total_rated=total_rated,
                            request=request
                        )

                profile = user.profile
                profile.last_activity = timezone.now()
                profile.save()
        except IntegrityError:
            pass
        
        redirect_url = reverse('next_movie')
        genre_id = request.POST.get('genre')
        person_query = request.POST.get('person_query', '').strip()
        params = []
        if genre_id: params.append(f'genre={genre_id}')
        if person_query: params.append(f'person_query={person_query}')
        if params: redirect_url += '?' + '&'.join(params)
        return redirect(redirect_url)

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
    context = { 'page_context': 'rating', 'total_seen_movies': total_seen_movies, 'all_genres': Genre.objects.all().order_by('name'), 'active_genre_id': int(genre_id) if genre_id else None, 'active_person_query': person_query, }
    if next_movie: context['movie'] = next_movie
    else: context['no_movies_left'] = True
    return render(request, 'tracker/movie_display.html', context)


@login_required
def profile_view(request, username=None):
    current_user = request.user
    
    if username:
        profile_owner = get_object_or_404(User, username=username)
    else:
        profile_owner = current_user
    
    profile = profile_owner.profile
    
    if request.method == 'POST':
        next_url = request.POST.get('next_url', reverse('my_profile'))

        if 'search_user' in request.POST:
            query = request.POST.get('query', '').strip()
            if query:
                existing_friend_ids = list(Friendship.objects.filter(from_user=current_user).values_list('to_user_id', flat=True))
                base_query = User.objects.exclude(id=current_user.id).exclude(id__in=existing_friend_ids)
                db_engine = settings.DATABASES['default']['ENGINE']
                if 'postgresql' in db_engine:
                    found_users = base_query.annotate(similarity=TrigramSimilarity('username', query)).filter(similarity__gt=0.15).order_by('-similarity')
                else:
                    found_users = base_query.filter(username__icontains=query)
                request.session['search_results'] = list(found_users.values('id', 'username'))
            return redirect(next_url)

        elif 'add_friend' in request.POST:
            user_id = request.POST.get('user_id')
            to_user = get_object_or_404(User, id=user_id)
            Friendship.objects.get_or_create(from_user=current_user, to_user=to_user)
            return redirect(next_url)

        elif 'accept_request' in request.POST:
            request_id = request.POST.get('request_id')
            friend_request = get_object_or_404(Friendship, id=request_id, to_user=current_user)
            
            with transaction.atomic():
                friend_request.status = Friendship.Status.ACCEPTED
                friend_request.accepted_at = timezone.now()
                friend_request.save()
                Friendship.objects.update_or_create(
                    from_user=current_user, 
                    to_user=friend_request.from_user,
                    defaults={
                        'status': Friendship.Status.ACCEPTED,
                        'accepted_at': timezone.now()
                    }
                )
            return redirect(next_url)

        elif 'decline_request' in request.POST:
            request_id = request.POST.get('request_id')
            friend_request = get_object_or_404(Friendship, id=request_id, to_user=current_user)
            friend_request.delete()
            return redirect(next_url)
        
        elif 'cancel_request' in request.POST:
            request_id = request.POST.get('request_id')
            friend_request = get_object_or_404(Friendship, id=request_id, from_user=current_user)
            friend_request.delete()
            return redirect(next_url)

        elif 'remove_friend' in request.POST:
            friend_id_to_remove = request.POST.get('remove_friend_id')
            if friend_id_to_remove:
                friend_to_remove = get_object_or_404(User, id=friend_id_to_remove)
                
                Friendship.objects.filter(
                    (Q(from_user=current_user) & Q(to_user=friend_to_remove)) |
                    (Q(from_user=friend_to_remove) & Q(to_user=current_user))
                ).delete()

            return redirect(next_url)

    # --- GET request context building ---
    is_self = (current_user == profile_owner)
    context = {
        'profile_owner': profile_owner,
        'profile': profile_owner.profile,
        'is_self': is_self,
        'total_seen_movies': UserMovieView.objects.filter(user=profile_owner, has_seen=True).count(),
    }

    if not is_self:
        if Friendship.objects.filter(from_user=current_user, to_user=profile_owner, status='ACCEPTED').exists():
            context['friendship_status'] = 'FRIENDS'
        else:
            received_request = Friendship.objects.filter(from_user=profile_owner, to_user=current_user, status='PENDING').first()
            if received_request:
                context['friendship_status'] = 'REQUEST_RECEIVED'
                context['request_obj'] = received_request
            elif Friendship.objects.filter(from_user=current_user, to_user=profile_owner, status='PENDING').exists():
                context['friendship_status'] = 'REQUEST_SENT'
            else:
                context['friendship_status'] = 'NOT_FRIENDS'

    if is_self or context.get('friendship_status') in ['FRIENDS', 'REQUEST_RECEIVED']:
        context['total_rated_movies'] = UserMovieView.objects.filter(user=profile_owner).count()
        
    if is_self:
        invited_friend_ids = set(InviteCode.objects.filter(
            generated_by=current_user,
            used_by__isnull=False
        ).values_list('used_by_id', flat=True))

        context.update({
            'available_codes': InviteCode.objects.filter(generated_by=current_user, used_by__isnull=True),
            # **OPTIMIZATION**: Fetch related user data in a single query
            'friends_list': Friendship.objects.filter(from_user=current_user, status='ACCEPTED').select_related('to_user'),
            'incoming_requests': Friendship.objects.filter(to_user=current_user, status='PENDING').select_related('from_user'),
            'sent_requests': Friendship.objects.filter(from_user=current_user, status='PENDING').select_related('to_user'),
            'search_results': request.session.pop('search_results', None),
            'invited_friend_ids': invited_friend_ids,
        })

    return render(request, 'tracker/profile_dashboard.html', context)


def about_view(request):
    return render(request, 'tracker/about.html')