from django.utils.functional import lazy


def _format_proxy(proxy, *args, **kwargs):
    """
    Helper function to enable string formatting of lazy translation objects.
    This appears to work alright, but I'm not quite sure.
    """
    return str(proxy).format(*args, **kwargs)


format_lazy = lazy(_format_proxy, str)    # pylint: disable=invalid-name
