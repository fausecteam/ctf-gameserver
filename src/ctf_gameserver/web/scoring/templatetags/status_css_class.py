from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()    # pylint: disable=invalid-name

CLASS_MAPPING = {
    _('up'): 'success',
    _('down'): 'danger',
    _('faulty'): 'danger',
    _('flag not found'): 'warning',
    _('recovering'): 'info',
    _('timeout'): 'active'
}


@register.filter
def status_css_class(status):
    """
    Template filter to get the appropriate Bootstrap CSS class for (the string representation of) a status
    from scoring.StatusCheck.STATUSES. Primarily designed for table rows, but the classes might work with
    other objects as well.
    """

    # Use gray background for missing checks
    if not status:
        return 'active'

    return CLASS_MAPPING.get(status, '')
