from django import template

register = template.Library()    # pylint: disable=invalid-name


@register.filter
def dict_access(dictionary, key):
    """
    Template filter to get the value from a dictionary depending on a variable key.
    """

    return dictionary.get(key, '')
