# apps/customer_api/views.py

from django.utils import timezone
from django.contrib.auth import update_session_auth_hash
from django.db.models import Avg

from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts.models import Property, Promotion
from apps.customer_panel.models import SavedProperty, PropertyLike, PropertyComment, PropertyRating
from .permissions import IsApprovedCustomer
from .serializers import (
    CustomerLoginSerializer,
    CustomerRegisterPhoneSerializer,
    CustomerRegisterEmailSerializer,
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
    TokenPairSerializer,
    ForgotPasswordSerializer,
    ResetConfirmSerializer,
    ChangePasswordSerializer,
    PropertyListSerializer,
    PropertyDetailSerializer,
    PropertyCommentSerializer,
    AddCommentSerializer,
    SavedPropertySerializer,
    PromotionSerializer,
)


# ─────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────

def get_relative_time(dt):
    """Reusable relative-time helper. Works with both naive and aware datetimes."""
    from datetime import datetime
    if dt is None:
        return ''
    # USE_TZ=False in this project — datetimes are naive
    now = datetime.now() if (dt.tzinfo is None) else timezone.now()
    diff    = now - dt
    seconds = int(diff.total_seconds())
    minutes = seconds // 60
    hours   = minutes // 60
    days    = diff.days
    weeks   = days // 7
    months  = days // 30
    years   = days // 365

    if seconds < 60:
        return "just now"
    elif minutes < 60:
        return f"{minutes} minute ago" if minutes == 1 else f"{minutes} minutes ago"
    elif hours < 24:
        return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"
    elif days < 7:
        return f"{days} day ago" if days == 1 else f"{days} days ago"
    elif weeks < 4:
        return f"{weeks} week ago" if weeks == 1 else f"{weeks} weeks ago"
    elif 0 < months < 12:
        return f"{months} month ago" if months == 1 else f"{months} months ago"
    else:
        if months == 0:
            return f"{weeks} weeks ago"
        if years == 0:
            return f"{months} months ago"
        return f"{years} year ago" if years == 1 else f"{years} years ago"


def _token_response(user):
    """Build a standardised token + user payload."""
    data = TokenPairSerializer.for_user(user)
    return TokenPairSerializer(data).data


# ─────────────────────────────────────────────
# Auth – Register
# ─────────────────────────────────────────────

class RegisterPhoneView(APIView):
    """POST /api/customer/auth/register/phone/"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomerRegisterPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"detail": "Registration successful.", "tokens": _token_response(user)},
            status=status.HTTP_201_CREATED,
        )


class RegisterEmailView(APIView):
    """POST /api/customer/auth/register/email/"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomerRegisterEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"detail": "Registration successful.", "tokens": _token_response(user)},
            status=status.HTTP_201_CREATED,
        )


# ─────────────────────────────────────────────
# Auth – Login / Logout
# ─────────────────────────────────────────────

class LoginView(APIView):
    """
    POST /api/customer/auth/login/
    Body: { login_type, phone|email, password }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomerLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        return Response(
            {"detail": "Login successful.", "tokens": _token_response(user)},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/customer/auth/logout/
    Body: { refresh }   — blacklists the refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({"detail": "Token is invalid or already expired."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# Auth – Password reset
# ─────────────────────────────────────────────

class ForgotPasswordView(APIView):
    """
    POST /api/customer/auth/forgot-password/
    Triggers OTP / reset link dispatch (wire up your OTP service here).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # ── TODO: dispatch OTP via SMS / email using your Redis OTP service ──
        # otp_service.send(user)

        contact = user.email if serializer.validated_data['login_type'] == 'email' else user.phone_number
        return Response(
            {"detail": f"Password reset instructions sent to {contact}."},
            status=status.HTTP_200_OK,
        )


class ResetConfirmView(APIView):
    """
    POST /api/customer/auth/reset-confirm/
    Body: { email, code, new_password, confirm_password }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # ── TODO: validate code against Redis OTP store, find user, set password ──
        # Example:
        # user = otp_service.verify_and_get_user(serializer.validated_data['email'],
        #                                        serializer.validated_data['code'])
        # user.set_password(serializer.validated_data['new_password'])
        # user.save()

        return Response(
            {"detail": "Password has been reset successfully. Please log in."},
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────
# Auth – Change password (authenticated)
# ─────────────────────────────────────────────

class ChangePasswordView(APIView):
    """PUT /api/customer/auth/change-password/"""
    permission_classes = [IsApprovedCustomer]

    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        # Return fresh tokens so the mobile client does not need to re-login
        return Response(
            {"detail": "Password updated successfully.", "tokens": _token_response(request.user)},
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────
# Home feed
# ─────────────────────────────────────────────

class HomeView(APIView):
    """
    GET /api/customer/home/
    Public. Returns active promotions + published property listings.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        properties = (
            Property.objects
            .filter(status='Published', is_active=True)
            .annotate(avg_rating=Avg('ratings__rating'))
            .order_by('-created_at')
            .select_related('user', 'user__profile')
            .prefetch_related('additional_images', 'likes', 'comments')
        )

        promotions = Promotion.objects.filter(is_active=True).order_by('-created_at')

        return Response({
            "promotions":  PromotionSerializer(promotions, many=True, context={'request': request}).data,
            "properties":  PropertyListSerializer(properties, many=True, context={'request': request}).data,
        })


# ─────────────────────────────────────────────
# Property detail
# ─────────────────────────────────────────────

class PropertyDetailView(APIView):
    """GET /api/customer/properties/<pk>/"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            prop = (
                Property.objects
                .filter(status='Published', pk=pk)
                .annotate(avg_rating=Avg('ratings__rating'))
                .select_related('user', 'user__profile')
                .prefetch_related('additional_images', 'likes', 'comments')
                .get()
            )
        except Property.DoesNotExist:
            return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(PropertyDetailSerializer(prop, context={'request': request}).data)


# ─────────────────────────────────────────────
# Save / Unsave toggle
# ─────────────────────────────────────────────

class ToggleSaveView(APIView):
    """
    POST /api/customer/properties/<pk>/save/
    Returns: { saved: true|false }
    """
    permission_classes = [IsApprovedCustomer]

    def post(self, request, pk):
        from django.shortcuts import get_object_or_404
        prop = get_object_or_404(Property, pk=pk)
        obj, created = SavedProperty.objects.get_or_create(user=request.user, property=prop)
        if not created:
            obj.delete()
            return Response({"saved": False, "detail": "Property removed from saved."})
        return Response({"saved": True, "detail": "Property saved."}, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────
# Like / Unlike toggle
# ─────────────────────────────────────────────

class ToggleLikeView(APIView):
    """
    POST /api/customer/properties/<pk>/like/
    Returns: { liked: true|false, likes_count: int }
    """
    permission_classes = [IsApprovedCustomer]

    def post(self, request, pk):
        from django.shortcuts import get_object_or_404
        prop = get_object_or_404(Property, pk=pk)
        obj, created = PropertyLike.objects.get_or_create(user=request.user, property=prop)
        if not created:
            obj.delete()
            return Response({"liked": False, "likes_count": prop.likes.count()})
        return Response({"liked": True, "likes_count": prop.likes.count()}, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────
# Saved list
# ─────────────────────────────────────────────

class SavedListView(generics.ListAPIView):
    """GET /api/customer/saved/"""
    permission_classes = [IsApprovedCustomer]
    serializer_class   = SavedPropertySerializer

    def get_queryset(self):
        return (
            SavedProperty.objects
            .filter(user=self.request.user)
            .select_related('property', 'property__user', 'property__user__profile')
            .prefetch_related('property__additional_images', 'property__likes', 'property__comments')
            .order_by('-saved_at')
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx


# ─────────────────────────────────────────────
# Comments & Ratings
# ─────────────────────────────────────────────

class PropertyCommentsView(APIView):
    """
    GET  /api/customer/properties/<pk>/comments/  — list comments + rating summary
    POST /api/customer/properties/<pk>/comments/  — add comment and/or rating
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsApprovedCustomer()]

    def _get_property(self, pk):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(Property, pk=pk, status='Published')

    def _rating_summary(self, prop, user=None):
        all_ratings = PropertyRating.objects.filter(property=prop)
        avg = 0.0
        if all_ratings.exists():
            avg = round(sum(r.rating for r in all_ratings) / all_ratings.count(), 1)
        user_rating = 0
        if user and user.is_authenticated:
            try:
                user_rating = PropertyRating.objects.get(user=user, property=prop).rating
            except PropertyRating.DoesNotExist:
                pass
        return {"avg_rating": avg, "user_rating": user_rating, "ratings_count": all_ratings.count()}

    def get(self, request, pk):
        prop     = self._get_property(pk)
        comments = (
            PropertyComment.objects
            .filter(property=prop)
            .select_related('user', 'user__profile')
            .order_by('-created_at')
        )
        return Response({
            "property_id":    prop.pk,
            "comments_count": comments.count(),
            "rating_summary": self._rating_summary(prop, request.user),
            "comments":       PropertyCommentSerializer(comments, many=True, context={'request': request}).data,
        })

    def post(self, request, pk):
        prop       = self._get_property(pk)
        serializer = AddCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = None
        text = serializer.validated_data.get('text', '').strip()
        if text:
            comment = PropertyComment.objects.create(
                user=request.user,
                property=prop,
                text=text,
            )

        rating_val = serializer.validated_data.get('rating')
        if rating_val:
            PropertyRating.objects.update_or_create(
                user=request.user,
                property=prop,
                defaults={'rating': rating_val},
            )

        return Response({
            "detail":         "Submitted successfully.",
            "comment":        PropertyCommentSerializer(comment, context={'request': request}).data if comment else None,
            "rating_summary": self._rating_summary(prop, request.user),
        }, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────

class CustomerProfileView(APIView):
    """
    GET  /api/customer/profile/
    PUT  /api/customer/profile/   (multipart/form-data for avatar upload)
    """
    permission_classes = [IsApprovedCustomer]

    def get(self, request):
        serializer = CustomerProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        serializer = CustomerProfileUpdateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.update(request.user, serializer.validated_data)
        return Response(
            {"detail": "Profile updated successfully.", "profile": CustomerProfileSerializer(user, context={'request': request}).data},
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────
# Support
# ─────────────────────────────────────────────

class SupportView(APIView):
    """POST /api/customer/support/"""
    permission_classes = [IsApprovedCustomer]

    def post(self, request):
        subject = request.data.get('subject', '').strip()
        message = request.data.get('message', '').strip()

        if not message:
            return Response({"detail": "Message is required."}, status=status.HTTP_400_BAD_REQUEST)

        # TODO: save to a SupportTicket model or send email
        return Response(
            {"detail": "Your message has been sent. We will get back to you soon."},
            status=status.HTTP_200_OK,
        )
