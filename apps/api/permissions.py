# apps/customer_api/permissions.py

from rest_framework.permissions import BasePermission


class IsApprovedCustomer(BasePermission):
    """
    Grants access only to authenticated, active, approved users with role='customer'.
    Mirrors the website's _customer_required() helper.
    """
    message = "You must be a verified customer to access this resource."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and
            user.is_authenticated and
            user.role == 'customer' and
            user.is_active and
            getattr(user, 'is_approved', False)
        )
