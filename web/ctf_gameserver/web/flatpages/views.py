from django.shortcuts import render, get_object_or_404

from .models import Flatpage


def flatpage(request, category=None, slug=''):
    if category is None:
        page = get_object_or_404(Flatpage, category=None, slug=slug)
    else:
        page = get_object_or_404(Flatpage, category__slug=category, slug=slug)

    # Hide sidebar links for pages without category
    if page.category is not None and page.has_siblings():
        sidebar_links = page.siblings
    else:
        sidebar_links = []

    return render(request, 'flatpage.html', {'page': page, 'sidebar_links': sidebar_links})
