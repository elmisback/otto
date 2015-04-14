from django.conf.urls.defaults import *
import views

urlpatterns = patterns(
    '',
    url(r'^$', views.login),
    url(r'^courses/$', views.courses),
    url(r'^courses/(?P<course_id>\d{8})/$', views.course),
    url(r'^courses/(?P<course_id>\d{8})/students/$', views.students),
    url(r'^courses/(?P<course_id>\d{8})/assignments/$', views.assignments),
    url(r'^courses/(?P<course_id>\d{8})/assignments/'
        'add/$', views.edit_assignment),
    url(r'^courses/(?P<course_id>\d{8})/assignments/'
        '(?P<assignment_id>\d{4})/$', views.assignment),
    url(r'^courses/(?P<course_id>\d{8})/assignments/'
        '(?P<assignment_id>\d{4})/edit/$', views.edit_assignment),
    url(r'^login/$', views.login),
    url(r'^register/$', views.register),
    url(r'^download-submission/$', views.download_submission),
)
