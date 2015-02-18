from django.conf.urls.defaults import *
from otto.views import index, login, register

urlpatterns = patterns('',
                url(r'^$', login),
                url(r'^index$', index),
                url(r'^login$', login),
                url(r'^register$', register),
                )
