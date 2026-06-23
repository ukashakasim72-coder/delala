from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Sum

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .forms import UserLoginForm, ForgotPasswordForm, ResetPasswordConfirmForm, UserProfileForm
from .models import VerificationCode, User as CustomUser, Profile, Property, PropertyImage
from .serializers import UserSerializer

from django.contrib.auth import login as auth_login


def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.user_cache
            login(request, user)
            messages.success(request, f"Welcome back, {user.email}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid login credentials.")
    else:
        form = UserLoginForm(request)
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def dashboard_view(request):
    user_properties = Property.objects.filter(user=request.user)

    active_rent = user_properties.filter(
        property_type='rent', status='Published', is_active=True
    ).count()
    successful_rent = user_properties.filter(
        property_type='rent', status='Published', is_active=False
    ).count()
    active_sale = user_properties.filter(
        property_type='sale', status='Published', is_active=True
    ).count()
    successful_sale = user_properties.filter(
        property_type='sale', status='Published', is_active=False
    ).count()
    total_views = user_properties.filter(status='Published').count()
    pending = user_properties.filter(status='Pending').count()

    context = {
        'active_rent': active_rent,
        'successful_rent': successful_rent,
        'active_sale': active_sale,
        'successful_sale': successful_sale,
        'total_views': total_views,
        'pending': pending,
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def add_property_view(request):
    if request.method == 'POST':
        property_name = request.POST.get('property_name')
        price = request.POST.get('price')
        property_type = request.POST.get('type')
        location = request.POST.get('location')
        bedrooms = request.POST.get('bedrooms')
        description = request.POST.get('description')
        bathrooms = request.POST.get('bathrooms')
        square_meters = request.POST.get('square_meters')

        # ---- Numeric validation (only digits allowed) ----
        def is_numeric(value):
            return value.isdigit()

        numeric_fields = {
            'price': price,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'square_meters': square_meters,
        }
        for field_name, field_value in numeric_fields.items():
            if field_value and not is_numeric(field_value):
                messages.error(request, f"{field_name.replace('_', ' ').title()} must contain only numbers.")
                # Re‑render the form with the submitted data
                return render(request, 'accounts/add_property.html', {
                    'property_name': property_name,
                    'price': price,
                    'type': property_type,
                    'location': location,
                    'bedrooms': bedrooms,
                    'description': description,
                    'bathrooms': bathrooms,
                    'square_meters': square_meters,
                })

        # Required fields validation
        if not property_name or not price or not property_type or not location or not bedrooms or not bathrooms or not square_meters:
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'accounts/add_property.html')

        main_image = (
            request.FILES.get('add_img_1') or
            request.FILES.get('add_img_2') or
            request.FILES.get('add_img_3') or
            request.FILES.get('add_img_4')
        )

        property_obj = Property.objects.create(
            user=request.user,
            property_name=property_name,
            price=price,
            property_type=property_type,
            location=location,
            bedrooms=bedrooms,
            description=description,
            bathrooms=bathrooms,
            square_meters=square_meters,
            image=main_image,
            status='Pending'
        )

        from .models import PropertyImage
        image_keys = [
            ('add_img_1', 'front_image_name'),
            ('add_img_2', 'back_image_name'),
            ('add_img_3', 'right_image_name'),
            ('add_img_4', 'left_image_name'),
        ]
        for img_key, name_key in image_keys:
            file = request.FILES.get(img_key)
            if file:
                caption = request.POST.get(name_key, '').strip()
                PropertyImage.objects.create(
                    property=property_obj,
                    image=file,
                    caption=caption
                )

        messages.success(request, f"Property '{property_name}' added successfully!")
        return redirect('listing')

    return render(request, 'accounts/add_property.html')

@login_required
def listing_view(request):
    properties = Property.objects.filter(user=request.user).order_by('-created_at')
    listings = []
    for prop in properties:
        listings.append({
            'id': prop.id,
            'property': prop.property_name,
            'type': prop.get_property_type_display(),
            'price': prop.price,
            'created_at': prop.created_at.strftime('%d %B, %Y'),
            'status': prop.status,
            'image': prop.image,
            'is_active': prop.is_active,
        })
    return render(request, 'accounts/listing.html', {'listings': listings})


@login_required
def property_detail_view(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    property_obj.views += 1
    property_obj.save(update_fields=['views'])

    created_date = property_obj.created_at.strftime('%B %d, %Y')
    created_time = property_obj.created_at.strftime('%I:%M %p')
    display_code = f"Codo-{property_obj.id + 1000}"

    agent = property_obj.user
    agent_full_name = agent.get_full_name() or agent.email
    agent_email = agent.email
    agent_phone = getattr(agent, 'phone_number', 'Not provided')

    if hasattr(agent, 'profile'):
        profile = agent.profile
        agent_location = profile.location or 'Not provided'
        profile_avatar_url = profile.avatar.url if profile.avatar else None
    else:
        agent_location = 'Not provided'
        profile_avatar_url = None

    additional_images = list(property_obj.additional_images.all())

    context = {
        'property': property_obj,
        'created_date': created_date,
        'created_time': created_time,
        'display_code': display_code,
        'agent_full_name': agent_full_name,
        'agent_email': agent_email,
        'agent_phone': agent_phone,
        'agent_location': agent_location,
        'profile_avatar_url': profile_avatar_url,
        'additional_images': additional_images,
    }
    return render(request, 'accounts/property_detail.html', context)


@login_required
def edit_property_view(request, pk):
    property_obj = get_object_or_404(Property, id=pk, user=request.user)

    if request.method == 'POST':
        property_name = request.POST.get('property_name')
        price = request.POST.get('price')
        property_type = request.POST.get('type')
        location = request.POST.get('location')
        bedrooms = request.POST.get('bedrooms')
        description = request.POST.get('description')
        bathrooms = request.POST.get('bathrooms')
        square_meters = request.POST.get('square_meters')

        # ---- Numeric validation (only digits allowed) ----
        def is_numeric(value):
            return value.isdigit()

        numeric_fields = {
            'price': price,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'square_meters': square_meters,
        }
        for field_name, field_value in numeric_fields.items():
            if field_value and not is_numeric(field_value):
                messages.error(request, f"{field_name.replace('_', ' ').title()} must contain only numbers.")
                # Re‑render the edit form with the submitted data
                return render(request, 'accounts/add_property.html', {
                    'property': property_obj,
                    'property_name': property_name,
                    'price': price,
                    'type': property_type,
                    'location': location,
                    'bedrooms': bedrooms,
                    'description': description,
                    'bathrooms': bathrooms,
                    'square_meters': square_meters,
                })

        # Update property fields
        property_obj.property_name = property_name
        property_obj.price = price
        property_obj.property_type = property_type
        property_obj.location = location
        property_obj.bedrooms = bedrooms
        property_obj.description = description
        property_obj.bathrooms = bathrooms
        property_obj.square_meters = square_meters

        if property_obj.status == 'Rejected':
            property_obj.status = 'Pending'

        if request.FILES.get('add_img_1'):
            property_obj.image = request.FILES.get('add_img_1')

        property_obj.save()

        from .models import PropertyImage
        image_keys = [
            ('add_img_1', 'front_image_name'),
            ('add_img_2', 'back_image_name'),
            ('add_img_3', 'right_image_name'),
            ('add_img_4', 'left_image_name'),
        ]
        for img_key, name_key in image_keys:
            file = request.FILES.get(img_key)
            if file:
                caption = request.POST.get(name_key, '').strip()
                PropertyImage.objects.create(
                    property=property_obj,
                    image=file,
                    caption=caption
                )

        messages.success(request, "Property updated successfully and submitted for review.")
        return redirect('listing')

    context = {'property': property_obj}
    return render(request, 'accounts/add_property.html', context)



@login_required
def toggle_active_property(request, pk):
    property_obj = get_object_or_404(Property, pk=pk, user=request.user)
    if property_obj.status == 'Published':
        property_obj.is_active = not property_obj.is_active
        property_obj.save()
        if property_obj.is_active:
            messages.success(request, "Property activated and visible to customers.")
        else:
            messages.success(request, "Property deactivated (hidden from customers).")
    else:
        messages.error(request, "Cannot toggle — property is not published yet.")
    return redirect('listing')


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


@login_required
def profile_view(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)
    if request.method == 'POST':
        user.first_name = request.POST.get('full_name', '')
        user.email = request.POST.get('email', user.email)
        user.phone_number = request.POST.get('phone_number', '')
        user.save()
        profile.location = request.POST.get('location', '')
        profile.whatsapp = request.POST.get('whatsapp', '')
        profile.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('profile')
    context = {
        'user': user,
        'profile': profile,
        'full_name': user.get_full_name(),
        'email': user.email,
        'phone_number': user.phone_number,
        'location': profile.location,
        'whatsapp': profile.whatsapp,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_gallery(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST' and request.FILES.get('avatar'):
        profile.avatar = request.FILES['avatar']
        profile.save()
        messages.success(request, "Profile picture updated!")
        return redirect('profile_gallery')
    return render(request, 'accounts/profile_gallery.html', {'profile': profile})


def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = CustomUser.objects.get(email=email)
            VerificationCode.objects.filter(user=user, is_used=False, expires_at__gt=timezone.now()).update(is_used=True)
            verification_code = VerificationCode.objects.create(user=user)
            subject = 'Password Reset Verification Code'
            message = render_to_string('accounts/password_reset_email.html', {
                'user': user,
                'code': verification_code.code,
                'expiration_minutes': 15,
            })
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=message)
            messages.success(request, "A verification code has been sent to your email address.")
            return redirect(reverse('reset_password_confirm') + f'?email={email}')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ForgotPasswordForm()
    return render(request, 'accounts/forgot_password.html', {'form': form})

from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from django.contrib.auth import update_session_auth_hash

@login_required
def reset_change_password_view(request):
    if request.method == 'POST':
        form = DjangoPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)  # keeps user logged in after password change
            messages.success(request, "Your password has been changed successfully.")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DjangoPasswordChangeForm(user=request.user)
    return render(request, 'accounts/reset_change_password.html', {'form': form})


def reset_password_confirm_view(request):
    email = request.GET.get('email', '')
    if not email:
        messages.error(request, "Email is required to reset password.")
        return redirect('forgot_password')
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        messages.error(request, "No user found with this email.")
        return redirect('forgot_password')
    if request.method == 'POST':
        form = ResetPasswordConfirmForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['verification_code']
            try:
                verification_instance = VerificationCode.objects.filter(
                    user=user, code=code, is_used=False, expires_at__gt=timezone.now()
                ).order_by('-created_at').first()
                if not verification_instance:
                    raise VerificationCode.DoesNotExist
                form.save(user)
                verification_instance.is_used = True
                verification_instance.save()
                messages.success(request, "Your password has been reset successfully. Please log in.")
                return redirect('password_reset_complete')
            except VerificationCode.DoesNotExist:
                messages.error(request, "Invalid or expired verification code.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ResetPasswordConfirmForm(initial={'email': email})
    return render(request, 'accounts/reset_password_confirm.html', {'form': form, 'email': email})


def password_reset_done(request):
    return render(request, 'accounts/password_reset_done.html')


def password_reset_complete(request):
    return render(request, 'accounts/password_reset_complete.html')


# ==================== REST API Views ====================

class LoginAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': getattr(user, 'role', 'customer'),
                }
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class RequestResetAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        try:
            user = CustomUser.objects.get(email=email)
            VerificationCode.objects.filter(user=user, is_used=False).update(is_used=True)
            code_obj = VerificationCode.objects.create(user=user)
            return Response({'message': 'Verification code sent', 'code': code_obj.code})
        except CustomUser.DoesNotExist:
            return Response({'error': 'No user with this email'}, status=status.HTTP_404_NOT_FOUND)


class ResetPasswordAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        new_password = request.data.get('new_password')
        try:
            user = CustomUser.objects.get(email=email)
            verification = VerificationCode.objects.filter(
                user=user, code=code, is_used=False, expires_at__gt=timezone.now()
            ).first()
            if not verification:
                return Response({'error': 'Invalid or expired code'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_password)
            user.save()
            verification.is_used = True
            verification.save()
            return Response({'message': 'Password reset successful'})
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def support(request):
    return render(request, 'accounts/support.html')