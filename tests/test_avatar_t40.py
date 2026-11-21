"""Тесты T40: фото профиля — загрузка, ограничения, защищённая раздача (IDOR)."""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .base import BaseTestCase


def make_image(fmt="JPEG", size=(200, 150), color=(120, 9, 61)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


class AvatarUploadTests(BaseTestCase):
    def test_upload_jpeg_shows_avatar(self):
        client = self.login(self.user_a)
        photo = SimpleUploadedFile("me.jpg", make_image(), content_type="image/jpeg")
        response = client.post(reverse("profile"), {"save_avatar": "1", "photo": photo})
        self.assertRedirects(response, reverse("profile"))
        self.user_a.student_profile.refresh_from_db()
        self.assertTrue(self.user_a.student_profile.photo)
        page = client.get(reverse("profile"))
        self.assertContains(page, 'class="avatar"')
        self.assertNotContains(page, 'class="initials"')

    def test_rejects_oversize_file(self):
        client = self.login(self.user_a)
        photo = SimpleUploadedFile("big.jpg", b"\x00" * (5 * 1024 * 1024 + 1), content_type="image/jpeg")
        response = client.post(reverse("profile"), {"save_avatar": "1", "photo": photo})
        self.user_a.student_profile.refresh_from_db()
        self.assertFalse(self.user_a.student_profile.photo)
        self.assertRedirects(response, reverse("profile"))

    def test_rejects_wrong_format(self):
        client = self.login(self.user_a)
        photo = SimpleUploadedFile("me.gif", make_image(fmt="GIF"), content_type="image/gif")
        client.post(reverse("profile"), {"save_avatar": "1", "photo": photo})
        self.user_a.student_profile.refresh_from_db()
        self.assertFalse(self.user_a.student_profile.photo)

    def test_rejects_too_small_image(self):
        client = self.login(self.user_a)
        photo = SimpleUploadedFile("tiny.png", make_image(fmt="PNG", size=(80, 80)), content_type="image/png")
        client.post(reverse("profile"), {"save_avatar": "1", "photo": photo})
        self.user_a.student_profile.refresh_from_db()
        self.assertFalse(self.user_a.student_profile.photo)

    def test_reupload_replaces_file(self):
        client = self.login(self.user_a)
        first = SimpleUploadedFile("one.jpg", make_image(), content_type="image/jpeg")
        client.post(reverse("profile"), {"save_avatar": "1", "photo": first})
        self.user_a.student_profile.refresh_from_db()
        first_name = self.user_a.student_profile.photo.name
        second = SimpleUploadedFile("two.jpg", make_image(color=(0, 0, 255)), content_type="image/jpeg")
        client.post(reverse("profile"), {"save_avatar": "1", "photo": second})
        self.user_a.student_profile.refresh_from_db()
        self.assertNotEqual(self.user_a.student_profile.photo.name, first_name)


class AvatarAccessTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user_a.student_profile.photo = SimpleUploadedFile("me.jpg", make_image(), content_type="image/jpeg")
        self.user_a.student_profile.save()

    def test_owner_gets_image(self):
        client = self.login(self.user_a)
        response = client.get(reverse("avatar", args=[self.user_a.student_profile.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("image/", response.headers["Content-Type"])

    def test_other_student_gets_404(self):
        # IDOR: чужой аватар не существует для этого пользователя.
        client = self.login(self.user_b)
        response = client.get(reverse("avatar", args=[self.user_a.student_profile.pk]))
        self.assertEqual(response.status_code, 404)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("avatar", args=[self.user_a.student_profile.pk]))
        self.assertEqual(response.status_code, 302)

    def test_missing_photo_is_404(self):
        client = self.login(self.user_b)
        response = client.get(reverse("avatar", args=[self.user_b.student_profile.pk]))
        self.assertEqual(response.status_code, 404)
