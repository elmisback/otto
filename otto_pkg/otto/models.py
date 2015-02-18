#from django.db import models
from google.appengine.ext import ndb

# key: user.user_id
class User(ndb.Model):
    is_instructor = ndb.BooleanProperty()
    courses = ndb.KeyProperty(kind="Course", repeated=True)

#   if needed later  
#class Student(User):
#class Instructor(User):


class Notification(ndb.Model):
    message = ndb.StringProperty(indexed=False)
    target_url = ndb.StringProperty(indexed=False)
    unread = ndb.BooleanProperty()
    creation_time = ndb.DateTimeProperty()

##in case we want this
class Comment(ndb.Model):
    date_posted = ndb.DateTimeProperty(auto_now_add=True)
    message = ndb.StringProperty()
    poster = ndb.UserProperty()
    id_str = ndb.StringProperty()

class Submission(ndb.Model):
    student = ndb.UserProperty()
    file_blob = ndb.BlobKeyProperty() # uses blobstore for files
    time = ndb.DateTimeProperty()
    flagged = ndb.BooleanProperty()
    comments = ndb.KeyProperty(kind=Comment, repeated=True)

class Assignment(ndb.Model):
    title = ndb.StringProperty()
    id_str = ndb.StringProperty()
    due_date = ndb.DateTimeProperty()
    date_created = ndb.DateTimeProperty(auto_now_add=True)
    description = ndb.StringProperty()
    changes = ndb.StringProperty(repeated=True)  ##probably want a list of changes
    submissions = ndb.KeyProperty(kind=Submission, repeated=True)
    comments = ndb.KeyProperty(kind=Comment, repeated=True)

class Course(ndb.Model):
    title = ndb.StringProperty()
    id_str = ndb.StringProperty()
    assignments = ndb.KeyProperty(kind=Assignment, repeated=True)
    students = ndb.KeyProperty(kind='User', repeated=True)
    instructors = ndb.StringProperty(repeated=True)
    notifications = ndb.KeyProperty(kind=Notification, repeated=True)
