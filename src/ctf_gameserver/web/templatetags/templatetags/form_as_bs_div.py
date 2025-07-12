from django import template
from django.forms import CheckboxInput, CheckboxSelectMultiple, RadioSelect, FileInput, MultiWidget
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
        elements = format_html_join('\n', '<li class="list-group-item list-group-item-danger">{}</li>',
                                    ((e,) for e in self))
        return format_html('<ul class="list-group">\n{}\n</ul>', elements)


def _get_css_classes(field):
    """
    Helper function which returns the appropriate (Bootstrap) CSS classes for rendering an input field and
    its `<div>` container.

    Returns:
        A tuple of the form `(div_classes, field_classes, iterate_subfields, wrap_in_label)`.
        `iterate_subfields` is a bool indicating that the field should be rendered by iterating over its
        sub-fields (i.e. over itself) and wrapping them in containers with `field_classes`. This is required
        for multiple radios and checkboxes belonging together.
        `wrap_in_label` is a bool that specifies whether the input field should be placed inside the
        associated `<label>`, as required by Bootstrap for checkboxes.
    """

    div_classes = []
    field_classes = []
    iterate_subfields = False
    wrap_in_label = False

    if field.errors:
        div_classes.append('has-error')

    widget = field.field.widget

    if isinstance(widget, CheckboxInput):
        div_classes.append('checkbox')
        wrap_in_label = True
    elif isinstance(widget, CheckboxSelectMultiple):
        div_classes.append('form-group')
        field_classes.append('checkbox')
        iterate_subfields = True
    elif isinstance(widget, RadioSelect):
        div_classes.append('form-group')
        field_classes.append('radio')
        iterate_subfields = True
    elif isinstance(widget, FileInput):
        pass
    elif isinstance(widget, MultiWidget):
        div_classes.append('form-group')
        div_classes.append('form-inline')
        field_classes.append('form-control')
    else:
        div_classes.append('form-group')
        field_classes.append('form-control')

    return (div_classes, field_classes, iterate_subfields, wrap_in_label)


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
        div_classes, field_classes, iterate_subfields, wrap_in_label = _get_css_classes(field)

        div_class_string = format_html_join(' ', '{}', [(mark_safe(c),) for c in div_classes])
        div_class_string += mark_safe(' ') + conditional_escape(force_str(field.css_classes()))
        field_class_string = format_html_join(' ', '{}', [(mark_safe(c),) for c in field_classes])

        output.append(format_html('<div class="{}">', div_class_string))

        if not wrap_in_label:
            output.append(force_str(field.label_tag()))

        if field.errors:
            output.append(str(_ListGroupErrorList([conditional_escape(e) for e in field.errors])))

        # The default rendering for RadioSelect and CheckboxSelectMultiple wraps the options in a list, but
        # Bootstrap requires `<div>`s
        if iterate_subfields:
            rendered_parts = []

            for subfield in field:
                rendered_parts.append(format_html('<div class="{}">', field_class_string))
                rendered_parts.append(force_str(subfield))
                rendered_parts.append(mark_safe('</div>'))

            rendered_field = format_html_join('\n', '{}', ((p,) for p in rendered_parts))
        else:
            rendered_field = force_str(field.as_widget(attrs={'class': field_class_string}))

        # Bootstrap requires to actial `<input>` element to be inside the associated `<label>` for
        # checkboxes
        if wrap_in_label:
            label_content = rendered_field + mark_safe(' ') + conditional_escape(force_str(field.label))
            output.append(force_str(field.label_tag(label_content, label_suffix='')))
        else:
            output.append(rendered_field)

        # 'show_hidden_initial' on fields means that they should additionally be rendered hidden for
        # comparisons between the initial and the current value
        if field.field.show_hidden_initial:
            output.append(force_str(field.as_hidden(only_initial=True)))

        help_text = conditional_escape(force_str(field.help_text))

        if not field.field.required:
            help_text = mark_safe('<span class="label label-default">Optional</span> ') + help_text

        if help_text:
            output.append(format_html('<span class="help-block">{}</span>', help_text))

        output.append(mark_safe('</div>'))

    if top_errors:
        output.insert(0, force_str(top_errors))

    return format_html_join('\n', '{}', ((o,) for o in output))
