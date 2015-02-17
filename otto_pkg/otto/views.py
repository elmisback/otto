from django.http import HttpResponse

from google.appengine.ext.webapp import template
from google.appengine.api import users
import logging
import os

def render_template(template_name, template_values):
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                        'templates/' + template_name)
    html = template.render(path, template_values)
    return HttpResponse(html)

def index(request):
    user = users.get_current_user()
    if user:
        #greeting = ('Welcome, %s! (<a href="%s">sign out</a>)' %
        #           (user.nickname(), ))
        logging.info(user.user_id())
        return render_template('courses.html', {'logout_url':users.create_logout_url('/')})
    else:
        greeting = ('<a href="%s">Sign in or register</a>.' %
                    users.create_login_url('/'))

    return HttpResponse('<html><body>%s</body></html>' % greeting)

#def login(request):
#
#import webapp2
#
#class MyHandler(webapp2.RequestHandler):
#    def get(self):
#        user = users.get_current_user()
#        if user:
#            greeting = ('Welcome, %s! (<a href="%s">sign out</a>)' %
#                        (user.nickname(), users.create_logout_url('/')))
#        else:
#            greeting = ('<a href="%s">Sign in or register</a>.' %
#                        users.create_login_url('/'))
#
#        self.response.out.write('<html><body>%s</body></html>' % greeting)
