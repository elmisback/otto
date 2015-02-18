from django.conf.urls.defaults import *
from otto.views import index, login

urlpatterns = patterns('',
                (r'^$', index),
                (r'^/index$', index),
                (r'^/login$', login),
                )
