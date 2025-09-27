# tracker/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Main movie loop view (GET/POST handler)
    path('', views.next_movie_view, name='next_movie'),

    # User Signup View
    path('signup/', views.SignUpView.as_view(), name='signup'),

    # User Profile View
    path('profile/', views.profile_view, name='profile_dashboard'),

    # About/Credits Page
    path('about/', views.about_view, name='about'),
]
