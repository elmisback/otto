import json
import logging
import mimetypes
from datetime import datetime, timedelta

from google.appengine.api.users import *
from google.appengine.api import mail
from google.appengine.ext import ndb, blobstore, webapp
from google.appengine.ext.webapp.blobstore_handlers import BlobstoreUploadHandler

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse

from models import *

from bs4 import BeautifulSoup


# A handler for our submission file uploads.
class UploadHandler(BlobstoreUploadHandler):
    def post(self):
        current_user = get_current_user()
        user_key = ndb.Key(User, current_user.user_id())
        try:
            logging.info(self.get_uploads())
            upload = self.get_uploads()[0]
            submission = Submission(
                student=user_key,
                file_blob=upload.key(),
                date_posted=datetime.now() - timedelta(hours=4),  # hacky!
                filename=upload.filename
            )
            submission.put()
            return self.response.out.write(submission.key.id())
        except:
            logging.info('Failed uploading submission.')
            raise
        return self.response.out.write('success!')

upload_handler = webapp.WSGIApplication([('/upload/', UploadHandler)])


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


# Verifies that the student is enrolled in this course.
def is_enrolled(fn):
    def wrapper(request, **kwargs):
        current_user = get_current_user()
        user_key = ndb.Key(User, current_user.user_id())
        user = user_key.get()
        course_id = kwargs['course_id']
        course = Course.get_by_id(course_id)
        courses_url = reverse(courses_view)
        if not user.is_instructor and user_key not in course.students_enrolled:
            logging.info('Student is not enrolled in course.')
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
def notifications_view(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    if request.is_ajax():
        if request.method == 'GET':
            notifications = get_notifications(user)
            response = HttpResponse()
            response.status_code = 200
            response.content_type = 'application/json'
            response.content = json.dumps({
                'notifications': notifications
            })
            return response
        else:
            user.notifications = []
            user.put()
    return HttpResponse()


@is_logged_in
def notifications_clear_view(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    user.notifications = []
    user.put()
    return HttpResponse()


@is_logged_in
@is_valid_course
@is_valid_assignment
def download_view(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    submission_id = kwargs['submission_id']
    submission = Submission.get_by_id(int(submission_id))
    if not user.is_instructor and user_key != submission.student:
        assignment_url = reverse(
            assignment_view, kwargs={
                'course_id': kwargs['course_id'],
                'assignment_id': kwargs['assignment_id']
            }
        )
        return redirect(assignment_url)
    response = HttpResponse(blobstore.BlobReader(submission.file_blob).read())
    content_type, encoding = mimetypes.guess_type(submission.filename)
    response['Content-Type'] = content_type
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(submission.filename)
    return response


@is_logged_in
@is_valid_course
@is_valid_assignment
@is_enrolled
def submit_view(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    course_id = kwargs['course_id']
    course = Course.get_by_id(course_id)
    assignment_id = kwargs['assignment_id']
    assignment = Assignment.get_by_id(assignment_id)
    assignment_url = reverse(
        assignment_view, kwargs={
            'course_id': kwargs['course_id'],
            'assignment_id': kwargs['assignment_id']
        }
    )
    response = HttpResponse()
    response.status_code = 200
    response.content_type = 'application/json'
    if assignment is not None:
        logging.info('Assignment is valid...')
        submission_id = kwargs['submission_id']
        submission = Submission.get_by_id(int(submission_id))
        replaced_submission_key = None
        if submission is not None:
            logging.info('Submission is valid...')
            if assignment.date_due < datetime.now() - timedelta(hours=4):
                blobstore.delete(submission.file_blob)
                response.status_code = 400
                response.content = json.dumps({
                    'message': 'Submissions for this assignment were due at {}. Your submission was not accepted.'.format(get_timestamp(assignment.date_due))
                })
                return response
            # fairly poor performance decision but oh well!
            for submission_key in assignment.submissions:
                if submission_key.get().student == user_key:
                    replaced_submission_key = submission_key.id()
                    replaced_submission = submission_key.get()
                    blobstore.delete(replaced_submission.file_blob)
                    assignment.submissions.remove(submission_key)
                    assignment.put()
                    submission_key.delete()
            assignment.submissions.append(submission.key)
            assignment.put()
            notification = Notification(
                message='{} uploaded a new submission for {}.'.format(user.nickname, assignment.title),
                target_url=assignment_url,
                timestamp=datetime.now() - timedelta(hours=4)
            )
            notification.put()
            instructor = course.instructor.get()
            if instructor is not None:
                instructor.notifications.insert(0, notification.key)
                instructor.put()
            submission.assignment = assignment.key
            submission.put()
        else:
            response.status_code = 400
            response.content = json.dumps({
                'message': 'There was an error in creating a submission for your upload. Please try again.'
            })
            return response
        response.content = json.dumps({
            'upload_url': blobstore.create_upload_url('/upload/'),
            'replaced_submission': replaced_submission_key,
            'submission': get_submission(course, assignment, submission)
        })
    return response


@is_logged_in
@is_valid_course
def assignment_edit_view(request, **kwargs):
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
    assignment_edit_url = reverse(
        assignment_edit_view, kwargs=kwargs
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
        'assignment_edit_url': assignment_edit_url,
        'breadcrumb': [
            ('Courses', courses_url),
            (course.title, assignments_url),
            ('Assignments', assignments_url)
        ],
        'notifications': get_notifications(user),
    }
    assignment_id = kwargs['assignment_id']
    assignment = Assignment.get_by_id(assignment_id)
    allowed_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'p', 'ul', 'ol', 'li', 'br', 'a', 'img']
    if request.method == 'POST':
        if 'remove' in request.POST:
            logging.info('Removing assignment!')
            course.assignments.remove(assignment.key)
            course.put()
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
                'You must enter a valid datetime (e.g. April 13, 2015 12:10PM).'))
        assignment_description = request.POST['assignment_description']
        if response.status_code == 400:
            logging.info('Returning a JSON response with input errors.')
            response.content = json.dumps({
                'failed_inputs': failed_inputs
            })
            return response
        soup = BeautifulSoup(assignment_description)
        for tag in soup.findAll(True):
            if tag.name not in allowed_tags:
                tag.hidden = True
        if assignment is None:
            logging.info('Creating a new assignment object from valid data.')
            assignment = Assignment(
                id=assignment_id,
                title=assignment_title,
                date_posted=datetime.now() - timedelta(hours=4), # hacky :)
                date_due=assignment_due_date,
                description=soup.renderContents()
            )
            logging.info('New assignment ID is {}.'.format(assignment.key))
            course.assignments.append(assignment.key)
            course.put()
            logging.info(course.assignments)
            assignment.put()
            notification = Notification(
                message='{} in {} has been posted.'.format(assignment.title, course.title),
                target_url=assignment_url,
                timestamp=datetime.now() - timedelta(hours=4)
            )
            notification.put()
            for student_key in course.students_enrolled:
                student = student_key.get()
                student.notifications.insert(0, notification.key)
                student.put()
            return redirect(assignment_url)
        else:
            logging.info('Assignment exists. Updating fields with data.')
            assignment.title = assignment_title
            assignment.date_due = assignment_due_date
            assignment.description = soup.renderContents()
            assignment.put()
            notification = Notification(
                message='{} in {} has been updated.'.format(assignment.title, course.title),
                target_url=assignment_url,
                timestamp=datetime.now() - timedelta(hours=4)
            )
            notification.put()
            for student_key in course.students_enrolled:
                student = student_key.get()
                student.notifications.insert(0, notification.key)
                student.put()
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
@is_enrolled
def assignment_view(request, **kwargs):
    current_user = get_current_user()
    user_key = ndb.Key(User, current_user.user_id())
    user = user_key.get()
    course_id = kwargs['course_id']
    course = Course.get_by_id(course_id)
    assignment_id = kwargs['assignment_id']
    assignment = Assignment.get_by_id(assignment_id)
    courses_url = reverse(courses_view)
    assignments_url = reverse(
        assignments_view, kwargs={
            'course_id': course_id
        }
    )
    assignment_edit_url = reverse(
        assignment_edit_view, kwargs=kwargs
    )
    assignment_url = reverse(
        assignment_view, kwargs=kwargs
    )
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
        'notifications': get_notifications(user),
        'upload_url': blobstore.create_upload_url('/upload/'),
        'submit_url': '{}submit/'.format(assignment_url),
        'assignment_url': assignment_url,
        'assignment_edit_url': assignment_edit_url,
        'assignment': get_assignment(assignment, course),
        'submissions': get_submissions(course, assignment, user),
        'comments': get_comments(assignment, user),
        'has_submission': user_key in [x.get().student for x in assignment.submissions],
        'can_submit': assignment.date_due > datetime.now() - timedelta(hours=4)
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
            comment = Comment(
                message=comment_message,
                poster=user_key,
                date_posted=datetime.now() - timedelta(hours=4)
            )
            comment.put()
            assignment.comments.append(comment.key)
            logging.info(assignment.comments)
            assignment.put()
            notification = Notification(
                message='{} posted a comment on {} in {}.'.format(user.nickname, assignment.title, course.title),
                target_url=assignment_url,
                timestamp=datetime.now() - timedelta(hours=4)
            )
            notification.put()
            for student_key in course.students_enrolled:
                if student_key != user_key:
                    student = student_key.get()
                    student.notifications.insert(0, notification.key)
                    student.put()
            instructor = course.instructor.get()
            if instructor is not None:
                if instructor.key != user_key:
                    instructor.notifications.insert(0, notification.key)
                    instructor.put()
            response.content = json.dumps(get_comment(comment, user))
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
        assignment_edit_view, kwargs={
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
        'notifications': get_notifications(user),
        'add_assignment_url': add_assignment_url,
        'assignments': get_assignments(course, user),
        'enrolled': not user.is_instructor and user_key in course.students_enrolled
    }
    if request.is_ajax():
        return render(request, 'view.html', context)
    return render(request, 'base.html', context)


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
        'notifications': get_notifications(user),
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
                    assignments_url = reverse(
                        assignments_view, kwargs={
                            'course_id': course_id
                        }
                    )
                    notification = Notification(
                        message='You have been approved for {}.'.format(course.title),
                        target_url=assignments_url,
                        timestamp=datetime.now() - timedelta(hours=4)
                    )
                    notification.put()
                    student.notifications.insert(0, notification.key)
                    student.put()
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
        'notifications': get_notifications(user),
        'courses_url': courses_url,
        'courses': get_courses(user)
    }
    if request.is_ajax():
        if request.method == 'POST':
            logging.info('Processing an AJAX POST request.')
            response = HttpResponse()
            response.status_code = 200
            response.content_type = 'application/json'
            if user.is_instructor:
                course_title = request.POST['course_title']
                if not course_title or not len(course_title) > 0:
                    logging.info('Course title not passed.')
                    response.status_code = 400
                    response.content = json.dumps({
                        'failed_inputs': [
                            ('course_title', 'You must enter a title for this course.')
                        ]
                    })
                    return response
                logging.info('Creating a new course titled {}.'
                             .format(course_title))
                try:
                    course = Course.create_course(course_title)
                except IDTimeout:
                    response.status_code = 500
                    response.content = json.dumps({
                        'message': 'Unable to add course. Please try again.'
                    })
                    return response
                user.add_course(course)
                user.put()
                response.content = json.dumps({
                    'course': get_course(course, user)
                })
                return response
            else:
                course_id = request.POST['course_id']
                if not course_id or not len(course_id) > 0:
                    logging.info('Course ID not passed.')
                    response.status_code = 400
                    response.content = json.dumps({
                        'failed_inputs': [
                            ('course_id', 'You must enter an ID to join a course.')
                        ]
                    })
                    return response
                course = Course.get_by_id(course_id)
                if course is None:
                    logging.info('Failed to find course with ID {}.'
                                 .format(course_id))
                    response.status_code = 400
                    response.content = json.dumps({
                        'failed_inputs': [
                            ('course_id', '{} is not a valid course ID.'.format(course_id))
                        ]
                    })
                    return response
                logging.info('Joining course with ID {}.'.format(course_id))
                if course.key in user.courses:
                    logging.info('Student already in course.')
                    response.status_code = 400
                    response.content = json.dumps({
                        'failed_inputs': [
                            ('course_id', 'You are already enrolled in or pending approval for this course.')
                        ]
                    })
                    return response
                user.add_course(course)
                user.put()
                course.add_student(user)
                course.put()
                students_url = reverse(
                    students_view, kwargs={
                        'course_id': course_id
                    }
                )
                notification = Notification(
                    message='{} is requesting permission to join {}.'.format(user.nickname, course.title),
                    target_url=students_url,
                    timestamp=datetime.now() - timedelta(hours=4)
                )
                notification.put()
                instructor = course.instructor.get()
                if instructor is not None:
                    instructor.notifications.insert(0, notification.key)
                    instructor.put()
                response.content = json.dumps({
                    'course': get_course(course, user)
                })
                return response
        else:
            return render(request, 'view.html', context)
    else:
        return render(request, 'base.html', context)


# Returns a list of parsed notification attributes for a specified notification.
def get_notifications(user):
    notifications = []
    for notification_key in user.notifications:
        notification = notification_key.get()
        if notification is not None:
            notification_obj = get_notification(notification)
            if notification_obj is not None:
                notifications.insert(0, notification_obj)
        else:
            pass
            # notification_key.delete()
    return notifications


# Returns a parsed notification attribute object for a specified notification.
def get_notification(notification):
    notification_obj = {}
    if notification is not None:
        notification_obj = {
            'message': notification.message,
            'target_url': notification.target_url,
            'timestamp': get_timestamp(notification.timestamp)
        }
    return notification_obj


# Returns a list of parsed submission attributes for a specified assignment.
def get_submissions(course, assignment, user):
    submissions = []
    for submission_key in assignment.submissions:
        submission = submission_key.get()
        if submission is not None:
            if user.is_instructor or user.key == submission.student:
                submission_obj = get_submission(course, assignment, submission)
                if submission_obj is not None:
                    submissions.append(submission_obj)
        else:
            assignment.submissions.remove(submission_key)
            assignment.put()
    return submissions


# Returns a parsed comment attribute object for a specified comment.
def get_submission(course, assignment, submission):
    submission_obj = {}
    if submission is not None:
        download_url = reverse(
            download_view, kwargs={
                'course_id': course.key.id(),
                'assignment_id': assignment.key.id(),
                'submission_id': submission.key.id()
            }
        )
        submission_obj = {
            'id': submission.key.id(),
            'author': submission.student.get().nickname,
            'filename': submission.filename,
            'download_url': download_url,
            'timestamp': get_timestamp(submission.date_posted)
        }
    return submission_obj


# Returns a list of parsed comment attributes for a specified assignment.
def get_comments(assignment, user):
    comments = []
    for comment_key in assignment.comments:
        comment = comment_key.get()
        if comment is not None:
            comment_obj = get_comment(comment, user)
            if comment_obj is not None:
                comments.append(comment_obj)
        else:
            assignment.comments.remove(comment_key)
            assignment.put()
    return comments


# Returns a parsed comment attribute object for a specified comment.
def get_comment(comment, user):
    comment_obj = {}
    if comment is not None:
        comment_obj = {
            'id': comment.key.id(),
            'author': comment.poster.get().nickname,
            'can_edit': user.key.id() == comment.poster.id() or user.is_instructor,
            'is_instructor': comment.poster.get().is_instructor,
            'message': comment.message,
            'timestamp': get_timestamp(comment.date_posted)
        }
    return comment_obj


# Returns a list of parsed student attributes for a specified course.
def get_students(course):
    students = []
    for student_key in course.students_pending + course.students_enrolled:
        student = student_key.get()
        if student is not None:
            student_obj = get_student(student, course)
            if student_obj is not None:
                students.append(student_obj)
        else:
            course.students_enrolled.remove(student_key)
            course.students_pending.remove(student_key)
            course.put()
    return students


# Returns a parsed student attribute object for a specified student.
def get_student(student, course):
    student_obj = {}
    if student is not None:
        student_obj = {
            'id': student.key.id(),
            'name': student.nickname,
            'status': course.is_enrolled(student)
        }
    return student_obj


# Returns a list of parsed assignment attributes for a specified course.
def get_assignments(course, user):
    assignments = []
    for assignment_key in course.assignments:
        assignment = assignment_key.get()
        if assignment is not None:
            assignment_obj = get_assignment(assignment, course)
            if assignment_obj is not None:
                assignments.append(assignment_obj)
        else:
            course.assignments.remove(assignment_key)
            course.put()
    return assignments


# Returns a parsed assignment attribute object for a specified assignment.
def get_assignment(assignment, course):
    assignment_obj = None
    if assignment is not None and course is not None:
        assignment_url = reverse(
            assignment_view, kwargs={
                'course_id': course.key.id(),
                'assignment_id': assignment.key.id()
            }
        )
        assignment_edit_url = reverse(
            assignment_edit_view, kwargs={
                'course_id': course.key.id(),
                'assignment_id': assignment.key.id()
            }
        )
        assignment_obj = {
            'id': assignment.key.id(),
            'title': assignment.title,
            'date_posted': get_timestamp(assignment.date_posted),
            'date_due': get_timestamp(assignment.date_due),
            'description': assignment.description,
            'url': assignment_url,
            'edit_url': assignment_edit_url,
            'past_deadline': assignment.date_due < datetime.now() - timedelta(hours=4)
        }
    return assignment_obj


# Returns a list of parsed course attributes for a specified user.
def get_courses(user):
    courses = []
    for course_key in user.courses:
        course = course_key.get()
        if course is not None:
            course_obj = get_course(course, user)
            if course_obj is not None:
                courses.append(course_obj)
        else:
            user.courses.remove(course_key)
            user.put()
    return courses


# Returns a parsed course attribute object for a specified course & user.
def get_course(course, user):
    course_obj = None
    if course is not None and user is not None:
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
        course_obj = {
            'id': course.key.id(),
            'title': course.title,
            'assignment_count': len(course.assignments),
            'student_count': len(course.students_enrolled + course.students_pending),
            'has_pending_students': len(course.students_pending) > 0,
            'is_enrolled': user.key in course.students_enrolled or user.is_instructor,
            'assignments_url': assignments_url,
            'students_url': students_url,
            'course_url': course_url
        }
    return course_obj


# Returns the globally-standard readable version of the timestamp.
def get_timestamp(timestamp):
    return timestamp.strftime('%B %d, %Y %I:%M%p')
