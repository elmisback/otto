import os
import json
import logging

from google.appengine.api import users
from google.appengine.ext import ndb

from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.core.context_processors import csrf

from models import Course, User


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
    if template_dict is None:
        template_dict = {}
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        'templates/' + template_name)
    response = render_to_response(path, template_dict)
    # Prevent post-signout access to data. TODO solve this problem for real
    response['Cache-Control'] = ('no-cache, max-age=0,'
                                 'must-revalidate, no-store')
    return response


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
            u.put()  # store user in database
        return redirect('/index')


def login(request):
    user = users.get_current_user()
    logging.info('Running login()')
    if user:
        logging.info('Found a user with id {}'.format(user.user_id))
        return redirect('/index')
    response = render(
            'login.html',
            {'login_url': users.create_login_url(request.path)}
    )
    return response


def generate_course_id():
    import time
    return str(int(time.time()))


@login_required
def courses(request):
    logging.info('Received request for \'courses\' page...')
    current_user = users.get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    logging.info('Current user is {}.'.format(user))
    if user.is_instructor:
        logging.info('Request is from an instructor.')
        if request.method == 'POST':
            logging.info('There is a POST request.')
            if request.POST['action'] == 'addCourse':
                logging.info('Adding a new course...')
                course_title = request.POST['course_title']
                course_id = generate_course_id()
                course_instructor = [current_user.nickname()]
                course = Course({
                    'title': course_title,
                    'id_str': course_id,
                    'instructors': course_instructor
                })
                course.put()
                logging.info('Responding to client after course add...')
                response = HttpResponse()
                response.status_code = 200
                response.content_type = 'application/json'
                response.content = json.dumps({
                    'course_id': course_id,
                    'course_title': course_title
                })
                return response
            elif request.POST['action'] == 'removeCourse':
                logging.info('Recevied request to delete course...')
                course_id = request.POST['course_id']
                course_key = ndb.Key(Course, course_id, parent=user_key)
                course_key.delete()
                # if course_key is not None:
                #     course_key.delete()
                #     logging.info('Course has been deleted...')
                # response = HttpResponse()
                # response.status_code = 200
                # response.content_type = 'application/json'
                # response.content = 'success'
                # return response
        else:
            pass
    else:
        pass
    logging.info([key.get() for key in user.courses])
    add_dialog_name = 'Course Name' if user.is_instructor else 'Course ID'
    placeholder = ('e.g. Data Structures' if user.is_instructor
                   else 'e.g. 1234567890')
    template_dict = {
            'user_name': current_user.nickname(),
            'logout_url': users.create_logout_url('/login'),
            'add_dialog_name': add_dialog_name,
            'placeholder': placeholder,
            'courses': [key.get() for key in user.courses]
    }
    template_dict.update(csrf(request))
    return render('courses.html', template_dict)


@login_required
def index(request):
    user = users.get_current_user()
    user_key = ndb.Key(User, user.user_id())
    u = user_key.get()
    logging.info('Actually handling index request!')
    logging.info('request.method={}'.format(request.method))
    logging.info("User's courses are: {}".format([k.get() for k in u.courses]))
    logging.info("u.courses={}".format(u.courses))
    if request.method == "POST":
        logging.info("It's a post request")
        if u.is_instructor:
            logging.info("...from an instructor")
            title = request.POST['courseID']
            logging.info('title={}'.format(title))
            k = ndb.Key(Course, title, parent=user_key)
            course = k.get()
            if course is None:
                id_str = generate_course_id()
                course = Course(key=k, title=title, id_str=id_str,
                                instructors=[user.nickname()])
                logging.info('Created course with id_str={}'.format(id_str))
            else:
                # Course already exists; probably this should create an error.
                raise Exception(
                        'Course already exists, handler not implemented.')

        else:
            logging.info("...from a student")
            id_str = request.POST['courseID']
            courses = [c for c in Course.query(Course.id_str == id_str)]
            if len(courses) == 0:
                logging.info('Found no courses matching the id.')
            else:
                course = courses[0]
                logging.info('Found course: {}'.format(course))
                if course is None:
                    raise Exception("Couldn't find the course.")
                if user_key in course.students:
                    raise Exception("You're already in that course.")
                course.students.append(user_key)
            k = course.key

        u.courses.append(k)
        course.put()
        u.put()
        logging.info('Successfully added course!')

    # Basic response.
    logging.info([k.get() for k in u.courses])
    add_dialog_name = 'Course Name' if u.is_instructor else 'Course ID'
    placeholder = ('e.g. Data Structures' if u.is_instructor
                   else 'e.g. 1234567890')
    template_dict = {
            'user_name': user.nickname(),
            'logout_url': users.create_logout_url('/login'),
            'add_dialog_name': add_dialog_name,
            'placeholder': placeholder,
            'courses': [k.get() for k in u.courses]
    }
    template_dict.update(csrf(request))
    return render('courses.html', template_dict)
