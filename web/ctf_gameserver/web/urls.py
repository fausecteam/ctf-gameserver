from django.conf import settings
from django.conf.urls import include, url
from django.contrib.auth import views as auth_views

from .registration import views as registration_views
from .flatpages import views as flatpages_views
from .admin import admin_site
from .forms import TeamAuthenticationForm, FormalPasswordResetForm

# pylint: disable=invalid-name, bad-continuation


# Arguments for the django.contrib.auth.views.password_reset view
_password_reset_args = {
    'template_name': 'password_reset.html',
    'email_template_name': 'password_reset_mail.txt',
    'subject_template_name': 'password_reset_subject.txt',
    'password_reset_form': FormalPasswordResetForm,
}


urlpatterns = [
    url(r'^register/$',
        registration_views.register,
        name='register'
    ),    # noqa
    url(r'^confirm-email/$',
        registration_views.confirm_email,
        name='confirm_email'
    ),
    url(r'^edit-team/$',
        registration_views.edit_team,
        name='edit_team'
    ),

    url(r'^login/$',
        auth_views.login,
        {'template_name': 'login.html', 'authentication_form': TeamAuthenticationForm},
        name='login'
    ),
    url(r'^logout/$',
        auth_views.logout,
        {'next_page': settings.HOME_URL},
        name='logout'
    ),
    url(r'^reset-password/$',
        auth_views.password_reset,
        _password_reset_args,
        name='password_reset'
    ),
    url(r'^reset-password/done/$',
        auth_views.password_reset_done,
        {'template_name': 'password_reset_done.html'},
        name='password_reset_done'
    ),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm,
        {'template_name': 'password_reset_confirm.html'},
        name='password_reset_confirm'
    ),

    url(r'^reset/complete/$',
        auth_views.password_reset_complete,
        {'template_name': 'password_reset_complete.html'},
        name='password_reset_complete'
    ),

    url(r'^admin/', include(admin_site.urls)),

    # Multiple seperate URL patterns have to be used to work around
    # https://code.djangoproject.com/ticket/9176
    url(r'^$',
        flatpages_views.flatpage,
        name='home_flatpage'
    ),
    url(r'^(?P<slug>[\w-]+)/$',
        flatpages_views.flatpage,
        name='no_category_flatpage'
    ),
    url(r'^(?P<category>[\w-]+)/(?P<slug>[\w-]+)/$',
        flatpages_views.flatpage,
        name='category_flatpage'
    )
]
