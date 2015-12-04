from django.core.urlresolvers import reverse
from django.conf import settings


class CSPMiddlware:
    """
    Middleware which adds a 'Content Security Policy' header according to the 'CSP_POLICIES' setting to every
    HTTP response.
    """

    def process_response(self, request, response):
        if settings.CSP_POLICIES:
            # REVISIT: This shall be removed when https://code.djangoproject.com/ticket/25165 is fixed
            if request.path_info.startswith(reverse('admin:index')):
                return response

            policies = []

            for directive, values in settings.CSP_POLICIES.items():
                policies.append(directive + ' ' + ' '.join(values))

            response['Content-Security-Policy'] = '; '.join(policies)

        return response
