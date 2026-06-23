from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.contrib.auth.models import BaseUserManager
from django.utils import timezone
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
import random


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    role = models.CharField(
        max_length=20,
        choices=(
            ('admin', 'Admin'),
            ('agent', 'Agent'),
            ('customer', 'Customer')
        ),
        default='customer'
    )
    is_approved = models.BooleanField(default=True)  # True = can access, False = pending

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email




class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    # Document fields
    national_id_front = models.ImageField(upload_to='agent_docs/', null=True, blank=True)
    national_id_back = models.ImageField(upload_to='agent_docs/', null=True, blank=True)
    license_front = models.ImageField(upload_to='agent_docs/', null=True, blank=True)
    license_back = models.ImageField(upload_to='agent_docs/', null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.email}"

class Property(models.Model):
    TYPE_CHOICES = (
        ('rent', 'For rent'),
        ('sale', 'For sale')
    )
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Published', 'Published'),
        ('Rejected', 'Rejected'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='properties'
    )
    property_name = models.CharField(max_length=200)
    price = models.CharField(max_length=100)
    property_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    location = models.CharField(max_length=200)
    bedrooms = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    bathrooms = models.CharField(max_length=50)
    square_meters = models.CharField(max_length=50)
    image = models.ImageField(upload_to='properties/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    views = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.property_name

# ✅ NEW: Stores up to 4 additional images per property
class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='additional_images'
    )
    image = models.ImageField(upload_to='properties/additional/')
    caption = models.CharField(max_length=100, blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.property.property_name}"

class VerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=5)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        if not self.code:
            self.code = str(random.randint(10000, 99999))
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        return f"{self.user.email} - {self.code}"


# Signal to create Profile automatically when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()

class Promotion(models.Model):
    PROMOTION_TYPES = (
        ('banner', 'Banner'),
        ('featured', 'Featured Listing'),
        ('discount', 'Discount'),
        ('announcement', 'Announcement'),
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPES, default='featured')
    property = models.ForeignKey(
        'Property', on_delete=models.SET_NULL,
        related_name='promotions', null=True, blank=True
    )
    # Display fields shown on card
    agent_phone = models.CharField(max_length=20, blank=True)
    discount_text = models.CharField(max_length=50, blank=True)
    property_name = models.CharField(max_length=200, blank=True)
    price = models.CharField(max_length=100, blank=True)
    property_type = models.CharField(max_length=10, blank=True)
    location = models.CharField(max_length=200, blank=True)
    bedrooms = models.CharField(max_length=50, blank=True)
    bathrooms = models.CharField(max_length=50, blank=True)
    square_meters = models.CharField(max_length=50, blank=True)
    # 4 images with captions
    image = models.ImageField(upload_to='promotions/', null=True, blank=True)
    image_2 = models.ImageField(upload_to='promotions/', null=True, blank=True)
    image_3 = models.ImageField(upload_to='promotions/', null=True, blank=True)
    image_4 = models.ImageField(upload_to='promotions/', null=True, blank=True)
    caption_1 = models.CharField(max_length=100, blank=True)
    caption_2 = models.CharField(max_length=100, blank=True)
    caption_3 = models.CharField(max_length=100, blank=True)
    caption_4 = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='promotions'
    )

    def __str__(self):
        return f"#{self.id} {self.title}"

