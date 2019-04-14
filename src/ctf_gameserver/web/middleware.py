from django.conf import settings


def csp_middleware(get_response):
    """
    Middleware which adds a 'Content Security Policy' header according to the 'CSP_POLICIES' setting to every
    HTTP response.
    """

    def middleware(request):
        response = get_response(request)

        if settings.CSP_POLICIES:
            policies = []

            for directive, values in settings.CSP_POLICIES.items():
                policies.append(directive + ' ' + ' '.join(values))

            response['Content-Security-Policy'] = '; '.join(policies)

        return response

    return middleware
