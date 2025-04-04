from django import template

register = template.Library()

@register.filter
def bootstrap_tag(tag):
    return {
        'error': 'danger'
    }.get(tag, tag)