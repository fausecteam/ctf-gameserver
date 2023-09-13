from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import re_path as url, reverse_lazy

from .registration import views as registration_views
from .scoring import views as scoring_views
from .flatpages import views as flatpages_views
from .vpnstatus import views as vpnstatus_views
from .admin import admin_site
from .forms import TeamAuthenticationForm, FormalPasswordResetForm

# pylint: disable=invalid-name


urlpatterns = [
    url(r'^auth/register/$',
        registration_views.register,
        name='register'
    ),    # noqa
    url(r'^auth/confirm-email/$',
        registration_views.confirm_email,
        name='confirm_email'
    ),
    url(r'^auth/edit-team/$',
        registration_views.edit_team,
        name='edit_team'
    ),
    url(r'^auth/delete-team/$',
        registration_views.delete_team,
        name='delete_team'
    ),

    url(r'^auth/login/$',
        auth_views.LoginView.as_view(template_name='login.html', authentication_form=TeamAuthenticationForm),
        name='login'
    ),
    url(r'^auth/logout/$',
        auth_views.LogoutView.as_view(next_page=settings.HOME_URL),
        name='logout'
    ),
    url(r'^auth/change-password/$',
        auth_views.PasswordChangeView.as_view(template_name='password_change.html',
                                              success_url=reverse_lazy('edit_team')),
        name='password_change'
    ),
    url(r'^auth/reset-password/$',
        auth_views.PasswordResetView.as_view(template_name='password_reset.html',
                                             email_template_name='password_reset_mail.txt',
                                             subject_template_name='password_reset_subject.txt',
                                             form_class=FormalPasswordResetForm),
        name='password_reset'
    ),
    url(r'^auth/reset-password/done/$',
        auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'),
        name='password_reset_done'
    ),
    url(r'^auth/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]+)/$',
        auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'),
        name='password_reset_confirm'
    ),
    url(r'^auth/reset/complete/$',
        auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'),
        name='password_reset_complete'
    ),

    url(r'^competition/teams/$',
        registration_views.TeamList.as_view(),
        name='team_list'
    ),
    url(r'^competition/teams\.json$',
        scoring_views.teams_json,
        name='team_json'
    ),
    url(r'^competition/scoreboard/$',
        scoring_views.scoreboard,
        name='scoreboard'
    ),
    url(r'^competition/scoreboard\.json$',
        scoring_views.scoreboard_json,
        name='scoreboard_json'
    ),
    url(r'^competition/scoreboard-ctftime\.json$',
        scoring_views.scoreboard_json_ctftime,
        name='scoreboard_json_ctftime'
    ),
    url(r'^competition/status/$',
        scoring_views.service_status,
        name='service_status'
    ),
    url(r'^competition/status\.json$',
        scoring_views.service_status_json,
        name='service_status_json'
    ),

    url(r'^vpn-status/$',
        vpnstatus_views.status_history,
        name='status_history'
    ),

    url(r'^downloads/$',
        registration_views.list_team_downloads,
        name='list_team_downloads'
    ),
    url(r'^downloads/(?P<filename>[^/]+)$',
        registration_views.get_team_download,
        name='get_team_download'
    ),

    url(r'^internal/mail-teams/$',
        registration_views.mail_teams,
        name='mail_teams'
    ),
    url(r'^internal/service-history$',
        scoring_views.service_history,
        name='service_history'
    ),
    url(r'^internal/service-history\.json$',
        scoring_views.service_history_json,
        name='service_history_json'
    ),
    url(r'^internal/missing-checks$',
        scoring_views.missing_checks,
        name='missing_checks'
    ),
    url(r'^internal/missing-checks\.json$',
        scoring_views.missing_checks_json,
        name='missing_checks.json'
    ),
    url(r'^admin/', admin_site.urls),

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

# This will only have an effect during development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
