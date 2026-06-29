# apps/customer_api/urls.py

from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'api'


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request, format=None):
    return Response({
        'auth': {
            'register_phone':  request.build_absolute_uri('/api/auth/register/phone/'),
            'register_email':  request.build_absolute_uri('/api/auth/register/email/'),
            'login':           request.build_absolute_uri('/api/auth/login/'),
            'logout':          request.build_absolute_uri('/api/auth/logout/'),
            'token_refresh':   request.build_absolute_uri('/api/auth/token/refresh/'),
            'forgot_password': request.build_absolute_uri('/api/auth/forgot-password/'),
            'reset_confirm':   request.build_absolute_uri('/api/auth/reset-confirm/'),
            'change_password': request.build_absolute_uri('/api/auth/change-password/'),
        },
        'feed': {
            'home': request.build_absolute_uri('/api/home/'),
        },
        #'properties': {
            #'detail':   '/api/properties/{pk}/',
            #'save':     '/api/properties/{pk}/save/',
            #'like':     '/api/properties/{pk}/like/',
            #'comments': '/api/properties/{pk}/comments/',
        #},
        'customer': {
            'saved':   request.build_absolute_uri('/api/saved/'),
            'profile': request.build_absolute_uri('/api/profile/'),
            'support': request.build_absolute_uri('/api/support/'),
        },
    })


urlpatterns = [

    # API Root
    path('', api_root, name='api_root'),

    # Auth
    path('auth/register/phone/',  views.RegisterPhoneView.as_view(),  name='register_phone'),
    path('auth/register/email/',  views.RegisterEmailView.as_view(),  name='register_email'),
    path('auth/login/',           views.LoginView.as_view(),          name='login'),
    path('auth/logout/',          views.LogoutView.as_view(),         name='logout'),
    path('auth/token/refresh/',   TokenRefreshView.as_view(),         name='token_refresh'),
    path('auth/forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('auth/reset-confirm/',   views.ResetConfirmView.as_view(),   name='reset_confirm'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change_password'),

    # Home feed
    path('home/', views.HomeView.as_view(), name='home'),

    # Properties
    path('properties/<int:pk>/',          views.PropertyDetailView.as_view(),   name='property_detail'),
    path('properties/<int:pk>/save/',     views.ToggleSaveView.as_view(),       name='toggle_save'),
    path('properties/<int:pk>/like/',     views.ToggleLikeView.as_view(),       name='toggle_like'),
    path('properties/<int:pk>/comments/', views.PropertyCommentsView.as_view(), name='property_comments'),

    # Saved list
    path('saved/', views.SavedListView.as_view(), name='saved'),

    # Profile
    path('profile/', views.CustomerProfileView.as_view(), name='profile'),

    # Support
    path('support/', views.SupportView.as_view(), name='support'),
]
