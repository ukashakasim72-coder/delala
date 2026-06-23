from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- UI URLs ---
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('add-property/', views.add_property_view, name='add_property'),
    path('listing/', views.listing_view, name='listing'),
    path('profile/', views.profile_view, name='profile'),                     # <-- ADD THIS
    path('profile/gallery/', views.profile_gallery, name='profile_gallery'),

    path('property/<int:pk>/', views.property_detail_view, name='property_detail'),
    path('property/edit/<int:pk>/', views.edit_property_view, name='edit_property'),

    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset_change_password/', views.reset_change_password_view, name='reset_change_password'),
    path('reset-confirm/', views.reset_password_confirm_view, name='reset_password_confirm'),
    path('reset-done/', views.password_reset_done, name='password_reset_done'),
    path('reset-complete/', views.password_reset_complete, name='password_reset_complete'),

    # --- REST API URLs ---
    path('api/login/', views.LoginAPI.as_view(), name='api_login'),
    path('api/request-reset/', views.RequestResetAPI.as_view(), name='api_request_reset'),
    path('api/reset-password/', views.ResetPasswordAPI.as_view(), name='api_reset_password'),

    path('property/toggle/<int:pk>/', views.toggle_active_property, name='toggle_active_property'),
    path('edit-property/<int:pk>/', views.edit_property_view, name='edit_property'),

    # ____support_____
    path('support/', views.support, name='support'),

]