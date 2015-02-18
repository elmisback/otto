#from django.db import models
from google.appengine.ext import ndb

# Create your models here.

class Notification(ndb.Model):
    message = ndb.StringProperty(indexed=False)
    target_url = ndb.StringProperty(indexed=False)
    unread = ndb.BooleanProperty()
    creation_time = ndb.DateTimeProperty()

class Submission(models.Model):
    student = ndb.UserProperty()
    file_blob = ndb.BlobKeyProperty() # uses blobstore for files
    time = ndb.DateTimeProperty()
    flagged = ndb.BooleanProperty()
    comments = ndb.KeyProperty(kind=Comment, repeated=True)

class Assignment(ndb.model):
    title = ndb.StringProperty()
    id_str = ndb.StringProperty()
    due_date = ndb.DateTimeProperty()
    date_created = ndb.DateTimeProperty(auto_now_add=True)
    description = ndb.StringProperty()
    changes = ndb.StringProperty(repeated=true)  ##probably want a list of changes
    submissions = ndb.StructuredProperty(Submissions, repeated=True)
    comments = ndb.StructuredProperty(Comment, repeated=True)  ##are we creating comment objects?

class Course(ndb.model):
    title = ndb.StringProperty()
    id_str = ndb.StringProperty()
    assignments = ndb.StructuredProperty(Assignment, repeated=True)
    users = ndb.UserProperty(repeated=True)

##in case we want this
class Comment(ndb.model):
    date_posted = ndb.DateTimeProperty(auto_now_add=True)
    message = ndb.StringProperty()
    poster = ndb.UserProperty()
    id_str = ndb.StringProperty()