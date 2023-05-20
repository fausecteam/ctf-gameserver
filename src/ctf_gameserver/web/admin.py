from django.contrib import admin
from django.utils.functional import classproperty
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from .registration.models import Team
from .registration.admin_inline import InlineTeamAdmin
from .scoring.models import GameControl
from .util import format_lazy


class CTFAdminSite(admin.AdminSite):
    """
    Custom variant of the AdminSite which replaces the default headers and titles.
    """

    index_title = _('Administration home')

    # Declare this lazily through a classproperty in order to avoid a circular dependency when creating
    # migrations
    @classproperty
    def site_header(cls):    # pylint: disable=no-self-argument
        return format_lazy(_('{competition_name} administration'),
                           competition_name=GameControl.get_instance().competition_name)

    @classproperty
    def site_title(cls):    # pylint: disable=no-self-argument
        return cls.site_header


admin_site = CTFAdminSite()    # pylint: disable=invalid-name


@admin.register(User, site=admin_site)
class CTFUserAdmin(UserAdmin):
    """
    Custom variant of UserAdmin which adjusts the displayed, filterable and editable fields and adds an
    InlineModelAdmin for the associated team.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add email field to user creation form
        for fieldset in self.add_fieldsets:
            if fieldset[0] is None:
                fieldset[1]['fields'] += ('email',)

    class TeamListFilter(admin.SimpleListFilter):
        """
        Admin list filter which allows filtering of user lists by whether they are associated with a Team.
        """
        title = _('associated team')
        parameter_name = 'has_team'

        def lookups(self, request, model_admin):
            return (
                ('1', _('Yes')),
                ('0', _('No'))
            )

        def queryset(self, request, queryset):
            if self.value() == '1':
                return queryset.filter(team__isnull=False)
            elif self.value() == '0':
                return queryset.filter(team__isnull=True)
            else:
                return queryset

    def user_has_team(self, user):
        """
        Indicates if the given user is associated with a team or not. This is used as value generator for an
        additional column in user lists.
        """
        try:
            user.team    # pylint: disable=pointless-statement
            return True
        except Team.DoesNotExist:
            return False

    user_has_team.short_description = _('Associated team')
    # Display on/off icons instead of strings for the user_has_team values
    user_has_team.boolean = True
    user_has_team.admin_order_field = 'team'

    list_display = ('username', 'is_active', 'is_staff', 'is_superuser', 'user_has_team', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', TeamListFilter, 'date_joined')
    search_fields = ('username', 'email', 'team__net_number', 'team__informal_email', 'team__affiliation',
                     'team__country')

    fieldsets = (
        (None, {'fields': ('username', 'password', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    inlines = [InlineTeamAdmin]
