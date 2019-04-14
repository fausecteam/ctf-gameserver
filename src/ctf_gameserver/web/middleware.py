from django.conf import settings


class CSPMiddlware:
    """
    Middleware which adds a 'Content Security Policy' header according to the 'CSP_POLICIES' setting to every
    HTTP response.
    """

    def process_response(self, _, response):
        if settings.CSP_POLICIES:
            policies = []

            for directive, values in settings.CSP_POLICIES.items():
                policies.append(directive + ' ' + ' '.join(values))

            response['Content-Security-Policy'] = '; '.join(policies)

        return response
