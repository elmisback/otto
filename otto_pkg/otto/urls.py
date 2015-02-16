from django.conf.urls.defaults import *
from otto.views import index

urlpatterns = patterns('',
                (r'^$', index),
                )
