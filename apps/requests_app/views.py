from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import MaintenanceForm, RequestForm
from .models import DemoDocument, MaintenanceRequest, RequestStatusEvent, StudentRequest

# Две формы заявки: тип задаёт URL, не студент.
KINDS = {
    "spravka": (StudentRequest.Type.CERTIFICATE, "Заказать справку"),
    "zayavlenie": (StudentRequest.Type.APPLICATION, "Подать заявление"),
}


@login_required
def request_list(request):
    entries = StudentRequest.objects.filter(owner=request.user)
    # Фильтр по типу/подтипу (ревью п.13); неизвестные значения игнорируются.
    type_value = request.GET.get("type")
    subtype_value = request.GET.get("subtype")
    if type_value in StudentRequest.Type.values:
        entries = entries.filter(type=type_value)
    if subtype_value in StudentRequest.Subtype.values:
        entries = entries.filter(subtype=subtype_value)
    page = Paginator(entries, 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "requests_app/request_list.html",
        {
            "page_obj": page,
            "querystring": params.urlencode(),
            "type_value": type_value if type_value in StudentRequest.Type.values else "",
            "subtype_value": subtype_value if subtype_value in StudentRequest.Subtype.values else "",
            "type_choices": StudentRequest.Type.choices,
            "subtype_choices": StudentRequest.Subtype.choices,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def request_create(request, kind="spravka"):
    if kind not in KINDS:
        raise Http404
    type_value, title = KINDS[kind]
    if request.method == "POST":
        form = RequestForm(type_value, request.POST)
        if form.is_valid():
            # Владелец, тип и статус задаёт только сервер, из request.user и URL.
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.type = type_value
            obj.status = StudentRequest.Status.SUBMITTED
            # Заявка и первая запись истории сохраняются атомарно.
            with transaction.atomic():
                obj.save()
                RequestStatusEvent.objects.create(
                    request=obj, to_status=obj.status, actor=request.user, note="Заявка подана студентом"
                )
            return redirect("request_detail", pk=obj.pk)
    else:
        form = RequestForm(type_value)
    # Профиль только для показа на шаге подтверждения; отсутствие профиля не ломает форму.
    profile = request.user.student_profile if hasattr(request.user, "student_profile") else None
    return render(
        request,
        "requests_app/request_form.html",
        {"form": form, "kind": kind, "title": title, "profile": profile},
    )


@login_required
@require_http_methods(["POST"])
def request_cancel(request, pk):
    # Отменить можно только свою заявку и только пока она не взята в работу.
    obj = get_object_or_404(
        StudentRequest, pk=pk, owner=request.user, status=StudentRequest.Status.SUBMITTED
    )
    with transaction.atomic():
        obj.status = StudentRequest.Status.CANCELLED
        obj.save(update_fields=["status", "updated_at"])
        RequestStatusEvent.objects.create(
            request=obj,
            from_status=StudentRequest.Status.SUBMITTED,
            to_status=obj.status,
            actor=request.user,
            note="Заявка отменена студентом",
        )
    return redirect("request_detail", pk=obj.pk)


@login_required
@require_http_methods(["GET"])
def request_detail(request, pk):
    # Чужая заявка не существует для этого пользователя: 404 без содержимого.
    obj = get_object_or_404(StudentRequest, pk=pk, owner=request.user)
    events = list(obj.status_events.all())
    rejection = None
    if obj.status == StudentRequest.Status.REJECTED:
        rejection = next(
            (event for event in reversed(events) if event.to_status == StudentRequest.Status.REJECTED),
            None,
        )
    return render(
        request,
        "requests_app/request_detail.html",
        {
            "obj": obj,
            "events": events,
            "rejection": rejection,
            "documents": obj.documents.filter(owner=request.user),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def maintenance(request):
    """Заявки на обслуживание кабинетов (ревью п.13): форма + свои заявки."""
    entries = MaintenanceRequest.objects.filter(owner=request.user).select_related("room")
    if request.method == "POST":
        form = MaintenanceForm(request.POST)
        if form.is_valid():
            # Владелец и статус задаёт только сервер, из request.user.
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.status = MaintenanceRequest.Status.SUBMITTED
            obj.save()
            messages.success(request, "Заявка зарегистрирована")
            return redirect("maintenance")
    else:
        form = MaintenanceForm()
    return render(
        request,
        "requests_app/maintenance.html",
        {"form": form, "entries": entries},
    )


@login_required
@require_http_methods(["GET"])
@never_cache
def request_sample(request, pk):
    obj = get_object_or_404(StudentRequest, pk=pk, owner=request.user, status=StudentRequest.Status.READY)
    response = render(request, "requests_app/request_sample.html", {"obj": obj})
    response.headers["Content-Disposition"] = 'attachment; filename="request-sample.html"'
    return response


@login_required
@require_http_methods(["GET"])
@never_cache
def document_download(request, pk):
    # Чужой документ не существует для этого пользователя: 404 без содержимого.
    doc = get_object_or_404(DemoDocument, pk=pk, owner=request.user)
    return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.file.name.rsplit("/", 1)[-1])
