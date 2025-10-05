# tracker/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.next_movie_view, name='next_movie'),
    
    path('signup/<str:invite_code>/', views.SignUpView.as_view(), name='signup_with_code'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    
    path('profile/', views.profile_view, name='my_profile'),
    path('profile/<str:username>/', views.profile_view, name='profile_dashboard'),
    path('profile/delete/', views.delete_account_view, name='delete_account'),

    # --- NEW API URLS FOR EDITING ACCOUNT DETAILS ---
    path('api/account-details-form/', views.get_account_details_form, name='get_account_details_form'),
    path('api/update-account-details/', views.update_account_details, name='update_account_details'),
    # --- END NEW URLS ---

    path('api/last-rated-page/<int:page>/', views.get_last_rated_page, name='get_last_rated_page'),
    path('api/seen-movies-page/<str:username>/<int:page>/', views.get_seen_movies_page, name='get_seen_movies_page'),
    path('api/update-rating/', views.update_rating, name='update_rating'),
    
    path('movie/<int:movie_id>/', views.movie_detail_view, name='movie_detail'),
    # --- NEW URL FOR PERSON DETAILS ---
    path('person/<int:person_id>/<str:role>/', views.person_detail_view, name='person_detail'),

    path('about/', views.about_view, name='about'),
]