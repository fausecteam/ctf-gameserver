from django.shortcuts import render, get_object_or_404

from .models import Flatpage


def flatpage(request, path):
    path_parts = path.rstrip('/').split('/')
    page = None

    for part in path_parts:
        parent = page
        page = get_object_or_404(Flatpage, parent=parent, slug=part)

    return render(request, 'flatpage.html', {'page': page})
