from django.conf.urls.defaults import *
import views

urlpatterns = patterns(
    '',
    url(r'^$', views.login_view),
    url(r'^notifications/$', views.notifications_view),
    url(r'^notifications/clear/$', views.notifications_clear_view),
    url(r'^courses/$', views.courses_view),
    url(r'^courses/(?P<course_id>\d{8})/$', views.course_view),
    url(r'^courses/(?P<course_id>\d{8})/students/$', views.students_view),
    url(r'^courses/(?P<course_id>\d{8})/assignments/$', views.assignments_view),
    url(r'^courses/(?P<course_id>\d{8})/assignments/(?P<assignment_id>\d{4})/$', views.assignment_view),
    url(r'^courses/(?P<course_id>\d{8})/assignments/(?P<assignment_id>\d{4})/submit/(?P<submission_id>\d{16})/$', views.submit_view),
    url(r'^courses/(?P<course_id>\d{8})/assignments/(?P<assignment_id>\d{4})/download/(?P<submission_id>\d{16})/$', views.download_view),
    url(r'^courses/(?P<course_id>\d{8})/assignments/'
        '(?P<assignment_id>\d{4})/edit/$', views.assignment_edit_view),
    url(r'^login/$', views.login_view),
    url(r'^register/$', views.register_view),
)
