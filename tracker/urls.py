# tracker/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.next_movie_view, name='next_movie'),
    
    # NEW: URL for invite links, captures the code
    path('signup/<str:invite_code>/', views.SignUpView.as_view(), name='signup_with_code'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    
    # --- UPDATED PROFILE URLS ---
    # A link to /profile/ will now show the logged-in user's profile
    path('profile/', views.profile_view, name='my_profile'),
    # This URL is for viewing a specific user's public profile
    path('profile/<str:username>/', views.profile_view, name='profile_dashboard'),

    path('api/last-rated-page/<int:page>/', views.get_last_rated_page, name='get_last_rated_page'),
    path('api/seen-movies-page/<str:username>/<int:page>/', views.get_seen_movies_page, name='get_seen_movies_page'),
    path('api/update-rating/', views.update_rating, name='update_rating'),
    path('movie/<int:movie_id>/', views.movie_detail_view, name='movie_detail'), # Placeholder


    path('about/', views.about_view, name='about'),
]