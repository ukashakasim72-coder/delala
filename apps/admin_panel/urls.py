from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.admin_login, name='home'),
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('forgot-password/', views.admin_forgot_password, name='forgot_password'),

    # Agents
    path('agents/', views.agent_list, name='agent_list'),
    path('agents/create/', views.agent_create, name='agent_create'),
    path('agents/edit/<int:pk>/', views.agent_edit, name='agent_edit'),
    path('agents/view/<int:pk>/', views.agent_view, name='agent_view'),
    path('agents/delete/<int:pk>/', views.delete_agent, name='delete_agent'),
    path('agents/block/<int:pk>/', views.block_agent, name='block_agent'),
    path('agents/login-as/<int:pk>/', views.login_as_agent, name='login_as_agent'),
    path('agents/properties/<int:pk>/', views.agent_properties, name='agent_properties'),

    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/edit/<int:pk>/', views.customer_edit, name='customer_edit'),
    path('customers/delete/<int:pk>/', views.delete_customer, name='delete_customer'),
    path('customers/block/<int:pk>/', views.block_customer, name='block_customer'),
    path('customers/approve/<int:pk>/', views.approve_customer, name='approve_customer'),

    # Reports
    path('monthly-reports/', views.monthly_reports, name='monthly_reports'),

    # Property edit (admin)
    path('edit-property/<int:pk>/', views.admin_edit_property, name='admin_edit_property'),

    # Listings
    path('manage-listings/', views.manage_listings, name='manage_listings'),
    path('manage-listings/delete/<int:pk>/', views.delete_listing, name='delete_listing'),
    path('approve-listings/', views.approve_listings, name='approve_listings'),
    path('approve-listing/<int:pk>/', views.approve_listing_action, name='approve_listing'),
    path('reject-listing/<int:pk>/', views.reject_listing_action, name='reject_listing'),
    path('toggle-status/<int:pk>/', views.toggle_listing_status, name='toggle_listing_status'),
    path('properties/detail/<int:pk>/', views.property_detail, name='property_detail'),

    # Promotions
    path('promotions/add/', views.add_promotion, name='add_promotion'),
    path('promotions/', views.promotion_list, name='promotion_list'),
    path('promotions/delete/<int:pk>/', views.delete_promotion, name='delete_promotion'),
    path('promotions/toggle/<int:pk>/', views.toggle_promotion, name='toggle_promotion'),
]

