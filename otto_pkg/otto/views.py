import json
import logging

from google.appengine.api.users import *
from google.appengine.ext import ndb

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse

from models import *


# Verifies that the user logged in before proceeding to view.
def login_required(fn):
    def wrapper(request, **kwargs):
        logging.info('Verifying if user is logged in.')
        current_user = get_current_user()
        if not current_user:
            logging.info('User is not logged in.')
            return login(request)
        logging.info('User is logged in. Checking for previous history.')
        user_key = ndb.Key(User, current_user.user_id())
        user = user_key.get()
        if user is None:
            logging.info('User has not logged in before. Registering...')
            return render(request, 'register.html')
        return fn(request, **kwargs)
    return wrapper


# Registers a first time user either as an instructor or a student.
def register(request):
    if request.method == 'POST':
        current_user = get_current_user()
        logging.info('Registering a new user as instructor or student.')
        if 'instructor' in request.POST:
            is_instructor = True
            logging.info('Registering a new instructor.')
        else:
            is_instructor = False
            logging.info('Registering a new student.')
        user_key = ndb.Key(User, current_user.user_id())
        user = user_key.get()
        if user is None:
            user = User(key=user_key, is_instructor=is_instructor)
            user.put()
        return redirect(reverse(courses))


# Displays a login form to authenticate the user.
def login(request):
    current_user = get_current_user()
    logging.info('Verifying if user is logged in.')
    if not current_user:
        logging.info('User is not logged in.')
        return render(request, 'login.html', {
            'login_url': create_login_url(request.path)
        })
    logging.info('User is logged in as {}'.format(current_user.nickname()))
    return redirect(reverse(courses))


@login_required
def edit_assignment(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    course_id = kwargs['course_id']
    course = Course.get_by_id(course_id)
    courses_url = reverse(courses)
    assignments_url = reverse(
        assignments, kwargs={'course_id': course.key.id()}
    )
    context = {
        'user': user,
        'user_name': current_user.nickname(),
        'logout_url': create_logout_url('/login'),
        'view_template': 'edit_assignment.html',
        'breadcrumb': [
            ('Courses', courses_url),
            (course.title, assignments_url),
            ('Assignments', assignments_url),
            ('Add New Assignment', '')
        ]
    }
    if request.is_ajax():
        return render(request, 'view.html', context)
    return render(request, 'base.html', context)


@login_required
def assignment(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    return HttpResponse()


@login_required
def assignments(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    course_id = kwargs['course_id']
    course = Course.get_by_id(course_id)
    courses_url = reverse(courses)
    if course is None:
        logging.info('Invalid course ID. Redirecting to /courses/.')
        return redirect(courses_url)
    if not user.is_instructor and user_key not in course.students_enrolled:
        logging.info('User is not enrolled. Redirecting to /courses/.')
        return redirect(courses_url)
    assignments_url = reverse(
        assignments, kwargs={'course_id': course.key.id()}
    )
    add_assignment_url = reverse(
        edit_assignment, kwargs={
            'course_id': course.key.id(),
            'assignment_id': Assignment.generate_id(4)
        }
    )
    context = {
        'user': user,
        'user_name': current_user.nickname(),
        'logout_url': create_logout_url('/login'),
        'view_template': 'assignments.html',
        'breadcrumb': [
            ('Courses', courses_url),
            (course.title, assignments_url),
            ('Assignments', assignments_url)
        ],
        'add_assignment_url': add_assignment_url,
        'assignments': get_assignments(course)
    }
    if request.is_ajax():
        return render(request, 'view.html', context)
    return render(request, 'base.html', context)


def get_assignments(course):
    assignments = []
    for assignment_key in course.assignments:
        assignment = assignment_key.get()
        if assignment is not None:
            edit_assignment_url = reverse(
                edit_assignment, kwargs={
                    'course_id': course.key.id(),
                    'assignment_id': assignment.key.id()
                }
            )
            assignments.append({
                'title': assignment.title,
                'id': assignment.key.id(),
                'date_posted': assignment.date_posted.strftime(
                    '%d/%m/%Y %I:%M%p'),
                'date_due': assignment.date_due.strftime('%d/%m/%Y %I:%M%p'),
                'submissions': len(assignment.submissions),
                'status': False,  # change to dynamic value
                'edit_assignment_url': edit_assignment_url
            })
    return assignments


@login_required
def students(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    course_id = kwargs['course_id']
    course = Course.get_by_id(course_id)
    courses_url = reverse(courses)
    assignments_url = reverse(
        assignments, kwargs={'course_id': course.key.id()}
    )
    students_url = reverse(
        students, kwargs={'course_id': course.key.id()}
    )
    context = {
        'user': user,
        'user_name': current_user.nickname(),
        'logout_url': create_logout_url('/login'),
        'view_template': 'students.html',
        'breadcrumb': [
            ('Courses', courses_url),
            (course.title, assignments_url),
            ('Students', students_url)
        ],
        'students_url': students_url
    }
    if course is None:
        logging.info('Invalid course ID. Redirecting to /courses/.')
        return redirect(courses_url)
    if not user.is_instructor:
        logging.info('Student trying to access /students/ page.')
        return redirect(courses_url)
    if request.is_ajax():
        if request.method == 'POST':
            action_type = request.POST['action_type']
            logging.info('Processing an action type of {}.'
                         .format(action_type))
            if action_type != 'approve_all':
                student_id = request.POST['student_id']
                student = User.get_by_id(student_id)
                if action_type == 'approve':
                    course.approve_student(student)
                else:
                    course.unapprove_student(student)
            else:
                course.approve_all_students()
            course.put()
            response = HttpResponse()
            response.status_code = 204
            return response
        context['students'] = get_students(course)
        return render(request, 'view.html', context)
    context['students'] = get_students(course)
    return render(request, 'base.html', context)


def get_students(course):
    students = []
    for student_key in course.students_pending + course.students_enrolled:
        student = student_key.get()
        students.append({
            'id': student.key.id(),
            'name': student.key.id(),  # needs replaced with nickname
            'status': course.is_enrolled(student)
        })
    return students


@login_required
def course(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    course_id = kwargs['course_id']
    course = Course.get_by_id(course_id)
    courses_url = reverse(courses)
    assignments_url = reverse(
        assignments, kwargs={'course_id': course.key.id()}
    )
    if course is None:
        logging.info('Invalid course ID. Redirecting to /courses/.')
        return redirect(courses_url)
    if request.is_ajax():
        if request.method == 'POST':
            logging.info('User is removing course ID {}.'.format(course_id))
            user.remove_course(course)
            user.put()
            if user.is_instructor:
                course.key.delete()
            else:
                course.remove_student(user)
                course.put()
            request.method = 'GET'
            return redirect(courses_url)
        else:
            return redirect(assignments_url)
    else:
        return redirect(assignments_url)


@login_required
def courses(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    courses_url = reverse(courses)
    context = {
        'user': user,
        'user_name': current_user.nickname(),
        'logout_url': create_logout_url('/login'),
        'view_template': 'courses.html',
        'breadcrumb': [
            ('Courses', courses_url)
        ],
        'courses': get_courses(user)
    }
    if request.is_ajax():
        if request.method == 'POST':
            logging.info('Processing an AJAX POST request.')
            if user.is_instructor:
                if ('course_title' not in request.POST or
                        len(request.POST['course_title']) <= 0):
                    logging.info('Course title is not in POST request.')
                    response = HttpResponse()
                    response.status_code = 400
                    response.content_type = 'application/json'
                    response.content = json.dumps({
                        'message': 'You must enter a title for this course.'
                    })
                    return response
                course_title = request.POST['course_title']
                logging.info('Creating a new course titled {}.'
                             .format(course_title))
                try:
                    course = Course.create_course(course_title)
                except IDTimeout:
                    response = HttpResponse()
                    response.status_code = 500
                    response.content_type = 'application/json'
                    response.content = json.dumps({
                        'message': 'Failed to add course. Please try again.'
                    })
                    return response
                user.add_course(course)
                user.put()
                response = HttpResponse()
                response.status_code = 200
                response.content_type = 'application/json'
                response.content = json.dumps(get_course(course, user))
                return response
            else:
                if ('course_id' not in request.POST or
                        len(request.POST['course_id']) <= 0):
                    logging.info('Course ID is empty or not in POST request.')
                    response = HttpResponse()
                    response.status_code = 400
                    response.content_type = 'application/json'
                    response.content = json.dumps({
                        'message': 'You must enter an ID to join a course.'
                    })
                    return response
                course_id = request.POST['course_id']
                course = Course.get_by_id(course_id)
                if not course:
                    logging.info('Failed to find course with ID {}.'
                                 .format(course_id))
                    response = HttpResponse()
                    response.status_code = 400
                    response.content_type = 'application/json'
                    response.content = json.dumps({
                        'message': ('{} is not a valid course ID.'
                                    .format(course_id))
                    })
                    return response
                logging.info('Joining course with ID {}.'.format(course_id))
                if course.key in user.courses:
                    logging.info('Student already in course.')
                    response = HttpResponse()
                    response.status_code = 400
                    response.content_type = 'application/json'
                    response.content = json.dumps({
                        'message': ('You are already enrolled in or pending '
                                    'approval for this course.')
                    })
                    return response
                user.add_course(course)
                user.put()
                course.add_student(user)
                course.put()
                response = HttpResponse()
                response.status_code = 200
                response.content_type = 'application/json'
                response.content = json.dumps(get_course(course, user))
                return response
        else:
            return render(request, 'view.html', context)
    else:
        return render(request, 'base.html', context)


def get_courses(user):
    courses = []
    for course_key in user.courses:
        course = course_key.get()
        if course is not None:
            courses.append(get_course(course, user))
    return courses


def get_course(this, user):
    assignments_url = reverse(
        assignments, kwargs={'course_id': this.key.id()}
    )
    students_url = reverse(
        students, kwargs={'course_id': this.key.id()}
    )
    course_url = reverse(
        course, kwargs={'course_id': this.key.id()}
    )
    return {
        'title': this.title,
        'id': this.key.id(),
        'enrolled': len(this.students_enrolled),
        'pending': len(this.students_pending),
        'assignments': len(this.assignments),
        'instructors': ', '.join(this.instructors),
        'status': this.is_enrolled(user),
        'assignments_url': assignments_url,
        'students_url': students_url,
        'course_url': course_url
    }
