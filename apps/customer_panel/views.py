from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone  # <-- added
from django.db.models import Count, Prefetch
from apps.accounts.models import Property, Profile, User
from .models import SavedProperty, PropertyLike, PropertyComment, PropertyRating


def customer_login(request):
    if request.user.is_authenticated and request.user.role == 'customer':
        if request.user.is_approved:
            return redirect('customer_panel:home')

    if request.method == 'POST':
        login_type = request.POST.get('login_type', 'phone')
        password = request.POST.get('password', '')

        if login_type == 'email':
            email = request.POST.get('email', '').strip().lower()
            if not email or not password:
                messages.error(request, "Email and password are required.")
                return render(request, 'customer_panel/login.html')
            try:
                user = User.objects.get(email=email, role='customer')
            except User.DoesNotExist:
                messages.error(request, "Invalid email or password.")
                return render(request, 'customer_panel/login.html')
        else:
            phone = request.POST.get('phone', '').strip()
            if not phone or not password:
                messages.error(request, "Phone number and password are required.")
                return render(request, 'customer_panel/login.html')
            try:
                user = User.objects.get(phone_number=phone, role='customer')
            except User.DoesNotExist:
                messages.error(request, "Invalid phone number or password.")
                return render(request, 'customer_panel/login.html')

        auth_user = authenticate(request, username=user.email, password=password)

        if auth_user is None:
            messages.error(request, "Invalid credentials.")
            return render(request, 'customer_panel/login.html')

        if not auth_user.is_active:
            messages.error(request, "Your account has been blocked. Contact support.")
            return render(request, 'customer_panel/login.html')

        if not auth_user.is_approved:
            messages.warning(request, "Your account is pending admin approval.")
            return render(request, 'customer_panel/login.html')

        login(request, auth_user)
        return redirect('customer_panel:home')

    return render(request, 'customer_panel/login.html')


def customer_register(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not full_name or not phone or not password:
            messages.error(request, "All fields are required.")
            return render(request, 'customer_panel/register.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'customer_panel/register.html')

        if User.objects.filter(phone_number=phone).exists():
            messages.error(request, "This phone number is already registered.")
            return render(request, 'customer_panel/register.html')

        internal_email = f"{phone}@digitaldelala.com"

        if User.objects.filter(email=internal_email).exists():
            messages.error(request, "This phone number is already registered.")
            return render(request, 'customer_panel/register.html')

        user = User.objects.create_user(
            email=internal_email,
            password=password,
            phone_number=phone,
            role='customer',
            first_name=full_name,
            is_approved=True,
        )

        auth_user = authenticate(request, username=internal_email, password=password)
        if auth_user:
            login(request, auth_user)
            return redirect('customer_panel:home')

        messages.success(request, "Registration successful! Please log in.")
        return redirect('customer_panel:login')

    return render(request, 'customer_panel/register.html')



def customer_register_email(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not full_name or not email or not password:
            messages.error(request, "All fields are required.")
            return render(request, 'customer_panel/register.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'customer_panel/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return render(request, 'customer_panel/register.html')

        user = User.objects.create_user(
            email=email,
            password=password,
            role='customer',
            first_name=full_name,
            is_approved=True,
        )

        auth_user = authenticate(request, username=email, password=password)
        if auth_user:
            login(request, auth_user)
            return redirect('customer_panel:home')

        messages.success(request, "Registration successful! Please log in.")
        return redirect('customer_panel:login')

    return render(request, 'customer_panel/register.html')



def customer_logout(request):
    logout(request)
    return redirect('customer_panel:home')   # <-- changed from 'login' to 'home'

def _customer_required(request):
    return (
        request.user.is_authenticated and
        request.user.role == 'customer' and
        request.user.is_active and
        request.user.is_approved
    )


def get_relative_time(dt):
    now = timezone.now()
    diff = now - dt
    seconds = int(diff.total_seconds())
    minutes = seconds // 60
    hours = minutes // 60
    days = diff.days
    weeks = days // 7
    months = days // 30
    years = days // 365

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
    elif months > 0 and months < 12:   # <-- key change: check months > 0
        return f"{months} month ago" if months == 1 else f"{months} months ago"
    else:
        # If months == 0 but weeks >= 4, it falls here – treat as weeks
        if months == 0:
            return f"{weeks} weeks ago"
        # Otherwise, handle years
        if years == 0:
            return f"{months} months ago"
        return f"{years} year ago" if years == 1 else f"{years} years ago"

from apps.accounts.models import Promotion

# customer_panel/views.py

from django.db.models import Avg   # ensure this import is present

def home(request):
    properties = Property.objects.filter(
        status='Published', is_active=True
    ).annotate(
        avg_rating=Avg('ratings__rating')
    ).order_by('-created_at')

    promotions = Promotion.objects.filter(is_active=True).order_by('-created_at')

    saved_ids = []
    liked_ids = []
    if request.user.is_authenticated and request.user.role == 'customer':
        saved_ids = list(SavedProperty.objects.filter(
            user=request.user
        ).values_list('property_id', flat=True))
        liked_ids = list(PropertyLike.objects.filter(
            user=request.user
        ).values_list('property_id', flat=True))

    for prop in properties:
        first_img = prop.additional_images.first()
        prop.front_image = first_img.image.url if first_img else (prop.image.url if prop.image else None)
        prop.front_caption = first_img.caption if first_img else ''
        prop.time_ago = get_relative_time(prop.created_at)
        prop.likes_count = prop.likes.count()
        prop.comments_count = prop.comments.count()
        agent = prop.user
        agent_phone = ''
        if agent.phone_number and agent.phone_number.strip():
            agent_phone = agent.phone_number.strip()
        else:
            try:
                if agent.profile.whatsapp and agent.profile.whatsapp.strip():
                    agent_phone = agent.profile.whatsapp.strip()
            except Exception:
                pass
        prop.agent_phone = agent_phone

    context = {
        'properties': properties,
        'promotions': promotions,
        'saved_ids': saved_ids,
        'liked_ids': liked_ids,
    }
    return render(request, 'customer_panel/home.html', context)
def forgot_password(request):
    if request.user.is_authenticated and request.user.role == 'customer':
        return redirect('customer_panel:home')

    if request.method == 'POST':
        login_type = request.POST.get('login_type', 'phone')
        user = None

        if login_type == 'email':
            email = request.POST.get('email', '').strip().lower()
            if not email:
                messages.error(request, "Email is required.")
                return render(request, 'customer_panel/forgot_password.html')
            try:
                user = User.objects.get(email=email, role='customer')
            except User.DoesNotExist:
                messages.error(request, "No customer account found with this email.")
                return render(request, 'customer_panel/forgot_password.html')
        else:
            phone = request.POST.get('phone', '').strip()
            if not phone:
                messages.error(request, "Phone number is required.")
                return render(request, 'customer_panel/forgot_password.html')
            try:
                user = User.objects.get(phone_number=phone, role='customer')
            except User.DoesNotExist:
                messages.error(request, "No customer account found with this phone number.")
                return render(request, 'customer_panel/forgot_password.html')

        # In production, send reset link/code here.
        messages.success(request, f"Password reset instructions sent to {user.email if login_type == 'email' else user.phone_number}.")
        return redirect('customer_panel:login')

    return render(request, 'customer_panel/forgot_password.html')


def toggle_save(request, pk):
    if not _customer_required(request):
        return redirect('customer_panel:login')
    property_obj = get_object_or_404(Property, pk=pk)
    saved_obj, created = SavedProperty.objects.get_or_create(
        user=request.user,
        property=property_obj
    )
    if not created:
        saved_obj.delete()
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/customer/home/'
    return redirect(next_url)


from django.db.models import Count, Prefetch   # <-- add this
from django.shortcuts import render, redirect
# ... other imports

def saved(request):
    if not _customer_required(request):
        return redirect('customer_panel:login')

    saved_properties = SavedProperty.objects.filter(
        user=request.user
    ).select_related('property').order_by('-saved_at')

    liked_ids = list(PropertyLike.objects.filter(
        user=request.user
    ).values_list('property_id', flat=True))

    saved_ids = list(SavedProperty.objects.filter(
        user=request.user
    ).values_list('property_id', flat=True))

    properties = []
    for sp in saved_properties:
        prop = sp.property
        # Skip unpublished
        if prop.status != 'Published' or not prop.is_active:
            continue

        prop.created_at_display = get_relative_time(prop.created_at)
        prop.likes_count = prop.likes.count()
        prop.comments_count = prop.comments.count()

        # Phone from user.phone_number or profile.whatsapp
        agent = prop.user
        agent_phone = ''
        if agent.phone_number and agent.phone_number.strip():
            agent_phone = agent.phone_number.strip()
        else:
            try:
                if agent.profile.whatsapp and agent.profile.whatsapp.strip():
                    agent_phone = agent.profile.whatsapp.strip()
            except Exception:
                pass
        prop.agent_phone = agent_phone

        properties.append(prop)

    context = {
        'properties': properties,
        'saved_ids': saved_ids,
        'liked_ids': liked_ids,
    }
    return render(request, 'customer_panel/saved.html', context)


def property_view(request, pk):
    if not _customer_required(request):
        return redirect('customer_panel:login')
    property_obj = get_object_or_404(Property, pk=pk, status='Published')
    additional_images = property_obj.additional_images.all()
    is_saved = SavedProperty.objects.filter(
        user=request.user, property=property_obj
    ).exists()
    agent = property_obj.user
    try:
        agent_profile = agent.profile
        agent_phone = agent_profile.whatsapp or agent.phone_number or 'Not provided'
        agent_avatar = agent_profile.avatar.url if agent_profile.avatar else None
        agent_location = agent_profile.location or 'Not provided'
    except Exception:
        agent_phone = agent.phone_number or 'Not provided'
        agent_avatar = None
        agent_location = 'Not provided'
    context = {
        'property': property_obj,
        'additional_images': additional_images,
        'is_saved': is_saved,
        'agent': agent,
        'agent_phone': agent_phone,
        'agent_avatar': agent_avatar,
        'agent_location': agent_location,
    }
    return render(request, 'customer_panel/property_view.html', context)


def toggle_like(request, pk):
    if not _customer_required(request):
        return redirect('customer_panel:login')
    if request.method == 'POST':
        property_obj = get_object_or_404(Property, pk=pk)
        like_obj, created = PropertyLike.objects.get_or_create(
            user=request.user, property=property_obj
        )
        if not created:
            like_obj.delete()
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/customer/home/'
        return redirect(next_url)
    return redirect('customer_panel:home')


def property_comments(request, pk):
    if not _customer_required(request):
        return redirect('customer_panel:login')

    property_obj = get_object_or_404(Property, pk=pk, status='Published')
    comments = PropertyComment.objects.filter(
        property=property_obj
    ).select_related('user').order_by('-created_at')

    all_ratings = PropertyRating.objects.filter(property=property_obj)
    avg_rating = 0
    if all_ratings.exists():
        avg_rating = round(sum(r.rating for r in all_ratings) / all_ratings.count(), 1)

    user_rating = 0
    try:
        user_rating = PropertyRating.objects.get(
            user=request.user, property=property_obj
        ).rating
    except PropertyRating.DoesNotExist:
        pass

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            PropertyComment.objects.create(
                user=request.user,
                property=property_obj,
                text=text
            )

        rating_val = request.POST.get('rating', '').strip()
        if rating_val and rating_val.isdigit():
            rating_int = int(rating_val)
            if 1 <= rating_int <= 5:
                PropertyRating.objects.update_or_create(
                    user=request.user,
                    property=property_obj,
                    defaults={'rating': rating_int}
                )

        return redirect('customer_panel:property_comments', pk=pk)

    context = {
        'property': property_obj,
        'comments': comments,
        'comments_count': comments.count(),
        'avg_rating': avg_rating,
        'user_rating': user_rating,
    }
    return render(request, 'customer_panel/comments.html', context)


def customer_profile(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        if full_name:
            parts = full_name.split()
            user.first_name = parts[0]
            user.last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
        user.phone_number = request.POST.get('phone_number', '')
        user.save()

        profile.location = request.POST.get('location', '')
        profile.whatsapp = request.POST.get('whatsapp', '')

        if request.FILES.get('avatar'):
            profile.avatar = request.FILES['avatar']
            profile.save()
            messages.success(request, "Profile picture updated.")
        else:
            profile.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('customer_panel:profile')

    context = {
        'user': user,
        'profile': profile,
        'full_name': user.get_full_name(),
    }
    return render(request, 'customer_panel/profile.html', context)


from django.contrib.auth import update_session_auth_hash

def change_password(request):
    if not _customer_required(request):
        return redirect('customer_panel:login')

    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not request.user.check_password(old_password):
            messages.error(request, "Old password is incorrect.")
            return render(request, 'customer_panel/change_password.html')

        if len(new_password) < 8:
            messages.error(request, "New password must be at least 8 characters.")
            return render(request, 'customer_panel/change_password.html')

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return render(request, 'customer_panel/change_password.html')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)  # keeps user logged in after password change
        messages.success(request, "Password updated successfully!")
        return redirect('customer_panel:profile')

    return render(request, 'customer_panel/change_password.html')

def support(request):
    if not _customer_required(request):
        return redirect('customer_panel:login')
    if request.method == 'POST':
        messages.success(request, 'Your message has been sent. We will get back to you soon.')
        return redirect('customer_panel:support')
    return render(request, 'customer_panel/support.html')



def reset_confirm(request):
    if request.user.is_authenticated and request.user.role == 'customer':
        return redirect('customer_panel:home')

    if request.method == 'POST':
        email = request.POST.get('email')
        code = request.POST.get('code')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # Basic validation (no actual token check – you can extend later)
        if not new_password or not confirm_password:
            messages.error(request, "Please fill in all password fields.")
            return render(request, 'customer_panel/reset_confirm.html', {'email': email})

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'customer_panel/reset_confirm.html', {'email': email})

        # In a real app, you would validate the code against a stored token
        # and find the user by email, then set the new password.
        # For now, just show a success message.
        messages.success(request, "Your password has been reset successfully. Please log in.")
        return redirect('customer_panel:login')

    email = request.GET.get('email', '')
    return render(request, 'customer_panel/reset_confirm.html', {'email': email})

