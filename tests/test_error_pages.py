from django.test import TestCase


class ErrorPagesTest(TestCase):
    def test_404_uses_custom_template(self):
        # DEBUG=False: студент на мёртвой ссылке видит страницу в стиле кабинета, а не голое «Not Found».
        response = self.client.get("/nonexistent-page/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Страница не найдена", status_code=404)
