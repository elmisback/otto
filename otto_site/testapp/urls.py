from django.conf.urls.defaults import *
from testapp.views import index

urlpatterns = patterns('',
                (r'^$', index),
                )
