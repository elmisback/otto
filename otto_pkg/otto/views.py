from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect

from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import ndb
import logging
import os
from models import Course, User

from django.core.context_processors import csrf
from django.shortcuts import render_to_response

def login_required(fn):
    def wrapper(request):
        logging.info('Running login_required()')
        user = users.get_current_user()
        if not user:
            logging.info('User not found.')
            return login(request)
        logging.info('User is logged in... checking for registration.')
        key = ndb.Key(User, user.user_id())
        u = key.get()
        if u is None:
            return render('register.html', csrf(request))
        logging.info(fn.func_name)
        logging.info(request.method)
        return fn(request)
    return wrapper 

def render(template_name, template_dict=None):
    if template_dict == None:
        template_dict = {}
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                        'templates/' + template_name)
    #html = template.render(path, template_dict)
    response = render_to_response(path, template_dict)
    # Prevent post-signout access to data. TODO solve this problem for real
    response['Cache-Control'] = 'no-cache, max-age=0, must-revalidate, no-store'
    return response
    #return render_to_response(path, template_dict)

# Views

def register(request):
    if request.method == "POST":
        user = users.get_current_user()
        logging.info("Registering user!")
        # Handle user creation and redirect to the index.
        if 'instructor' in request.POST:
            is_instructor = True
            logging.info('Adding new instructor!')
        elif 'student' in request.POST:
            is_instructor = False
            logging.info('Adding new student!')
        key = ndb.Key(User, user.user_id())
        u = key.get()
        if u is None:
            u = User(key=key, is_instructor=is_instructor, courses=[]) 
            u.put() # store user in database
        return redirect('/index')

def login(request):
    user = users.get_current_user()
    logging.info('Running login()')
    if user:
        logging.info('Found a user with id {}'.format(user.user_id))
        return redirect('/index')
    response = render('login.html', 
                  {'login_url': users.create_login_url(request.path)})
    return response

# TODO hack
def get_new_course_id():
    return str(int(time.time()))

@login_required
def index(request):
    user = users.get_current_user()
    user_key = ndb.Key(User, user.user_id())
    u = user_key.get()
    logging.info('Actually handling index request!')
    logging.info('request.method={}'.format(request.method))
    logging.info("User's courses are: {}".format([k.get() for k in u.courses]))
    logging.info("u.courses={}".format(u.courses))
    #return render('login.html', {'login_url': users.create_login_url('index/')})
    #logging.info('User is {}'.format(request.user))
    #if not user:
    #    return render('login.html')
    if request.method == "POST": # Handle updates to data model.
                                 # Maybe move to a "controller" function?
        logging.info("It's a post request")
        if u.is_instructor:
            logging.info("...from an instructor")
            title = request.POST['courseID']
            logging.info('title={}'.format(title))
            k = ndb.Key(Course, title, parent=user_key)
            course = k.get()
            if course is None:
                course = Course(key=k, title=title, url_str=k.urlsafe(),
                                instructors=[user.nickname()])
                logging.info('Created course with url_str={}'.format(k.urlsafe()))
            else:
                # Course already exists; probably this should create an error.
                raise Exception(
                        'Course already exists, handler not implemented.')

        else:
            logging.info("...from a student")
            url_str = request.POST['courseID']
            k = ndb.Key(urlsafe=url_str) 
            course = k.get()
            if course is None:
                raise Exception("Couldn't find the course.")
            course.students.append(user_key)
            for k_old in u.courses:
                if k.url_str == k_old.url_str:
                    # Course already exists; probably this should create an error.
                    raise Exception('User error: course already exists, '
                                    'handler not implemented.')

        u.courses.append(k)
        course.put()
        u.put()
        logging.info('Successfully added course!')

    # Basic response.
    logging.info([k.get() for k in u.courses])
    add_dialog_name = 'Course Name' if u.is_instructor else 'Course ID'
    placeholder = ('e.g. CS1520: Web Apps' if u.is_instructor 
                    else 'e.g. agVoZWxsb3IPCxIHQWNjb3VudBiZiwIM')
    template_dict = {'user_name': user.nickname(),
                    'logout_url': users.create_logout_url('/login'),
                    'add_dialog_name': add_dialog_name,
                    'placeholder': placeholder,
                    'courses': [k.get() for k in u.courses],
                    }
    template_dict.update(csrf(request))
    return render('courses.html', template_dict)
