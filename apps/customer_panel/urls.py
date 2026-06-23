from django.urls import path
from . import views

app_name = 'customer_panel'

urlpatterns = [
    # Public home page (no login)
    path('', views.home, name='home'),

    # Authentication
    path('login/', views.customer_login, name='login'),       # login page
    path('logout/', views.customer_logout, name='logout'),
    path('register/', views.customer_register, name='register'),
    path('register/email/', views.customer_register_email, name='register_email'),

    # Protected views (require login)
    path('saved/', views.saved, name='saved'),
    path('save/<int:pk>/', views.toggle_save, name='toggle_save'),
    path('like/<int:pk>/', views.toggle_like, name='toggle_like'),
    path('property/<int:pk>/', views.property_view, name='property_view'),
    path('property/<int:pk>/comments/', views.property_comments, name='property_comments'),
    path('profile/', views.customer_profile, name='profile'),
    path('support/', views.support, name='support'),
    path('change-password/', views.change_password, name='change_password'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-confirm/', views.reset_confirm, name='reset_confirm'),
]