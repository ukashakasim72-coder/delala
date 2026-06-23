from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class UserLoginForm(AuthenticationForm):
    email = forms.EmailField(
        label="Email",
        widget=forms.TextInput(attrs={'autocomplete': 'email', 'autofocus': True, 'class': 'form-input-field'}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'class': 'form-input-field'}),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        if 'username' in self.fields:
            del self.fields['username']

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Invalid login credentials.")
            if not self.user_cache.is_active:
                raise forms.ValidationError("This account is inactive.")
        else:
            self.user_cache = None
            if not email:
                raise forms.ValidationError("Email is required.")
            if not password:
                raise forms.ValidationError("Password is required.")
        return self.cleaned_data

    def get_user(self):
        return self.user_cache


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-input-field', 'placeholder': 'example@gmail.com'}),
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No user found with this email address.")
        return email


class ResetPasswordConfirmForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-input-field', 'placeholder': 'example@gmail.com'})
    )
    verification_code = forms.CharField(
        max_length=5,
        widget=forms.TextInput(attrs={'class': 'form-input-field', 'placeholder': '12876'}),
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input-field', 'placeholder': '••••••••••••••'}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input-field', 'placeholder': '••••••••••••••'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', "Passwords don't match.")
        if new_password and len(new_password) < 8:
            self.add_error('new_password', "Password must be at least 8 characters long.")
        return cleaned_data

    def save(self, user):
        user.set_password(self.cleaned_data['new_password'])
        user.save()


class UserProfileForm(forms.ModelForm):
    full_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input-field'}),
        label="Full name"
    )

    class Meta:
        model = User
        fields = ['full_name', 'email']   # avatar is NOT here – it belongs to Profile model
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-input-field'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            first = self.instance.first_name or ''
            last = self.instance.last_name or ''
            self.initial['full_name'] = f"{first} {last}".strip()
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['email'].help_text = "Email cannot be changed here. Contact support if needed."

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data.get('full_name', '')
        parts = full_name.split(' ', 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ''
        if commit:
            user.save()
        return user

# accounts/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

# apps/accounts/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()

class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input-field', 'placeholder': 'Current password'}),
        label="Old password"
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input-field', 'placeholder': 'New password'}),
        label="New password",
        validators=[validate_password]  # optional but recommended
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input-field', 'placeholder': 'Confirm new password'}),
        label="Confirm password"
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise ValidationError("Your old password is incorrect.")
        return old_password

    def clean(self):
        cleaned_data = super().clean()
        new_pass = cleaned_data.get('new_password')
        confirm_pass = cleaned_data.get('confirm_password')
        if new_pass and confirm_pass and new_pass != confirm_pass:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self):
        """Update the user's password in the database."""
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()
        return self.user


