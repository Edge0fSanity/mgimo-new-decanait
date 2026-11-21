from .models import ExternalLink


def useful_links(request):
    """Полезные ссылки для футера base.html (ревью п.10, п.12)."""
    return {"useful_links": ExternalLink.objects.filter(is_active=True)}
