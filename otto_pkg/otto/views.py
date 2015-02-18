from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect

from google.appengine.ext.webapp import template
from google.appengine.api import users
import logging
import os
from models import Course

def login_required(fn):
    def wrapper(request):
        logging.info('Running login_required()')
        user = users.get_current_user()
        if not user:
            logging.info('User not found.')
            return login(request)
        return fn(request)
    return wrapper 

def render(template_name, template_dict):
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                        'templates/' + template_name)
    html = template.render(path, template_dict)
    response = HttpResponse(html)
    # Prevent post-signout access to data. TODO solve this problem for real
    response['Cache-Control'] = 'no-cache, max-age=0, must-revalidate, no-store'
    return response
    #return render_to_response(path, template_dict)

def login(request):
    user = users.get_current_user()
    logging.info('Running login()')
    #if user:
    #    logging.info('Found a user with id {}'.format(user.userid))
    #    return redirect('/index')
    next_page = '/register' if request.path == '/login' else request.path
    response = render('login.html', 
                  {'login_url': users.create_login_url(next_page)})
    return response

@login_required
def index(request):
    user = users.get_current_user()
    #return render('login.html', {'login_url': users.create_login_url('/index')})
    #logging.info('User is {}'.format(request.user))
    #if not user:
    #    return render('login.html')
    if request.method == "GET":
        logging.info(user.user_id())
        return render('courses.html', 
                        {'user_name': user.nickname(),
                         'logout_url': users.create_logout_url('/login')})
    elif request.method == "POST":
        Course = request.POST['identifier']

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
