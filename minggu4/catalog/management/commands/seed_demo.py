from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import Assignment, Course, Enrollment, Lesson, Submission
from users.models import User


class Command(BaseCommand):
    help = "Membuat sample data Lecturer, Student, Course, Lesson, Enrollment, Assignment, dan Submission (idempotent)"

    def get_user(self, username, email, role):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "role": role},
        )
        if created:
            user.set_password("12345")
            user.save()
        return user

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. USER
        lecturer = self.get_user("suprayogi", "suprayogi@gmail.com", User.Role.LECTURER)
        student = self.get_user("fauzan", "fauzan@gmail.com", User.Role.STUDENT)

        # 2. COURSE
        course, _ = Course.objects.get_or_create(
            code="PSS01",
            defaults={
                "title": "Pemrograman Sisi Server",
                "description": "Belajar backend development dengan Django.",
                "lecturer": lecturer,
            },
        )

        # 3. LESSON
        lessons = [
            "Pengenalan Backend",
            "Pola Arsitektur Backend",
            "Containerisasi dengan Docker",
        ]
        for order, title in enumerate(lessons, start=1):
            Lesson.objects.get_or_create(
                course=course, order=order, defaults={"title": title}
            )

        # 4. ENROLLMENT
        Enrollment.objects.get_or_create(student=student, course=course)

        # 5. ASSIGNMENT
        assignment1, _ = Assignment.objects.get_or_create(
            course=course,
            title="Tugas Django ORM",
            defaults={
                "description": "Implementasikan model dan relationship menggunakan Django ORM.",
                "deadline": timezone.now() + timedelta(days=7),
            },
        )
        assignment2, _ = Assignment.objects.get_or_create(
            course=course,
            title="Tugas REST API",
            defaults={
                "description": "Buat REST API sederhana menggunakan Django.",
                "deadline": timezone.now() + timedelta(days=14),
            },
        )

        # 6. SUBMISSION
        Submission.objects.get_or_create(
            assignment=assignment1,
            student=student,
            defaults={
                "content": "Saya telah menyelesaikan implementasi Django ORM.",
                "grade": 87.5,
            },
        )
        Submission.objects.get_or_create(
            assignment=assignment2,
            student=student,
            defaults={
                "content": "Saya telah menyelesaikan REST API menggunakan Django.",
                "grade": 90.0,
            },
        )

        self.stdout.write(self.style.SUCCESS("Sample data berhasil dibuat."))
