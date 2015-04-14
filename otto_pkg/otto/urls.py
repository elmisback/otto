from django.conf.urls.defaults import *
import views

urlpatterns = patterns(
    '',
    url(r'^$', views.login_view),
    url(r'^courses/$', views.courses_view),
    url(r'^courses/(?P<course_id>\d{8})/$', views.course_view),
    url(r'^courses/(?P<course_id>\d{8})/students/$', views.students_view),
    url(r'^courses/(?P<course_id>\d{8})/assignments/$',
        views.assignments_view),
    url(r'^courses/(?P<course_id>\d{8})/assignments/'
        '(?P<assignment_id>\d{4})/$', views.assignment_view),
    url(r'^courses/(?P<course_id>\d{8})/assignments/'
        '(?P<assignment_id>\d{4})/edit/$', views.edit_assignment_view),
    url(r'^login/$', views.login_view),
    url(r'^register/$', views.register_view),
)
