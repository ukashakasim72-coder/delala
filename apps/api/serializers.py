# apps/customer_api/serializers.py

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Property, Profile, User, Promotion
from apps.customer_panel.models import SavedProperty, PropertyLike, PropertyComment, PropertyRating


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────

class CustomerRegisterPhoneSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone     = serializers.CharField(max_length=20)
    password  = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_phone(self, value):
        value = value.strip()
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        phone = validated_data['phone']
        internal_email = f"{phone}@digitaldelala.com"

        if User.objects.filter(email=internal_email).exists():
            raise serializers.ValidationError({"phone": "This phone number is already registered."})

        full_name = validated_data['full_name'].strip()
        parts = full_name.split()

        user = User.objects.create_user(
            email=internal_email,
            password=validated_data['password'],
            phone_number=phone,
            role='customer',
            first_name=parts[0],
            last_name=' '.join(parts[1:]) if len(parts) > 1 else '',
            is_approved=True,
        )
        return user


class CustomerRegisterEmailSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email     = serializers.EmailField()
    password  = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        full_name = validated_data['full_name'].strip()
        parts = full_name.split()

        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role='customer',
            first_name=parts[0],
            last_name=' '.join(parts[1:]) if len(parts) > 1 else '',
            is_approved=True,
        )
        return user


class CustomerLoginSerializer(serializers.Serializer):
    login_type = serializers.ChoiceField(choices=['phone', 'email'], default='phone')
    phone      = serializers.CharField(required=False, allow_blank=True)
    email      = serializers.EmailField(required=False, allow_blank=True)
    password   = serializers.CharField(write_only=True)

    def validate(self, data):
        login_type = data.get('login_type', 'phone')
        password   = data.get('password', '')

        if login_type == 'email':
            email = data.get('email', '').strip().lower()
            if not email:
                raise serializers.ValidationError({"email": "Email is required."})
            try:
                user = User.objects.get(email=email, role='customer')
            except User.DoesNotExist:
                raise serializers.ValidationError({"non_field_errors": "Invalid email or password."})
        else:
            phone = data.get('phone', '').strip()
            if not phone:
                raise serializers.ValidationError({"phone": "Phone number is required."})
            try:
                user = User.objects.get(phone_number=phone, role='customer')
            except User.DoesNotExist:
                raise serializers.ValidationError({"non_field_errors": "Invalid phone number or password."})

        auth_user = authenticate(username=user.email, password=password)
        if auth_user is None:
            raise serializers.ValidationError({"non_field_errors": "Invalid credentials."})
        if not auth_user.is_active:
            raise serializers.ValidationError({"non_field_errors": "Your account has been blocked. Contact support."})
        if not auth_user.is_approved:
            raise serializers.ValidationError({"non_field_errors": "Your account is pending admin approval."})

        data['user'] = auth_user
        return data


class TokenPairSerializer(serializers.Serializer):
    access  = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user    = serializers.SerializerMethodField(read_only=True)

    def get_user(self, obj):
        u = obj['user']
        return {
            'id':        u.id,
            'full_name': u.get_full_name(),
            'email':     u.email,
            'phone':     u.phone_number,
            'role':      u.role,
        }

    @classmethod
    def for_user(cls, user):
        refresh = RefreshToken.for_user(user)
        return {
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user':    user,
        }


class ForgotPasswordSerializer(serializers.Serializer):
    login_type = serializers.ChoiceField(choices=['phone', 'email'], default='phone')
    phone      = serializers.CharField(required=False, allow_blank=True)
    email      = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, data):
        if data['login_type'] == 'email':
            email = data.get('email', '').strip().lower()
            if not email:
                raise serializers.ValidationError({"email": "Email is required."})
            try:
                data['user'] = User.objects.get(email=email, role='customer')
            except User.DoesNotExist:
                raise serializers.ValidationError({"non_field_errors": "No customer account found with this email."})
        else:
            phone = data.get('phone', '').strip()
            if not phone:
                raise serializers.ValidationError({"phone": "Phone number is required."})
            try:
                data['user'] = User.objects.get(phone_number=phone, role='customer')
            except User.DoesNotExist:
                raise serializers.ValidationError({"non_field_errors": "No customer account found with this phone number."})
        return data


class ResetConfirmSerializer(serializers.Serializer):
    email            = serializers.EmailField(required=False, allow_blank=True)
    code             = serializers.CharField()
    new_password     = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password     = serializers.CharField(write_only=True)
    new_password     = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        try:
            validate_password(data['new_password'], self.context['request'].user)
        except Exception as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return data


# ─────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────

class ProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False)

    class Meta:
        model  = Profile
        fields = ['location', 'whatsapp', 'avatar']


class CustomerProfileSerializer(serializers.ModelSerializer):
    profile   = ProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'full_name', 'email', 'phone_number', 'profile']

    def get_full_name(self, obj):
        return obj.get_full_name()


class CustomerProfileUpdateSerializer(serializers.Serializer):
    full_name    = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    location     = serializers.CharField(required=False, allow_blank=True)
    whatsapp     = serializers.CharField(required=False, allow_blank=True)
    avatar       = serializers.ImageField(required=False)

    def update(self, user, validated_data):
        full_name = validated_data.get('full_name', '').strip()
        if full_name:
            parts = full_name.split()
            user.first_name = parts[0]
            user.last_name  = ' '.join(parts[1:]) if len(parts) > 1 else ''

        if 'phone_number' in validated_data:
            user.phone_number = validated_data['phone_number']

        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        if 'location' in validated_data:
            profile.location = validated_data['location']
        if 'whatsapp' in validated_data:
            profile.whatsapp = validated_data['whatsapp']
        if 'avatar' in validated_data:
            profile.avatar = validated_data['avatar']
        profile.save()

        return user


# ─────────────────────────────────────────────
# Promotions
# ─────────────────────────────────────────────

class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Promotion
        fields = [
            'id', 'title', 'description', 'promotion_type',
            'property_name', 'price', 'property_type', 'location',
            'bedrooms', 'bathrooms', 'square_meters',
            'agent_phone', 'discount_text',
            'image', 'image_2', 'image_3', 'image_4',
            'caption_1', 'caption_2', 'caption_3', 'caption_4',
            'is_active', 'created_at',
        ]


# ─────────────────────────────────────────────
# Properties
# ─────────────────────────────────────────────

class AgentMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    phone     = serializers.SerializerMethodField()
    whatsapp  = serializers.SerializerMethodField()
    avatar    = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'full_name', 'phone', 'whatsapp', 'avatar']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_phone(self, obj):
        if obj.phone_number and obj.phone_number.strip():
            return obj.phone_number.strip()
        try:
            if obj.profile.whatsapp and obj.profile.whatsapp.strip():
                return obj.profile.whatsapp.strip()
        except Exception:
            pass
        return ''

    def get_whatsapp(self, obj):
        try:
            return obj.profile.whatsapp.strip() if obj.profile.whatsapp else ''
        except Exception:
            return ''

    def get_avatar(self, obj):
        try:
            if obj.profile.avatar:
                request = self.context.get('request')
                url = obj.profile.avatar.url
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return None


class PropertyImageSerializer(serializers.Serializer):
    """Serializes a single PropertyImage (additional_images FK set)."""
    url     = serializers.SerializerMethodField()
    caption = serializers.CharField()

    def get_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class PropertyListSerializer(serializers.ModelSerializer):
    front_image    = serializers.SerializerMethodField()
    all_images     = serializers.SerializerMethodField()   # ← NEW: full image list with captions
    time_ago       = serializers.SerializerMethodField()
    likes_count    = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    avg_rating     = serializers.FloatField(read_only=True)
    agent          = AgentMiniSerializer(source='user', read_only=True)
    is_saved       = serializers.SerializerMethodField()
    is_liked       = serializers.SerializerMethodField()

    class Meta:
        model  = Property
        fields = [
            'id', 'property_name', 'description', 'price', 'location',
            'property_type', 'bedrooms', 'bathrooms', 'square_meters',
            'front_image', 'all_images',
            'time_ago', 'likes_count', 'comments_count',
            'avg_rating', 'agent', 'is_saved', 'is_liked', 'status', 'created_at',
        ]

    def _user(self):
        request = self.context.get('request')
        return request.user if request and request.user.is_authenticated else None

    def get_front_image(self, obj):
        """First additional image, falling back to the main image field."""
        request = self.context.get('request')
        first = obj.additional_images.first()
        url = first.image.url if first else (obj.image.url if obj.image else None)
        return request.build_absolute_uri(url) if url and request else url

    def get_all_images(self, obj):
        """
        Returns all additional images with captions.
        Falls back to including the main image as the first entry if no
        additional images exist, so the client always has something to show.

        Shape: [ { "url": "...", "caption": "..." }, ... ]
        """
        request = self.context.get('request')
        images = []

        for img in obj.additional_images.all():
            url = request.build_absolute_uri(img.image.url) if request else img.image.url
            images.append({'url': url, 'caption': img.caption or ''})

        # Fallback: include main image if no additional images uploaded
        if not images and obj.image:
            url = request.build_absolute_uri(obj.image.url) if request else obj.image.url
            images.append({'url': url, 'caption': ''})

        return images

    def get_time_ago(self, obj):
        from .views import get_relative_time
        return get_relative_time(obj.created_at)

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_is_saved(self, obj):
        user = self._user()
        if not user or getattr(user, 'role', None) != 'customer':
            return False
        return SavedProperty.objects.filter(user=user, property=obj).exists()

    def get_is_liked(self, obj):
        user = self._user()
        if not user or getattr(user, 'role', None) != 'customer':
            return False
        return PropertyLike.objects.filter(user=user, property=obj).exists()


class PropertyDetailSerializer(PropertyListSerializer):
    agent_location = serializers.SerializerMethodField()

    class Meta(PropertyListSerializer.Meta):
        # all_images is already in PropertyListSerializer.Meta.fields
        # agent_location added here for detail view only
        fields = PropertyListSerializer.Meta.fields + ['agent_location']

    def get_agent_location(self, obj):
        try:
            return obj.user.profile.location or ''
        except Exception:
            return ''


# ─────────────────────────────────────────────
# Comments & Ratings
# ─────────────────────────────────────────────

class CommentUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    avatar    = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'full_name', 'avatar']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_avatar(self, obj):
        try:
            if obj.profile.avatar:
                request = self.context.get('request')
                url = obj.profile.avatar.url
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return None


class PropertyCommentSerializer(serializers.ModelSerializer):
    user     = CommentUserSerializer(read_only=True)
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model  = PropertyComment
        fields = ['id', 'user', 'text', 'created_at', 'time_ago']

    def get_time_ago(self, obj):
        from .views import get_relative_time
        return get_relative_time(obj.created_at)


class AddCommentSerializer(serializers.Serializer):
    text   = serializers.CharField(min_length=1)
    rating = serializers.IntegerField(required=False, min_value=1, max_value=5)


class SavedPropertySerializer(serializers.ModelSerializer):
    property = PropertyListSerializer(read_only=True)

    class Meta:
        model  = SavedProperty
        fields = ['id', 'property', 'saved_at']
