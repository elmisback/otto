import logging

from google.appengine.ext import ndb, db
from google.appengine.api.users import *

from django.core.urlresolvers import reverse

from views import *


class User(ndb.Model):
    is_instructor = ndb.BooleanProperty()
    courses = ndb.KeyProperty(kind='Course', repeated=True)

    def add_course(self, course):
        self.courses.append(course.key)

    def remove_course(self, course):
        if course.key in self.courses:
            self.courses.remove(course.key)


class Notification(ndb.Model):
    message = ndb.StringProperty(indexed=False)
    target_url = ndb.StringProperty(indexed=False)
    unread = ndb.BooleanProperty()
    creation_time = ndb.DateTimeProperty(auto_now_add=True)


class Comment(ndb.Model):
    date_posted = ndb.DateTimeProperty(auto_now_add=True)
    message = ndb.StringProperty()
    poster = ndb.KeyProperty(kind='User')
    id_str = ndb.StringProperty()
    parent_comment = ndb.KeyProperty(kind='Comment')


class Submission(ndb.Model):
    student = ndb.UserProperty()
    file_blob = ndb.BlobKeyProperty()  # uses blobstore for files
    title = ndb.StringProperty()
    time = ndb.DateTimeProperty(auto_now_add=True)
    flagged = ndb.BooleanProperty()
    comments = ndb.KeyProperty(kind='Comment', repeated=True)
    graded = ndb.BooleanProperty()

    @classmethod
    @ndb.transactional(xg=True)
    def _create_submission(cls, title, student, file_blob):
        digits = 11
        submission = cls(title=title, student=student, file_blob=file_blob,
                         id=cls.generate_id(digits))
        submission.put()
        return submission

    @classmethod
    def create_submission(cls, title, student, file_blob):
        submission = None
        while submission is None:
            try:
                submission = cls._create_submission(title, student, file_blob)
            except db.TransactionFailedError:
                break
        return submission

    @classmethod
    def generate_id(cls, digits):
        import time
        from random import randint
        id_gen = lambda: ''.join([str(randint(0, 9)) for i in xrange(digits)])
        submission_id = id_gen()
        submission = cls.get_by_id(submission_id)
        t0 = time.time()
        timeout = 2  # seconds
        while submission:
            if time.time() > t0 + timeout:
                logging.error('Failed to generate a unique ID in time.'
                              'The ID space may be too saturated.')
                raise IDTimeout
            submission_id = id_gen()
            submission = cls.get_by_id(submission_id)
        return submission_id


class Assignment(ndb.Model):
    title = ndb.StringProperty()
    date_due = ndb.DateTimeProperty()
    date_posted = ndb.DateTimeProperty(auto_now_add=True)
    description = ndb.StringProperty()
    changes = ndb.StringProperty(repeated=True)
    submissions = ndb.KeyProperty(kind='Submission', repeated=True)
    comments = ndb.KeyProperty(kind='Comment', repeated=True)

    @classmethod
    @ndb.transactional(xg=True)
    def _create_assignment(cls, assignment_title):
        digits = 4
        assignment = cls(title=assignment_title, id=cls.generate_id(digits))
        assignment.put()
        return assignment

    @classmethod
    def create_assignment(cls, assignment_title):
        assignment = None
        while assignment is None:
            try:
                assignment = cls._create_assignment(assignment_title)
            except db.TransactionFailedError:
                break
        return assignment

    @classmethod
    def generate_id(cls, digits):
        import time
        from random import randint
        id_gen = lambda: ''.join([str(randint(0, 9)) for i in xrange(digits)])
        assignment_id = id_gen()
        assignment = cls.get_by_id(assignment_id)
        t0 = time.time()
        timeout = 2  # seconds
        while assignment:
            if time.time() > t0 + timeout:
                logging.error('Failed to generate a unique ID in time.'
                              'The ID space may be too saturated.')
                raise IDTimeout
            assignment_id = id_gen()
            assignment = cls.get_by_id(assignment_id)
        return assignment_id


class Course(ndb.Model):
    title = ndb.StringProperty()
    assignments = ndb.KeyProperty(kind='Assignment', repeated=True)
    students_enrolled = ndb.KeyProperty(kind='User', repeated=True)
    students_pending = ndb.KeyProperty(kind='User', repeated=True)
    instructors = ndb.StringProperty(repeated=True)
    notifications = ndb.KeyProperty(kind='Notification', repeated=True)

    @classmethod
    @ndb.transactional(xg=True)
    def _create_course(cls, course_title):
        digits = 8
        course = cls(title=course_title, id=cls.generate_id(digits),
                     instructors=[get_current_user().nickname()])
        course.put()
        return course

    @classmethod
    def create_course(cls, course_title):
        course = None
        while course is None:
            try:
                course = cls._create_course(course_title)
            except db.TransactionFailedError:
                break
        return course

    @classmethod
    def generate_id(cls, digits):
        import time
        from random import randint
        id_gen = lambda: ''.join([str(randint(0, 9)) for i in xrange(digits)])
        course_id = id_gen()
        course = cls.get_by_id(course_id)
        t0 = time.time()
        timeout = 2  # seconds
        while course:
            if time.time() > t0 + timeout:
                logging.error('Failed to generate a unique ID in time.'
                              'The ID space may be too saturated.')
                raise IDTimeout
            course_id = id_gen()
            course = cls.get_by_id(course_id)
        return course_id

    def add_student(self, student):
        self.students_pending.append(student.key)

    def approve_student(self, student):
        if student.key in self.students_pending:
            self.students_pending.remove(student.key)
            self.students_enrolled.append(student.key)

    def unapprove_student(self, student):
        if student.key in self.students_enrolled:
            self.students_enrolled.remove(student.key)
            self.students_pending.append(student.key)

    def approve_all_students(self):
        self.students_enrolled.extend(self.students_pending)
        self.students_pending = []

    def remove_student(self, student):
        if student.key in self.students_pending:
            self.students_pending.remove(student.key)
        if student.key in self.students_enrolled:
            self.students_enrolled.remove(student.key)

    def is_enrolled(self, student):
        return student.key in self.students_enrolled


class IDTimeout(Exception):
    pass
