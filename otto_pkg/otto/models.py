from google.appengine.ext import ndb


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
    creation_time = ndb.DateTimeProperty()


class Comment(ndb.Model):
    date_posted = ndb.DateTimeProperty(auto_now_add=True)
    message = ndb.StringProperty()
    poster = ndb.UserProperty()
    id_str = ndb.StringProperty()


class Submission(ndb.Model):
    student = ndb.UserProperty()
    file_blob = ndb.BlobKeyProperty()  # uses blobstore for files
    time = ndb.DateTimeProperty()
    flagged = ndb.BooleanProperty()
    comments = ndb.KeyProperty(kind='Comment', repeated=True)


class Assignment(ndb.Model):
    title = ndb.StringProperty()
    id_str = ndb.StringProperty()
    due_date = ndb.DateTimeProperty()
    date_created = ndb.DateTimeProperty(auto_now_add=True)
    description = ndb.StringProperty()
    changes = ndb.StringProperty(repeated=True)
    submissions = ndb.KeyProperty(kind='Submission', repeated=True)
    comments = ndb.KeyProperty(kind='Comment', repeated=True)


class Course(ndb.Model):
    title = ndb.StringProperty()
    id_str = ndb.StringProperty()
    assignments = ndb.KeyProperty(kind='Assignment', repeated=True)
    students_enrolled = ndb.KeyProperty(kind='User', repeated=True)
    students_pending = ndb.KeyProperty(kind='User', repeated=True)
    instructors = ndb.StringProperty(repeated=True)
    notifications = ndb.KeyProperty(kind='Notification', repeated=True)

    @classmethod
    def get_by_id(cls, id):
        return cls.query(cls.id_str == id).get()

    def add_student(self, student):
        self.students_pending.append(student.key)

    def approve_student(self, student):
        if student.key in self.students_pending:
            self.students_pending.remove(student.key)
            self.students_enrolled.append(student.key)

    def approve_all_students(self):
        self.students_enrolled.extend(self.students_pending)
        self.students_pending = []

    def remove_student(self, student):
        if student.key in self.students_pending:
            self.students_pending.remove(student.key)
        if student.key in self.students_enrolled:
            self.students_enrolled.remove(student.key)

    def get_enrollment_status(self, student):
        if student.key in self.students_enrolled:
            return 'Enrolled'
        elif student.key in self.students_pending:
            return 'Pending'
        else:
            return 'Not Enrolled'

    def get_object(self):
        return {
            'course_title': self.title,
            'course_id': self.id_str,
            'course_assignments': len(self.assignments),
            'course_enrolled': len(self.students_enrolled),
            'course_pending': len(self.students_pending),
            'course_instructors': ', '.join(self.instructors),
            'course_url': 'courses/{}'.format(self.id_str)
        }

    def get_object_with_status(self, student):
        obj = self.get_object()
        obj['course_status'] = self.get_enrollment_status(student)
        return obj
