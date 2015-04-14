import json
import logging
from datetime import datetime, timedelta

from google.appengine.api.users import *
from google.appengine.api import mail
from google.appengine.ext import ndb

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse

from models import *

from bs4 import BeautifulSoup


# Verifies that the user logged in before proceeding to view.
def is_logged_in(fn):
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


# Verifies that we are attempting to access subviews of a valid course.
def is_valid_course(fn):
    def wrapper(request, **kwargs):
        course_id = kwargs['course_id']
        course = Course.get_by_id(course_id)
        courses_url = reverse(courses_view)
        if course is None:
            logging.info('Invalid course ID was passed. Redirecting to '
                         'courses view.')
            return redirect(courses_url)
        return fn(request, **kwargs)
    return wrapper


# Verifies that we are attempting to access subviews of a valid course.
def is_valid_assignment(fn):
    def wrapper(request, **kwargs):
        assignment_id = kwargs['assignment_id']
        assignment = Assignment.get_by_id(assignment_id)
        courses_url = reverse(courses_view)
        if assignment is None:
            logging.info('Invalid assignment ID was passed. Redirecting to '
                         'courses view.')
            return redirect(courses_url)
        return fn(request, **kwargs)
    return wrapper


# Registers a first time user either as an instructor or a student.
def register_view(request):
    if request.method == 'POST':
        if 'instructor' in request.POST:
            logging.info('Registering a new instructor.')
            is_instructor = True
        else:
            logging.info('Registering a new student.')
            is_instructor = False
        current_user = get_current_user()
        user_id = current_user.user_id()
        user = User.get_by_id(user_id)
        if user is None:
            user = User(id=user_id, is_instructor=is_instructor,
                        nickname=current_user.nickname())
            user.put()
        return redirect(reverse(courses_view))


# Displays a login form to authenticate the user.
def login_view(request):
    current_user = get_current_user()
    if not current_user:
        logging.info('User is not logged in.')
        return render(request, 'login.html', {
            'login_url': create_login_url(request.path)
        })
    logging.info('User is logged in as {}'.format(current_user.nickname()))
    return redirect(reverse(courses_view))


@is_logged_in
@is_valid_course
def edit_assignment_view(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    course_id = kwargs['course_id']
    course = Course.get_by_id(course_id)
    courses_url = reverse(courses_view)
    assignments_url = reverse(
        assignments_view, kwargs={
            'course_id': course_id
        }
    )
    edit_assignment_url = reverse(
        edit_assignment_view, kwargs=kwargs
    )
    assignment_url = reverse(
        assignment_view, kwargs=kwargs
    )
    context = {
        'user': user,
        'user_name': current_user.nickname(),
        'logout_url': create_logout_url('/login'),
        'view_template': 'edit_assignment.html',
        'assignments_url': assignments_url,
        'edit_assignment_url': edit_assignment_url,
        'breadcrumb': [
            ('Courses', courses_url),
            (course.title, assignments_url),
            ('Assignments', assignments_url)
        ]
    }
    assignment_id = kwargs['assignment_id']
    assignment = Assignment.get_by_id(assignment_id)
    if request.method == 'POST':
        if 'remove' in request.POST:
            logging.info('Removing assignment!')
            course.assignments.remove(assignment.key)
            assignment.key.delete()
            return redirect(assignments_url)
        logging.info('Processing POST request on edit assignment page.')
        assignment_title = request.POST['assignment_title']
        response = HttpResponse()
        response.status_code = 200
        response.content_type = 'application/json'
        failed_inputs = []
        if not assignment_title:
            logging.info('No assignment title passed!')
            response.status_code = 400
            failed_inputs.append(('assignment_title',
                'You must enter a title for the assignment.'))
        try:
            assignment_due_date = datetime.strptime(
                request.POST['assignment_due_date'], '%B %d, %Y %I:%M%p')
        except ValueError:
            logging.info('No valid due date passed!')
            response.status_code = 400
            failed_inputs.append(('assignment_due_date',
                'You must enter a valid datetime (e.g. 4/13/2015 12:10PM).'))
        assignment_description = request.POST['assignment_description']
        if response.status_code == 400:
            logging.info('Returning a JSON response with input errors.')
            response.content = json.dumps({
                'failed_inputs': failed_inputs
            })
            return response
        if assignment is None:
            logging.info('Creating a new assignment object from valid data.')
            assignment = Assignment(
                id=assignment_id,
                title=assignment_title,
                date_posted=datetime.now() - timedelta(hours=4), # hacky :)
                date_due=assignment_due_date,
                description=assignment_description
            )
            logging.info('New assignment ID is {}.'.format(assignment.key))
            course.assignments.append(assignment.key)
            course.put()
            logging.info(course.assignments)
            assignment.put()
            return redirect(assignment_url)
        else:
            logging.info('Assignment exists. Updating fields with data.')
            assignment.title = assignment_title
            assignment.date_due = assignment_due_date
            assignment.description = assignment_description
            assignment.put()
            return redirect(assignment_url)
    else:
        logging.info('Processing a GET request on edit assignment page.')
        assignment_id = kwargs['assignment_id']
        assignment = Assignment.get_by_id(assignment_id)
        if assignment is None:
            logging.info('Assignment does not exist.')
            context['breadcrumb'].append(('Add New Assignment', ''))
            context['page_title'] = 'Add New Assignment'
        else:
            logging.info('Assignment exists. Returning instance.')
            assignment_url = reverse(
                assignment_view, kwargs={
                    'course_id': course_id,
                    'assignment_id': assignment_id
                }
            )
            context['breadcrumb'].append((assignment.title, assignment_url))
            context['breadcrumb'].append(('Edit', ''))
            context['page_title'] = 'Edit Assignment'
            context['assignment'] = assignment
            context['assignment_due_date'] = assignment.date_due.strftime('%B %d, %Y %I:%M%p')
    if request.is_ajax():
        return render(request, 'view.html', context)
    return render(request, 'base.html', context)


@is_logged_in
@is_valid_course
@is_valid_assignment
def assignment_view(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    course_id = kwargs['course_id']
    course = Course.get_by_id(course_id)
    courses_url = reverse(courses_view)
    assignments_url = reverse(
        assignments_view, kwargs={
            'course_id': course_id
        }
    )
    edit_assignment_url = reverse(
        edit_assignment_view, kwargs=kwargs
    )
    assignment_url = reverse(
        assignment_view, kwargs=kwargs
    )
    assignment_id = kwargs['assignment_id']
    assignment = Assignment.get_by_id(assignment_id)
    soup = BeautifulSoup(assignment.description)
    allowed_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'p', 'ul', 'ol', 'li', 'br', 'a', 'img']
    for tag in soup.findAll(True):
        if tag.name not in allowed_tags:
            tag.hidden = True
    context = {
        'user': user,
        'user_name': current_user.nickname(),
        'logout_url': create_logout_url('/login'),
        'view_template': 'assignment.html',
        'breadcrumb': [
            ('Courses', courses_url),
            (course.title, assignments_url),
            ('Assignments', assignments_url),
            (assignment.title, '')
        ],
        'edit_assignment_url': edit_assignment_url,
        'assignment_url': assignment_url,
        'submissions_url': '',  # change this to dynamic value
        'submissions_count': len(assignment.submissions),
        'assignment_id': assignment.key.id(),
        'assignment_title': assignment.title,
        'assignment_date_posted': assignment.date_posted.strftime(
            '%B %d, %Y %I:%M%p'),
        'assignment_date_due': assignment.date_due.strftime(
            '%B %d, %Y %I:%M%p'),
        'assignment_description': soup.renderContents(),
        'assignment_has_submission': False,  # change this to dynamic value
        'past_deadline': assignment.date_due < datetime.now() - timedelta(hours=4),
        'comments': get_comments(assignment)
    }
    if request.method == 'POST':
        if 'submit_comment' in request.POST:
            logging.info('Trying to submit a comment...')
            comment_message = request.POST['comment_message']
            response = HttpResponse()
            response.status_code = 200
            failed_inputs = []
            if not comment_message:
                logging.info('No comment message passed!')
                response.status_code = 400
                failed_inputs.append(('comment_message', 'You must enter a comment message.'))
            if response.status_code == 400:
                response.content = json.dumps({
                    'failed_inputs': failed_inputs
                })
                return response
            comment = Comment(message=comment_message, poster=user_key)
            comment.put()
            assignment.comments.append(comment.key)
            logging.info(assignment.comments)
            assignment.put()
            response.content = json.dumps(get_comment(comment))
            logging.info('Returning the comment object.')
            return response
        elif 'delete_comment' in request.POST:
            logging.info('Deleting a comment...')
            comment_id = request.POST['comment_id']
            comment = Comment.get_by_id(int(comment_id))
            if comment is not None:
                logging.info('Comment found!')
                assignment.comments.remove(comment.key)
                comment.key.delete()
                assignment.put()
            response = HttpResponse()
            response.status_code = 204
            return response
    if request.is_ajax():
        return render(request, 'view.html', context)
    return render(request, 'base.html', context)


def get_submissions(assignment):
    return


def get_comments(assignment):
    if assignment is not None:
        comments = []
        for comment_key in assignment.comments:
            comment = comment_key.get()
            if comment is not None:
                comments.append(get_comment(comment))
        return comments


def get_comment(comment):
    return {
        'id': comment.key.id(),
        'author': comment.poster.get().nickname,
        'is_instructor': comment.poster.get().is_instructor,
        'message': comment.message,
        'timestamp': comment.date_posted.strftime('%B %d, %Y %I:%M%p')
    }


@is_logged_in
@is_valid_course
def assignments_view(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    course_id = kwargs['course_id']
    course = Course.get_by_id(course_id)
    courses_url = reverse(courses_view)
    assignments_url = reverse(
        assignments_view, kwargs={
            'course_id': course_id
        }
    )
    add_assignment_url = reverse(
        edit_assignment_view, kwargs={
            'course_id': course_id,
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
        'assignments': get_assignments(course, user)
    }
    context['enrolled'] = (not user.is_instructor and
                           user_key in course.students_enrolled)
    if request.is_ajax():
        return render(request, 'view.html', context)
    return render(request, 'base.html', context)


def get_assignments(course, user):
    assignments = []
    for assignment_key in course.assignments:
        assignment = assignment_key.get()
        if assignment is not None:
            assignment_url = reverse(
                assignment_view, kwargs={
                    'course_id': course.key.id(),
                    'assignment_id': assignment.key.id()
                }
            )
            edit_assignment_url = reverse(
                edit_assignment_view, kwargs={
                    'course_id': course.key.id(),
                    'assignment_id': assignment.key.id()
                }
            )

            assignments.append({
                'id': assignment.key.id(),
                'title': assignment.title,
                'date_posted': assignment.date_posted.strftime(
                    '%B %d, %Y %I:%M%p'),
                'date_due': assignment.date_due.strftime(
                    '%B %d, %Y %I:%M%p'),
                'has_submission': False,  # change to dynamic value
                'assignment_url': assignment_url,
                'edit_url': edit_assignment_url
            })
    return assignments


@is_logged_in
def students_view(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    course_id = kwargs['course_id']
    course = Course.get_by_id(course_id)
    courses_url = reverse(courses_view)
    assignments_url = reverse(
        assignments_view, kwargs={
            'course_id': course.key.id()
        }
    )
    students_url = reverse(
        students_view, kwargs={
            'course_id': course.key.id()
        }
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
                    # logging.info('Sending email to {} of students approval'
                    #               .format(current_user.email()))
                    # mail.send_mail(sender="Otto team <bapratt94@gmail.com>",
                    #                to=current_user.email(),
                    #                subject="Student approved for {}".format(course.title),
                    #                body="Student {} has been approved.".format(student_id)
                    #                )
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
            'name': student.nickname,
            'status': course.is_enrolled(student)
        })
    return students


@is_logged_in
@is_valid_course
def course_view(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    course_id = kwargs['course_id']
    course = Course.get_by_id(course_id)
    courses_url = reverse(courses_view)
    assignments_url = reverse(
        assignments_view, kwargs={
            'course_id': course.key.id()
        }
    )
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


@is_logged_in
def courses_view(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    courses_url = reverse(courses_view)
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


def get_course(course, user):
    assignments_url = reverse(
        assignments_view, kwargs={
            'course_id': course.key.id()
        }
    )
    students_url = reverse(
        students_view, kwargs={
            'course_id': course.key.id()
        }
    )
    course_url = reverse(
        course_view, kwargs={
            'course_id': course.key.id()
        }
    )
    return {
        'id': course.key.id(),
        'title': course.title,
        'enrolled': len(course.students_enrolled),
        'pending': len(course.students_pending),
        'assignments': len(course.assignments),
        'instructors': ', '.join(course.instructors),
        'status': course.is_enrolled(user),
        'assignments_url': assignments_url,
        'students_url': students_url,
        'course_url': course_url
    }
