from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import RequestForm
from .models import DemoDocument, RequestStatusEvent, StudentRequest

# Две формы заявки: тип задаёт URL, не студент.
KIND_BY_SLUG = {"spravka": StudentRequest.Type.CERTIFICATE, "zayavlenie": StudentRequest.Type.APPLICATION}


@login_required
def request_list(request):
    requests = StudentRequest.objects.filter(owner=request.user)
    return render(request, "requests_app/request_list.html", {"requests": requests})


@login_required
@require_http_methods(["GET", "POST"])
def request_create(request, kind="spravka"):
    type_value = KIND_BY_SLUG.get(kind)
    if type_value is None:
        raise Http404
    if request.method == "POST":
        form = RequestForm(type_value, request.POST)
        if form.is_valid():
            # Владелец, тип и статус задаёт только сервер, из request.user и URL.
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.type = type_value
            obj.status = StudentRequest.Status.SUBMITTED
            obj.save()
            RequestStatusEvent.objects.create(
                request=obj, to_status=obj.status, actor=request.user, note="Заявка подана студентом"
            )
            return redirect("request_detail", pk=obj.pk)
    else:
        form = RequestForm(type_value)
    titles = {"spravka": "Новая справка", "zayavlenie": "Новое заявление"}
    return render(
        request,
        "requests_app/request_form.html",
        {"form": form, "kind": kind, "title": titles[kind]},
    )


@login_required
@require_http_methods(["GET"])
def request_detail(request, pk):
    # Чужая заявка не существует для этого пользователя: 404 без содержимого.
    obj = get_object_or_404(StudentRequest, pk=pk, owner=request.user)
    return render(
        request,
        "requests_app/request_detail.html",
        {"obj": obj, "events": obj.status_events.select_related("actor")},
    )


@login_required
@require_http_methods(["GET"])
def document_download(request, pk):
    # Чужой документ не существует для этого пользователя: 404 без содержимого.
    doc = get_object_or_404(DemoDocument, pk=pk, owner=request.user)
    return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.file.name.rsplit("/", 1)[-1])
