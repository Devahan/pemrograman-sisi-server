from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from .models import Assignment, Course, Enrollment, Lesson, Submission

User = get_user_model()


class CatalogBaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lecturer = User.objects.create_user(
            username="dosen", password="pass12345", role=User.Role.LECTURER
        )
        cls.student = User.objects.create_user(
            username="mhs", password="pass12345", role=User.Role.STUDENT
        )
        cls.course = Course.objects.create(
            code="PSS01",
            title="Pemrograman Sisi Server",
            lecturer=cls.lecturer,
        )


class CourseTests(CatalogBaseTest):
    def test_str(self):
        self.assertEqual(str(self.course), "PSS01 - Pemrograman Sisi Server")

    def test_default_is_active(self):
        self.assertTrue(self.course.is_active)

    def test_code_is_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Course.objects.create(
                    code="PSS01", title="Duplikat", lecturer=self.lecturer
                )

    def test_ordering_by_code(self):
        Course.objects.create(code="AAA01", title="A", lecturer=self.lecturer)
        codes = list(Course.objects.values_list("code", flat=True))
        self.assertEqual(codes, ["AAA01", "PSS01"])

    def test_lecturer_is_protected_on_delete(self):
        with self.assertRaises(ProtectedError):
            self.lecturer.delete()

    def test_courses_taught_related_name(self):
        self.assertIn(self.course, self.lecturer.courses_taught.all())


class LessonTests(CatalogBaseTest):
    def test_unique_order_per_course(self):
        Lesson.objects.create(course=self.course, title="L1", content="c", order=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Lesson.objects.create(
                    course=self.course, title="L2", content="c", order=1
                )

    def test_same_order_allowed_in_different_course(self):
        other = Course.objects.create(
            code="PSS02", title="Other", lecturer=self.lecturer
        )
        Lesson.objects.create(course=self.course, title="L1", content="c", order=1)
        Lesson.objects.create(course=other, title="L1", content="c", order=1)
        self.assertEqual(Lesson.objects.count(), 2)

    def test_ordering_by_order(self):
        Lesson.objects.create(course=self.course, title="Kedua", content="c", order=2)
        Lesson.objects.create(course=self.course, title="Pertama", content="c", order=1)
        titles = list(self.course.lessons.values_list("title", flat=True))
        self.assertEqual(titles, ["Pertama", "Kedua"])

    def test_str(self):
        lesson = Lesson.objects.create(
            course=self.course, title="Pengenalan Backend", content="c", order=1
        )
        self.assertEqual(str(lesson), "PSS01 - Pengenalan Backend")

    def test_cascade_delete_when_course_deleted(self):
        Lesson.objects.create(course=self.course, title="L1", content="c", order=1)
        self.course.delete()
        self.assertEqual(Lesson.objects.count(), 0)


class EnrollmentTests(CatalogBaseTest):
    def test_unique_student_course(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Enrollment.objects.create(student=self.student, course=self.course)

    def test_related_names(self):
        enrollment = Enrollment.objects.create(
            student=self.student, course=self.course
        )
        self.assertIn(enrollment, self.student.enrollments.all())
        self.assertIn(enrollment, self.course.enrollments.all())

    def test_str(self):
        enrollment = Enrollment.objects.create(
            student=self.student, course=self.course
        )
        self.assertEqual(str(enrollment), "mhs -> PSS01")

    def test_cascade_delete_when_course_deleted(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        self.course.delete()
        self.assertEqual(Enrollment.objects.count(), 0)


class AssignmentSubmissionTests(CatalogBaseTest):
    def _make_assignment(self):
        return Assignment.objects.create(
            course=self.course,
            title="Tugas Django ORM",
            deadline=timezone.now() + timedelta(days=7),
        )

    def test_assignment_str_and_related_name(self):
        assignment = self._make_assignment()
        self.assertEqual(str(assignment), "PSS01 - Tugas Django ORM")
        self.assertIn(assignment, self.course.assignments.all())

    def test_submission_defaults(self):
        assignment = self._make_assignment()
        submission = Submission.objects.create(
            assignment=assignment, student=self.student, content="isi"
        )
        self.assertIsNotNone(submission.submitted_at)
        self.assertIsNone(submission.grade)

    def test_submission_grade_decimal(self):
        assignment = self._make_assignment()
        submission = Submission.objects.create(
            assignment=assignment, student=self.student, grade=Decimal("87.50")
        )
        submission.refresh_from_db()
        self.assertEqual(submission.grade, Decimal("87.50"))

    def test_submission_str_and_traversal(self):
        assignment = self._make_assignment()
        submission = Submission.objects.create(
            assignment=assignment, student=self.student
        )
        self.assertEqual(str(submission), "mhs -> Tugas Django ORM")
        self.assertIn(submission, assignment.submissions.all())
        self.assertIn(submission, self.student.submissions.all())

    def test_cascade_from_course_to_submission(self):
        assignment = self._make_assignment()
        Submission.objects.create(assignment=assignment, student=self.student)
        self.course.delete()
        self.assertEqual(Assignment.objects.count(), 0)
        self.assertEqual(Submission.objects.count(), 0)


class QueryOptimizationTests(CatalogBaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for i in range(1, 4):
            Course.objects.create(
                code=f"PSS0{i + 1}", title=f"Course {i}", lecturer=cls.lecturer
            )
            Lesson.objects.create(
                course=cls.course, title=f"Lesson {i}", content="c", order=i
            )

    def test_select_related_uses_single_query(self):
        with self.assertNumQueries(1):
            courses = Course.objects.select_related("lecturer")
            for course in courses:
                course.lecturer.username

    def test_without_select_related_uses_extra_queries(self):
        n = Course.objects.count()
        with self.assertNumQueries(1 + n):
            for course in Course.objects.all():
                course.lecturer.username

    def test_prefetch_related_uses_two_queries(self):
        with self.assertNumQueries(2):
            for course in Course.objects.prefetch_related("lessons"):
                list(course.lessons.all())


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="admin", password="pass12345"
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_admin_pages_return_200(self):
        urls = [
            "/admin/",
            "/admin/catalog/course/",
            "/admin/catalog/lesson/",
            "/admin/catalog/enrollment/",
            "/admin/catalog/assignment/",
            "/admin/catalog/submission/",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_requires_login(self):
        self.client.logout()
        response = self.client.get("/admin/catalog/course/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
