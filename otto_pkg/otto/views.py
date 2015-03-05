import os
import json
import logging

from google.appengine.api.users import *
from google.appengine.ext import ndb
from google.appengine.ext import db

from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.core.context_processors import csrf

from models import *

def login_required(fn):
    def wrapper(request):
        logging.info('Running login_required()')
        user = get_current_user()
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
        user = get_current_user()
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
        return redirect('/courses')

def login(request):
    user = get_current_user()
    logging.info('Running login()')
    if user:
        logging.info('Found a user with id {}'.format(user.user_id))
        return redirect('/courses')
    response = render(
        'login.html',
        {'login_url': create_login_url(request.path)}
    )
    return response

@ndb.transactional(xg=True)
def _create_course(title):
    digits = 8
    course = Course(title=title, id=Course.generate_id(digits),
                    instructors=[get_current_user().nickname()])
    course.put()
    return course

def create_course(title):
    """Creates a course named title.
    
    Using a transaction guarantees we will never generate two courses with the 
    same ID. 
    """
    course = None
    while course is None:
        try:
            course = _create_course(title)
        except db.TransactionFailedError:
            pass
    
    return course

@login_required
def courses(request):
    logging.info('Processing request for courses page.')
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    logging.info('Current user is {}.'.format(current_user.nickname()))
    if user.is_instructor:
        template = 'courses_instructor.html'
        if request.method == 'POST':
            logging.info('Processing a POST request from an instructor.')
            if request.POST['action'] == 'addCourse':
                course_title = request.POST['course_title']
                logging.info('POST request to add a course with title {}.'
                             .format(course_title))
                if len(course_title) <= 0:
                    response = HttpResponse()
                    response.content_type = 'application/json'
                    response.content = json.dumps({
                        'success': False,
                        'message': ('The course title must be at least '
                                    'one character.')
                    })
                    return response
                try:
                    course = create_course(course_title)
                except IDTimeout:
                    response = HttpResponse()
                    response.content_type = 'application/json'
                    response.content = json.dumps({
                        'success': False,
                        'message': ("Sorry! We don't have space to add more "
                                    "courses right now. Please try again "
                                    "later.")
                    })
                    return response
                user.add_course(course)
                user.put()
                if request.POST['ajax']:  # AJAX calls only needs new course
                    logging.info('Responding to client with new course.')
                    course_object = course.get_object()
                    course_object['success'] = True
                    response = HttpResponse()
                    response.content_type = 'application/json'
                    response.content = json.dumps(course_object)
                    return response
            elif request.POST['action'] == 'removeCourse':
                course_id = request.POST['course_id']
                logging.info('POST request to remove course with ID {}.'
                             .format(course_id))
                course = Course.get_by_id(course_id)
                # TODO: query all users who have this course added
                # TODO: modify model to have only one relationship
                course.key.delete()
                user.remove_course(course)
                user.put()
                if request.POST['ajax']:  # AJAX call only needs confirmation
                    logging.info('Responding to client with confirmation.')
                    return HttpResponse()
    else:
        template = 'courses_student.html'
        if request.method == 'POST':
            logging.info('Processing a POST request from a student.')
            if request.POST['action'] == 'joinCourse':
                course_id = request.POST['course_id']
                logging.info('Student requests to join course with ID {}.'
                             .format(course_id))
                course = Course.get_by_id(course_id)
                if course is None:
                    response = HttpResponse()
                    response.content_type = 'application/json'
                    response.content = json.dumps({
                        'success': False,
                        'message': ('Unable to find course matching the ID. '
                                    'Please verify the ID and try again.')
                    })
                    return response
                status = course.get_enrollment_status(user)
                if status in ['Enrolled', 'Pending']:
                    response = HttpResponse()
                    response.content_type = 'application/json'
                    response.content = json.dumps({
                        'success': False,
                        'message': ('You are already enrolled in this course.'
                                    if status == 'Enrolled' else
                                    'Your enrollment is pending approval.')
                    })
                    return response
                course.add_student(user)
                course.put()
                user.add_course(course)
                user.put()
                if request.POST['ajax']:
                    logging.info('Responding to client with new course.')
                    response = HttpResponse()
                    response.content_type = 'application/json'
                    course_object = course.get_object_with_status(user)
                    course_object['success'] = True
                    response.content = json.dumps(course_object)
                    return response
            elif request.POST['action'] == 'leaveCourse':
                course_id = request.POST['course_id']
                logging.info('Student requests to leave course with ID {}.'
                             .format(course_id))
                course = Course.get_by_id(course_id)
                course.remove_student(user)
                course.put()
                user.remove_course(course)
                user.put()
                if request.POST['ajax']:  # AJAX call only needs confirmation
                    logging.info('Responding to client with confirmation.')
                    return HttpResponse()
    courses = []
    for course_key in user.courses:
        course = course_key.get()
        if course is not None:
            courses.append(course.get_object_with_status(user))
    data = {
        'user': user,
        'user_name': current_user.nickname(),
        'logout_url': create_logout_url('/login'),
        'courses': courses
    }
    data.update(csrf(request))
    return render(template, data)
