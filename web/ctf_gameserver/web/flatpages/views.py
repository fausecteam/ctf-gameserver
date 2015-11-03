from django.shortcuts import render, get_object_or_404

from .models import Flatpage


def flatpage(request, category, slug):
    if category is None:
        slug_string = slug if slug is not None else ''
        page = get_object_or_404(Flatpage, category=None, slug=slug_string)
    else:
        page = get_object_or_404(Flatpage, category__slug=category, slug=slug)

    return render(request, 'flatpage.html', {'page': page})
