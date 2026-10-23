from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_role_default_is_student(self):
        user = User.objects.create_user(username="budi", password="pass12345")
        self.assertEqual(user.role, User.Role.STUDENT)

    def test_role_choices(self):
        self.assertEqual(
            set(User.Role.values),
            {"ADMIN", "LECTURER", "STUDENT"},
        )

    def test_create_user(self):
        user = User.objects.create_user(
            username="dosen",
            password="pass12345",
            role=User.Role.LECTURER,
        )
        self.assertEqual(user.role, User.Role.LECTURER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("pass12345"))

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            username="root",
            password="pass12345",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_str(self):
        user = User.objects.create_user(
            username="suprayogi",
            password="pass12345",
            role=User.Role.LECTURER,
        )
        self.assertEqual(str(user), "suprayogi (LECTURER)")
