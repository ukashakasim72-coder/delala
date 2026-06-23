from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter


class CustomerSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # Force role = customer for all social logins
        user.role = 'customer'
        user.save()
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        return '/customer/home/'


class CustomerAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        return '/customer/home/'


