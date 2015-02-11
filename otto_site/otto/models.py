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
