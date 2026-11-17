from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import RequestForm
from .models import RequestStatusEvent, StudentRequest


@login_required
def request_list(request):
    requests = StudentRequest.objects.filter(owner=request.user)
    return render(request, "requests_app/request_list.html", {"requests": requests})


@login_required
@require_http_methods(["GET", "POST"])
def request_create(request):
    if request.method == "POST":
        form = RequestForm(request.POST)
        if form.is_valid():
            # Владелец и статус задаёт только сервер, из request.user.
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.status = StudentRequest.Status.SUBMITTED
            obj.save()
            RequestStatusEvent.objects.create(
                request=obj, to_status=obj.status, actor=request.user, note="Заявка подана студентом"
            )
            return redirect("request_detail", pk=obj.pk)
    else:
        form = RequestForm(initial={"type": StudentRequest.Type.CERTIFICATE})
    return render(request, "requests_app/request_form.html", {"form": form})


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
