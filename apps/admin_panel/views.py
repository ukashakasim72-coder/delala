from datetime import timedelta, datetime
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from django.contrib import messages
from apps.accounts.models import Property, PropertyImage
from apps.accounts.models import User, Property, Profile, VerificationCode, Promotion
from rest_framework.exceptions import PermissionDenied
from datetime import datetime, timedelta, date
from django.contrib.auth import login as auth_login
from django.core.exceptions import PermissionDenied


# ---------- helper decorator ----------
def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_panel:login')
        if not (request.user.is_staff or
                getattr(request.user, 'is_admin', False) or
                getattr(request.user, 'role', '') == 'admin'):
            raise PermissionDenied("You do not have permission to perform this action.")
        return view_func(request, *args, **kwargs)
    return wrapper

# ---------- admin login ----------
def admin_login(request):
    if request.user.is_authenticated and request.user.role == 'admin':
        return redirect('admin_panel:dashboard')
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None and user.role == 'admin':
            login(request, user)
            return redirect('admin_panel:dashboard')
        else:
            messages.error(request, "Invalid credentials or not an admin.")
    return render(request, 'admin_panel/login.html')

def admin_logout(request):
    logout(request)
    return redirect('admin_panel:login')

@admin_required
def admin_forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        code = request.POST.get('code')
        new_pass = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')
        if new_pass != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, 'admin_panel/forgot_password.html')
        try:
            user = User.objects.get(email=email, role='admin')
        except User.DoesNotExist:
            messages.error(request, "No admin user with this email.")
            return render(request, 'admin_panel/forgot_password.html')
        try:
            verification = VerificationCode.objects.filter(
                user=user, code=code, is_used=False, expires_at__gt=timezone.now()
            ).latest('created_at')
        except VerificationCode.DoesNotExist:
            messages.error(request, "Invalid or expired code.")
            return render(request, 'admin_panel/forgot_password.html')
        user.set_password(new_pass)
        user.save()
        verification.is_used = True
        verification.save()
        messages.success(request, "Password reset successfully. Please log in.")
        return redirect('admin_panel:login')
    return render(request, 'admin_panel/forgot_password.html')


@admin_required
def admin_edit_property(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)

    if request.method == 'POST':
        property_obj.property_name = request.POST.get('property_name')
        property_obj.price = request.POST.get('price')
        property_obj.property_type = request.POST.get('type')
        property_obj.location = request.POST.get('location')
        property_obj.bedrooms = request.POST.get('bedrooms')
        property_obj.description = request.POST.get('description')
        property_obj.bathrooms = request.POST.get('bathrooms')
        property_obj.square_meters = request.POST.get('square_meters')

        if request.FILES.get('add_img_1'):
            property_obj.image = request.FILES.get('add_img_1')

        property_obj.save()

        for key in ['add_img_2', 'add_img_3', 'add_img_4']:
            file = request.FILES.get(key)
            if file:
                PropertyImage.objects.create(property=property_obj, image=file)

        messages.success(request, f"Property '{property_obj.property_name}' updated.")

        next_url = request.POST.get('next', '')
        if next_url == 'manage':
            return redirect('admin_panel:manage_listings')
        return redirect('admin_panel:approve_listings')

    next_url = request.GET.get('next', 'approve')
    return render(request, 'admin_panel/admin_edit_property.html', {
        'property': property_obj,
        'next': next_url,
    })


# ---------- dashboard ----------
@admin_required
def dashboard(request):
    today = timezone.now().date()
    context = {
        'total_listings': Property.objects.count(),
        'total_customers': User.objects.filter(role='customer').count(),
        'total_agents': User.objects.filter(role='agent').count(),
        'active_listings': Property.objects.filter(status='Published').count(),
        'listings_today': Property.objects.filter(created_at__date=today).count(),
        'approved_today': Property.objects.filter(status='Published', created_at__date=today).count(),
        'pending_listings': Property.objects.filter(status='Pending').count(),
    }
    return render(request, 'admin_panel/home.html', context)

# ---------- agents ----------
@admin_required
def agent_list(request):
    agents = User.objects.filter(role='agent').select_related('profile')
    agent_data = []
    for idx, agent in enumerate(agents, start=1):
        agent_data.append({
            'no': idx,
            'full_name': agent.get_full_name(),
            'email': agent.email,
            'created_at': agent.date_joined,
            'phone': agent.phone_number or '',
            'whatsapp': getattr(agent.profile, 'whatsapp', '') if hasattr(agent, 'profile') else '',
            'location': getattr(agent.profile, 'location', '') if hasattr(agent, 'profile') else '',
            'id': agent.id,
            'is_blocked': not agent.is_active,
        })
    return render(request, 'admin_panel/agent_list.html', {'agents': agent_data})


@admin_required
def agent_create(request):
    if request.method == 'POST':
        def get_clean_str(key):
            val = request.POST.get(key, '')
            if isinstance(val, list):
                val = val[0] if val else ''
            return val.strip()

        email = get_clean_str('email')
        phone = get_clean_str('phone')
        whatsapp = get_clean_str('whatsapp')
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        full_name = get_clean_str('full_name')
        location = get_clean_str('location')

        context = {
            'full_name': full_name,
            'phone': phone,
            'location': location,
            'email': email,
            'whatsapp': whatsapp,
            'errors': {},
        }

        errors = {}

        if not full_name:
            errors['full_name'] = "Full name is required."

        if not email:
            errors['email'] = "Email is required."
        elif User.objects.filter(email=email).exists():
            errors['email'] = f"Email '{email}' is already registered."

        if not phone:
            errors['phone'] = "Phone number is required."
        elif User.objects.filter(phone_number=phone).exists():
            errors['phone'] = f"Phone number '{phone}' is already used by another agent."

        if whatsapp:
            existing_profile = Profile.objects.filter(whatsapp=whatsapp).first()
            if existing_profile:
                errors['whatsapp'] = f"WhatsApp number '{whatsapp}' is already used by another agent."

        if not password:
            errors['password'] = "Password is required."
        elif len(password) < 6:
            errors['password'] = "Password must be at least 6 characters."

        if not confirm_password:
            errors['confirm_password'] = "Please confirm your password."
        elif password and password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if errors:
            context['errors'] = errors
            return render(request, 'admin_panel/create_account.html', context)

        try:
            user = User.objects.create_user(email=email, password=password)
        except Exception as e:
            context['errors'] = {'email': f"Error creating user: {str(e)}"}
            return render(request, 'admin_panel/create_account.html', context)

        user.role = 'agent'
        user.is_approved = True   # agents created by admin never need approval
        if full_name:
            parts = full_name.split()
            user.first_name = parts[0]
            user.last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
        user.phone_number = phone
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.location = location
        profile.whatsapp = whatsapp
        if request.FILES.get('national_id_front'):
            profile.national_id_front = request.FILES['national_id_front']
        if request.FILES.get('national_id_back'):
            profile.national_id_back = request.FILES['national_id_back']
        if request.FILES.get('license_front'):
            profile.license_front = request.FILES['license_front']
        if request.FILES.get('license_back'):
            profile.license_back = request.FILES['license_back']
        profile.save()

        messages.success(request, f"Agent {email} created successfully.")
        return redirect('admin_panel:agent_list')

    return render(request, 'admin_panel/create_account.html', {'errors': {}})


@admin_required
def agent_edit(request, pk):
    agent = get_object_or_404(User, pk=pk)
    if agent.role != 'agent':
        messages.error(request, "Not an agent.")
        return redirect('admin_panel:agent_list')

    if request.method == 'POST':
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        whatsapp = request.POST.get('whatsapp')
        full_name = request.POST.get('full_name', '').strip()
        new_password = request.POST.get('new_password')
        location = request.POST.get('location', '')

        if User.objects.filter(email=email).exclude(id=agent.id).exists():
            messages.error(request, f"Email '{email}' is already used by another agent.")
            return render(request, 'admin_panel/create_account.html', {
                'agent': agent, 'full_name': full_name, 'email': email,
                'phone': phone, 'location': location, 'whatsapp': whatsapp, 'is_edit': True,
            })
        if phone and User.objects.filter(phone_number=phone).exclude(id=agent.id).exists():
            messages.error(request, f"Phone number '{phone}' is already used by another agent.")
            return render(request, 'admin_panel/create_account.html', {
                'agent': agent, 'full_name': full_name, 'email': email,
                'phone': phone, 'location': location, 'whatsapp': whatsapp, 'is_edit': True,
            })
        if whatsapp:
            existing_profile = Profile.objects.filter(whatsapp=whatsapp).exclude(user=agent).first()
            if existing_profile:
                messages.error(request, f"WhatsApp number '{whatsapp}' is already used by another agent.")
                return render(request, 'admin_panel/create_account.html', {
                    'agent': agent, 'full_name': full_name, 'email': email,
                    'phone': phone, 'location': location, 'whatsapp': whatsapp, 'is_edit': True,
                })

        agent.email = email
        agent.phone_number = phone
        agent.is_approved = True   # stays approved on edit

        if full_name:
            parts = full_name.split()
            agent.first_name = parts[0]
            agent.last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

        if new_password:
            agent.set_password(new_password)
        agent.save()

        profile = agent.profile
        profile.location = location
        profile.whatsapp = whatsapp

        if request.FILES.get('national_id_front'):
            profile.national_id_front = request.FILES['national_id_front']
        if request.FILES.get('national_id_back'):
            profile.national_id_back = request.FILES['national_id_back']
        if request.FILES.get('license_front'):
            profile.license_front = request.FILES['license_front']
        if request.FILES.get('license_back'):
            profile.license_back = request.FILES['license_back']
        profile.save()

        messages.success(request, "Agent updated successfully.")
        return redirect('admin_panel:agent_list')

    profile = agent.profile
    context = {
        'agent': agent,
        'full_name': agent.get_full_name(),
        'email': agent.email,
        'phone': agent.phone_number,
        'location': profile.location if profile else '',
        'whatsapp': profile.whatsapp if profile else '',
        'avatar_url': profile.avatar.url if profile and profile.avatar else None,
        'national_id_front_url': profile.national_id_front.url if profile and profile.national_id_front else None,
        'national_id_back_url': profile.national_id_back.url if profile and profile.national_id_back else None,
        'license_front_url': profile.license_front.url if profile and profile.license_front else None,
        'license_back_url': profile.license_back.url if profile and profile.license_back else None,
        'is_edit': True,
    }
    return render(request, 'admin_panel/create_account.html', context)


@admin_required
def agent_view(request, pk):
    agent = get_object_or_404(User, pk=pk, role='agent')
    try:
        profile = agent.profile
    except:
        profile = None
    context = {
        'agent': agent,
        'full_name': agent.get_full_name(),
        'email': agent.email,
        'phone': agent.phone_number,
        'location': profile.location if profile else '',
        'whatsapp': profile.whatsapp if profile else '',
        'avatar_url': profile.avatar.url if profile and profile.avatar else None,
        'profile': profile,
    }
    return render(request, 'admin_panel/agent_view.html', context)


def login_as_agent(request, pk):
    if not request.user.is_authenticated or request.user.role != 'admin':
        raise PermissionDenied
    agent = get_object_or_404(User, pk=pk, role='agent')
    agent.backend = 'django.contrib.auth.backends.ModelBackend'
    auth_login(request, agent)
    messages.success(request, f"You are now logged in as {agent.email}.")
    return redirect('listing')


@admin_required
def agent_properties(request, agent_id):
    agent = get_object_or_404(User, id=agent_id, role='agent')
    properties = Property.objects.filter(user=agent).order_by('-created_at')

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

    context = {
        'agent': agent,
        'listings': listings,
    }
    return render(request, 'admin_panel/agent_property.html', context)


@admin_required
def monthly_reports(request):
    today = timezone.now().date()

    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    start_dt = timezone.make_aware(datetime.combine(first_day, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(last_day, datetime.max.time()))

    total_listings = Property.objects.filter(created_at__range=(start_dt, end_dt)).count()
    total_customers = User.objects.filter(role='customer', date_joined__range=(start_dt, end_dt)).count()
    total_agents = User.objects.filter(role='agent', date_joined__range=(start_dt, end_dt)).count()
    active_listings = Property.objects.filter(
        status='Published', is_active=True,
        created_at__range=(start_dt, end_dt)
    ).count()
    listings_today = Property.objects.filter(created_at__date=today).count()
    approved_today = Property.objects.filter(
        status='Published', created_at__date=today
    ).count()

    def fmt(n):
        if n >= 1000:
            return f"{n/1000:.1f}K"
        return str(n)

    months = [
        (1,'January'),(2,'February'),(3,'March'),(4,'April'),
        (5,'May'),(6,'June'),(7,'July'),(8,'August'),
        (9,'September'),(10,'October'),(11,'November'),(12,'December'),
    ]
    years = list(range(2024, today.year + 1))

    context = {
        'total_listings': fmt(total_listings),
        'total_customers': fmt(total_customers),
        'total_agents': fmt(total_agents),
        'active_listings': fmt(active_listings),
        'listings_today': listings_today,
        'approved_today': approved_today,
        'month_range': f"{first_day.strftime('%b')} 1 - {last_day.strftime('%b')} {last_day.day}",
        'selected_month': month,
        'selected_year': year,
        'months': months,
        'years': years,
        'current_month_name': first_day.strftime('%B %Y'),
    }
    return render(request, 'admin_panel/monthly_reports.html', context)


@admin_required
def delete_agent(request, pk):
    agent = get_object_or_404(User, pk=pk, role='agent')
    agent.delete()
    messages.success(request, "Agent deleted successfully.")
    return redirect('admin_panel:agent_list')


@admin_required
def block_agent(request, pk):
    agent = get_object_or_404(User, pk=pk, role='agent')

    agent.is_active = not agent.is_active
    agent.save()

    if not agent.is_active:
        updated = Property.objects.filter(user=agent, status='Published').update(status='Inactive')
        messages.success(request, f"Agent {agent.email} has been blocked. {updated} active listings moved to Inactive.")
    else:
        updated = Property.objects.filter(user=agent, status='Inactive').update(status='Published')
        messages.success(request, f"Agent {agent.email} has been unblocked. {updated} listings restored to Published.")

    return redirect('admin_panel:agent_list')

# ---------- customers ----------
@admin_required
def customer_list(request):
    customers = User.objects.filter(role='customer').select_related('profile')
    customer_data = []
    for idx, cust in enumerate(customers, start=1):
        customer_data.append({
            'no': idx,
            'id': cust.id,
            'full_name': cust.get_full_name(),
            'email': cust.email,
            'phone': cust.phone_number or '',
            'location': getattr(cust.profile, 'location', '') if hasattr(cust, 'profile') else '',
            'is_blocked': not cust.is_active,
            'is_approved': cust.is_approved,
        })
    return render(request, 'admin_panel/customer_list.html', {'customers': customer_data})


@admin_required
def customer_edit(request, pk):
    customer = get_object_or_404(User, pk=pk, role='customer')
    profile, _ = Profile.objects.get_or_create(user=customer)
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        if full_name:
            parts = full_name.split(' ', 1)
            customer.first_name = parts[0]
            customer.last_name = parts[1] if len(parts) > 1 else ''
        customer.email = request.POST.get('email', customer.email)
        customer.phone_number = request.POST.get('phone', '')
        new_password = request.POST.get('new_password', '')
        if new_password:
            customer.set_password(new_password)
        customer.save()
        profile.location = request.POST.get('location', '')
        profile.whatsapp = request.POST.get('whatsapp', '')
        profile.save()
        messages.success(request, f"Customer updated successfully.")
        return redirect('admin_panel:customer_list')
    context = {
        'customer': customer,
        'full_name': customer.get_full_name(),
        'email': customer.email,
        'phone': customer.phone_number or '',
        'location': profile.location,
        'whatsapp': profile.whatsapp,
    }
    return render(request, 'admin_panel/customer_edit.html', context)


@admin_required
def delete_customer(request, pk):
    customer = get_object_or_404(User, pk=pk, role='customer')
    customer.delete()
    messages.success(request, "Customer deleted successfully.")
    return redirect('admin_panel:customer_list')


@admin_required
def block_customer(request, pk):
    customer = get_object_or_404(User, pk=pk, role='customer')
    customer.is_active = not customer.is_active
    customer.save()
    state = "unblocked" if customer.is_active else "blocked"
    messages.success(request, f"Customer has been {state}.")
    return redirect('admin_panel:customer_list')


@admin_required
def approve_customer(request, pk):
    customer = get_object_or_404(User, pk=pk, role='customer')
    customer.is_approved = not customer.is_approved
    customer.save()
    state = "approved" if customer.is_approved else "set to pending"
    messages.success(request, f"Customer has been {state}.")
    return redirect('admin_panel:customer_list')


# ---------- listings ----------
@admin_required
def manage_listings(request):
    published_listings = Property.objects.filter(status='Published').order_by('-created_at')
    listings = []
    for prop in published_listings:
        property_code = f"ID: #{prop.id + 1000}"
        listings.append({
            'id': prop.id,
            'property_name': prop.property_name,
            'property_code': property_code,
            'type': prop.get_property_type_display(),
            'price': prop.price,
            'created_at': prop.created_at.strftime('%d %B, %Y'),
            'agent_name': prop.user.get_full_name() or prop.user.email,
            'status': prop.status,
            'image': prop.image,
        })
    return render(request, 'admin_panel/manage_listings.html', {'listings': listings})


@admin_required
def delete_listing(request, pk):
    listing = get_object_or_404(Property, pk=pk)
    listing.delete()
    messages.success(request, "Listing deleted successfully.")
    return redirect('admin_panel:manage_listings')


@admin_required
def toggle_listing_status(request, listing_id):
    property_obj = get_object_or_404(Property, pk=listing_id)
    if property_obj.status == 'Published':
        property_obj.status = 'Pending'
        messages.success(request, f"Property '{property_obj.property_name}' changed to Pending.")
    elif property_obj.status == 'Pending':
        property_obj.status = 'Published'
        messages.success(request, f"Property '{property_obj.property_name}' changed to Published.")
    else:
        messages.error(request, "Cannot change status of this property.")
        return redirect('admin_panel:manage_listings')
    property_obj.save()
    return redirect('admin_panel:manage_listings')


@admin_required
def approve_listings(request):
    pending_listings = Property.objects.filter(status='Pending').order_by('-created_at')

    listings = []
    for prop in pending_listings:
        listings.append({
            'id': prop.id,
            'property': prop.property_name,
            'type': prop.get_property_type_display(),
            'price': prop.price,
            'created_at': prop.created_at.strftime('%d %B, %Y'),
            'agent_name': prop.user.get_full_name() or prop.user.email,
            'status': prop.status,
            'image': prop.image,
        })
    return render(request, 'admin_panel/approve_listings.html', {'listings': listings})


@admin_required
def approve_listing_action(request, pk):
    listing = get_object_or_404(Property, pk=pk)
    listing.status = 'Published'
    listing.save()
    messages.success(request, f"Listing '{listing.property_name}' approved and published.")
    return redirect('admin_panel:approve_listings')


@admin_required
def reject_listing_action(request, pk):
    listing = get_object_or_404(Property, pk=pk)
    listing.status = 'Rejected'
    listing.save()
    messages.success(request, "Listing rejected.")
    return redirect('admin_panel:approve_listings')

# ---------- property detail ----------
@admin_required
def property_detail(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    created_date = property_obj.created_at.strftime('%B %d, %Y')
    created_time = property_obj.created_at.strftime('%I:%M %p')
    display_code = f"Codo-{property_obj.id + 1000}"
    agent = property_obj.user
    agent_full_name = agent.get_full_name() or agent.email
    agent_email = agent.email
    agent_phone = agent.phone_number or "Not provided"
    try:
        profile = agent.profile
        agent_location = profile.location or "Not provided"
        profile_avatar_url = profile.avatar.url if profile.avatar else None
    except:
        agent_location = "Not provided"
        profile_avatar_url = None
    try:
        additional_images = property_obj.additional_images.all()
    except:
        additional_images = []
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
    return render(request, 'admin_panel/property_detail.html', context)


# ---------- promotions ----------
@admin_required
def add_promotion(request):
    properties = Property.objects.filter(status='Published').order_by('-created_at')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Promotion title is required.")
            return render(request, 'admin_panel/add_promotion.html', {'properties': properties})

        property_obj = None
        property_id = request.POST.get('property_id', '').strip()
        if property_id:
            try:
                property_obj = Property.objects.get(pk=int(property_id))
            except (Property.DoesNotExist, ValueError):
                pass

        agent_phone = request.POST.get('agent_phone', '').strip()
        if not agent_phone and property_obj:
            agent_phone = property_obj.user.phone_number or ''

        promotion = Promotion.objects.create(
            title=title,
            description=request.POST.get('description', '').strip(),
            promotion_type=request.POST.get('promotion_type', 'featured'),
            discount_text=request.POST.get('discount_text', '').strip(),
            property=property_obj,
            agent_phone=agent_phone,
            property_name=request.POST.get('property_name', '').strip(),
            price=request.POST.get('price', '').strip(),
            property_type=request.POST.get('type', '').strip(),
            location=request.POST.get('location', '').strip(),
            bedrooms=request.POST.get('bedrooms', '').strip(),
            bathrooms=request.POST.get('bathrooms', '').strip(),
            square_meters=request.POST.get('square_meters', '').strip(),
            image=request.FILES.get('add_img_1') or None,
            image_2=request.FILES.get('add_img_2') or None,
            image_3=request.FILES.get('add_img_3') or None,
            image_4=request.FILES.get('add_img_4') or None,
            caption_1=request.POST.get('front_image_name', '').strip(),
            caption_2=request.POST.get('back_image_name', '').strip(),
            caption_3=request.POST.get('right_image_name', '').strip(),
            caption_4=request.POST.get('left_image_name', '').strip(),
            is_active=request.POST.get('is_active') == 'on',
            created_by=request.user,
        )
        messages.success(request, f"Promotion #{promotion.id} '{promotion.title}' saved.")
        return redirect('admin_panel:promotion_list')

    return render(request, 'admin_panel/add_promotion.html', {'properties': properties})


@admin_required
def promotion_list(request):
    promotions = Promotion.objects.all().order_by('-created_at')
    return render(request, 'admin_panel/promotion_list.html', {'promotions': promotions})


@admin_required
def delete_promotion(request, pk):
    promotion = get_object_or_404(Promotion, pk=pk)
    promotion.delete()
    messages.success(request, "Promotion deleted.")
    return redirect('admin_panel:promotion_list')


@admin_required
def toggle_promotion(request, pk):
    promotion = get_object_or_404(Promotion, pk=pk)
    promotion.is_active = not promotion.is_active
    promotion.save()
    state = "activated" if promotion.is_active else "deactivated"
    messages.success(request, f"Promotion '{promotion.title}' {state}.")
    return redirect('admin_panel:promotion_list')



