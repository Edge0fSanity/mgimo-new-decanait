"""Тесты ревью п.10/п.12 (T45/T47): полезные ссылки в футере."""
from django.urls import reverse

from apps.dashboard.models import ExternalLink

from .base import BaseTestCase


class UsefulLinksTests(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ExternalLink.objects.create(title="Moodle МГИМО", url="#", sort_order=0)
        ExternalLink.objects.create(title="Кафедра МЭО и ВЭС", url="https://mgimo.ru/study/faculty/meo/kmeovs/", sort_order=1)
        ExternalLink.objects.create(title="Скрытая ссылка", url="https://example.com", sort_order=2, is_active=False)

    def test_footer_shows_stub_as_text_and_real_as_link(self):
        page = self.login(self.user_a).get(reverse("home"))
        self.assertContains(page, "Полезные ссылки:")
        self.assertContains(page, "Moodle МГИМО")
        self.assertNotContains(page, 'href="#">')  # заглушка не кликается в никуда
        self.assertContains(page, 'href="https://mgimo.ru/study/faculty/meo/kmeovs/"')
        self.assertNotContains(page, "Скрытая ссылка")
