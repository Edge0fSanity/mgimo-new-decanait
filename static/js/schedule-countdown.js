// T35: «через N ч M мин» / «M мин» / «идёт сейчас» у ближайшего занятия.
// Даты приходят из шаблона в МСК с офсетом, Date-сравнение абсолютное —
// пояс устройства на результат не влияет.
(function () {
  var entries = Array.prototype.slice.call(
    document.querySelectorAll(".entry[data-starts-at]")
  );
  if (!entries.length) return;

  var badge = document.createElement("span");
  badge.className = "badge countdown-badge";

  function format(mins) {
    if (mins < 60) return "через " + mins + " мин";
    var h = Math.floor(mins / 60);
    var m = mins % 60;
    return "через " + h + " ч" + (m ? " " + m + " мин" : "");
  }

  function show(li, text) {
    badge.textContent = text;
    li.querySelector(".time").after(badge);
  }

  function update() {
    badge.remove();
    var now = Date.now();
    var next = null;
    for (var i = 0; i < entries.length; i++) {
      var li = entries[i];
      var start = Date.parse(li.dataset.startsAt);
      var end = Date.parse(li.dataset.endsAt);
      if (now >= start && now < end) {
        show(li, "идёт сейчас");
        return;
      }
      if (start > now && (!next || start < Date.parse(next.dataset.startsAt))) {
        next = li;
      }
    }
    if (next) {
      show(next, format(Math.round((Date.parse(next.dataset.startsAt) - now) / 60000)));
    }
  }

  update();
  setInterval(update, 60000);
})();
