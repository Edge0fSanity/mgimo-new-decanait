from django.db import models


class ExternalLink(models.Model):
    """Полезная ссылка (Moodle, библиотека, кафедры); ввод через admin (ревью п.10, п.12)."""

    title = models.CharField("Название", max_length=120, unique=True)
    url = models.CharField("URL", max_length=300)
    sort_order = models.PositiveSmallIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        verbose_name = "Полезная ссылка"
        verbose_name_plural = "Полезные ссылки"
        ordering = ["sort_order"]

    def __str__(self):
        return self.title
