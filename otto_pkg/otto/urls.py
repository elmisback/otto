from django.conf.urls.defaults import *
import views

urlpatterns = patterns(
    '',
    url(r'^$', views.login),
    url(r'^courses$', views.courses),
    url(r'^login$', views.login),
    url(r'^register$', views.register),
    url(r'^assignment$', views.assignment),
)
