from django import template
from django.forms import CheckboxInput, CheckboxSelectMultiple, RadioSelect, MultiWidget
from django.forms.utils import ErrorList
from django.utils.encoding import force_str
from django.utils.html import format_html, format_html_join, conditional_escape
from django.utils.translation import gettext as _
from django.utils.safestring import mark_safe

register = template.Library()    # pylint: disable=invalid-name


class _ListGroupErrorList(ErrorList):
    """
    Custom variant of django.forms.utils.ErrorList which emits errors using Bootstrap 'list groups'.
    """

    def as_ul(self):
        elements = format_html_join('\n', '<li class="list-group-item list-group-item-danger mb-4">{}</li>',
                                    ((e,) for e in self))
        return format_html('<ul class="list-group">\n{}\n</ul>', elements)


def _get_css_classes(field):
    """
    Helper function which returns the appropriate (Bootstrap) CSS classes for rendering an input field and
    its `<div>` container.

    Returns:
        A tuple of the form `(div_classes, field_classes, label_classes)`.
    """

    div_classes = ['mb-3']
    field_classes = []
    label_classes = []

    if field.errors:
        field_classes.append('is-invalid')

    widget = field.field.widget

    if isinstance(widget, CheckboxInput):
        div_classes.append('form-check')
        field_classes.append('form-check-input')
        label_classes.append('form-check-label')
    elif isinstance(widget, (CheckboxSelectMultiple, RadioSelect)):
        # See Git log for inspiration on how this was handled previously
        raise NotImplementedError('Checkbox groups and radio selects are currently not supported')
    elif isinstance(widget, MultiWidget):
        # See Git log for inspiration on how this was handled previously
        raise NotImplementedError('Multi value fields are currently not supported')
    else:
        field_classes.append('form-control')
        label_classes.append('form-label')

    return (div_classes, field_classes, label_classes)


@register.filter
def as_bs_div(form):
    """
    Template filter that renders a form in `div` tags, using Bootstrap CSS classes. This is kind of inspired
    by django.forms.forms.BaseForm._html_output().
    Because it needs to call field methods with arguments, this could not be implemented at the template
    level. In conformance with the regular form rendering methods, it does not respect the current autoescape
    setting and always escapes potentially unsafe strings.
    """

    output = []
    top_errors = _ListGroupErrorList([conditional_escape(e) for e in form.non_field_errors()])

    for field in form.hidden_fields():
        # Display errors for hidden fields in the global error list
        for error in field.errors:
            top_errors.append(format_html(_('Hidden field {name}: {error}'), name=field.name, error=error))
        output.append(str(field))

    for field in form.visible_fields():
        div_classes, field_classes, label_classes = _get_css_classes(field)

        div_class_string = format_html_join(' ', '{}', [(mark_safe(c),) for c in div_classes])
        div_class_string += mark_safe(' ') + conditional_escape(force_str(field.css_classes()))
        field_class_string = format_html_join(' ', '{}', [(mark_safe(c),) for c in field_classes])
        label_class_string = format_html_join(' ', '{}', [(mark_safe(c),) for c in label_classes])

        output.append(format_html('<div class="{}">', div_class_string))
        output.append(force_str(field.label_tag(attrs={'class': label_class_string})))

        rendered_field = force_str(field.as_widget(attrs={'class': field_class_string}))
        output.append(rendered_field)

        for e in field.errors:
            output.append(format_html('<div class="invalid-feedback">{}</div>', e))

        # 'show_hidden_initial' on fields means that they should additionally be rendered hidden for
        # comparisons between the initial and the current value
        if field.field.show_hidden_initial:
            output.append(force_str(field.as_hidden(only_initial=True)))

        help_text = conditional_escape(force_str(field.help_text))

        if not field.field.required:
            help_text = mark_safe('<span class="badge text-bg-secondary">Optional</span> ') + help_text

        if help_text:
            output.append(format_html('<div class="form-text">{}</div>', help_text))

        output.append(mark_safe('</div>'))

    if top_errors:
        output.insert(0, top_errors.as_ul())

    return format_html_join('\n', '{}', ((o,) for o in output))
