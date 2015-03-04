from django.conf.urls.defaults import *
import views

urlpatterns = patterns(
    '',
    url(r'^$', views.login),
    url(r'^courses$', views.courses),
    url(r'^courses/(?P<course_id>\d{10})$', views.course),
    url(r'^login$', views.login),
    url(r'^register$', views.register),
)
