from django.db import models

# =============================================================================
# admin_panel has NO database models of its own.
#
# All models used by admin_panel views and templates live in accounts/models.py
# and are imported directly:
#
# from apps.accounts.models import User, Property, Profile, VerificationCode
#
# Here is what each model is used for in admin_panel:
#
# User (accounts.User)
#   - admin_login        → authenticate by email+password, check role=='admin'
#   - agent_list         → filter role='agent', read is_active for block status
#   - agent_create       → create_user() with role='agent'
#   - agent_edit         → update email, phone_number, password
#   - agent_view         → read-only view of agent data
#   - delete_agent       → agent.delete() — permanent, cascades all related data
#   - block_agent        → toggle agent.is_active (False = cannot login)
#   - customer_list      → filter role='customer'
#   - dashboard          → count by role and status
#
# Profile (accounts.Profile)
#   - agent_create       → save location, whatsapp, national_id_front/back,
#                          license_front/back after creating agent User
#   - agent_edit         → update location, whatsapp
#   - agent_view         → display avatar, location, whatsapp,
#                          national_id_front/back, license_front/back
#   - property_detail    → display agent avatar (profile_avatar_url)
#
# Property (accounts.Property)
#   - dashboard          → count total, published, pending, today's listings
#   - manage_listings    → filter status in ['Published','Active'], toggle status
#   - approve_listings   → filter status='Pending', show for review
#   - approve_listing_action → set status='Published'
#   - reject_listing_action  → set status='Rejected' (data stays in DB)
#   - delete_listing     → property.delete() — permanent
#   - toggle_listing_status  → toggle Published ↔ Pending
#   - property_detail    → full property detail view for admin
#
# PropertyImage (accounts.PropertyImage)
#   - property_detail    → display additional_images (front/back/right/left)
#                          via related_name='additional_images'
#
# VerificationCode (accounts.VerificationCode)
#   - admin_forgot_password → verify code, reset admin password
#
# =============================================================================


