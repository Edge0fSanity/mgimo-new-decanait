"""Тесты UX-прохода T1–T4: переходы недель, «отметить все», CTA заявления, архив объявлений."""
from django.urls import reverse

from apps.academics.models import Group
from apps.communications.models import Announcement, Notification

from .base import BaseTestCase


class ScheduleWeekNavTests(BaseTestCase):
    def test_week_view_has_prev_next_links(self):
        client = self.login(self.user_a)
        page = client.get("/schedule/?view=week&week_of=2026-12-28")
        self.assertContains(page, "week_of=2026-12-21")
        self.assertContains(page, "week_of=2027-01-04")

        # В режиме «Сегодня» переходов по неделям нет.
        self.assertNotContains(client.get("/schedule/?view=today"), "week_of=")

    def test_schedule_links_to_teachers_and_free_rooms(self):
        """P1-5: явные входы в «Преподаватели» и «Аудитории», неделя передаётся для возврата."""
        client = self.login(self.user_a)
        page = client.get("/schedule/?view=week&week_of=2026-12-28")
        self.assertContains(page, "teachers/?week_of=2026-12-28")
        self.assertContains(page, "free-rooms/?week_of=2026-12-28")
        # В режиме «Сегодня» неделя не передаётся.
        page = client.get("/schedule/?view=today")
        self.assertContains(page, "teachers/")

    def test_teachers_back_link_preserves_week(self):
        client = self.login(self.user_a)
        page = client.get(reverse("teachers"), {"week_of": "2026-12-28"})
        self.assertContains(page, "view=week&amp;week_of=2026-12-28")


class MarkAllNotificationsReadTests(BaseTestCase):
    def test_mark_all_touches_only_own_and_get_is_405(self):
        for i in range(2):
            Notification.objects.create(recipient=self.user_a, kind="status", title=f"A{i}")
        Notification.objects.create(recipient=self.user_b, kind="status", title="B0")

        client = self.login(self.user_a)
        self.assertEqual(client.get(reverse("notification_read_all")).status_code, 405)
        response = client.post(reverse("notification_read_all"))
        self.assertRedirects(response, reverse("notifications"))
        self.assertFalse(
            Notification.objects.filter(recipient=self.user_a, read_at__isnull=True).exists()
        )
        # Чужие уведомления не тронуты.
        self.assertTrue(
            Notification.objects.filter(recipient=self.user_b, read_at__isnull=True).exists()
        )


class HomeCtaTests(BaseTestCase):
    def test_home_links_to_zayavlenie_and_archive(self):
        client = self.login(self.user_a)
        page = client.get(reverse("home"))
        self.assertContains(page, "Подать заявление")
        self.assertContains(page, reverse("request_create_kind", args=["zayavlenie"]))
        self.assertContains(page, reverse("announcements"))


class AnnouncementsArchiveTests(BaseTestCase):
    def test_archive_shows_all_and_own_group_not_other_group(self):
        Announcement.objects.create(
            title="Общее объявление", body="Текст", audience=Announcement.Audience.ALL
        )
        Announcement.objects.create(
            title="Объявление группы",
            body="Текст",
            audience=Announcement.Audience.GROUP,
            group=self.user_a.student_profile.base_group,
        )
        other = Group.objects.create(code="МЭО-02", title="Другая группа")
        Announcement.objects.create(
            title="Чужое объявление",
            body="Текст",
            audience=Announcement.Audience.GROUP,
            group=other,
        )

        client = self.login(self.user_a)
        page = client.get(reverse("announcements"))
        self.assertContains(page, "Общее объявление")
        self.assertContains(page, "Объявление группы")
        self.assertNotContains(page, "Чужое объявление")
