from django.conf.urls import include, url
from django.contrib import admin

from .registration import views as registration_views


# pylint: disable=invalid-name
urlpatterns = [
    url(r'^register/$', registration_views.register, name='register'),
    url(r'^confirm/$', registration_views.confirm_email, name='confirm_email'),

    url(r'^admin/', include(admin.site.urls))
]
