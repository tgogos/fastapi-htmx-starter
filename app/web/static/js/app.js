/**
 * Minimal vanilla JS bindings for the HTMX UI.
 * - Pico <dialog> confirm before destructive HTMX deletes
 * - Toast notifications (HX-Trigger: showToast)
 * - Dismiss flash messages
 * - Send CSRF header on HTMX requests when meta csrf-token is present
 */
(function () {
  "use strict";

  var pendingConfirmEl = null;

  function confirmDialog() {
    return document.getElementById("confirm-dialog");
  }

  function confirmMessageEl() {
    return document.getElementById("confirm-dialog-message");
  }

  function openConfirm(el) {
    var dialog = confirmDialog();
    var messageEl = confirmMessageEl();
    if (!dialog || !messageEl) {
      return false;
    }
    pendingConfirmEl = el;
    messageEl.textContent = el.getAttribute("data-confirm") || "Are you sure?";
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    var confirmBtn = document.getElementById("confirm-dialog-ok");
    if (confirmBtn) {
      confirmBtn.focus();
    }
    return true;
  }

  function closeConfirm() {
    var dialog = confirmDialog();
    pendingConfirmEl = null;
    if (!dialog) {
      return;
    }
    if (typeof dialog.close === "function") {
      dialog.close();
    } else {
      dialog.removeAttribute("open");
    }
  }

  function toastRegion() {
    return document.getElementById("toast-region");
  }

  function showToast(message, level) {
    var region = toastRegion();
    if (!region || !message) {
      return;
    }
    var toast = document.createElement("div");
    toast.className = "toast toast-" + (level || "ok");
    toast.setAttribute("role", "status");
    toast.textContent = message;

    var dismiss = document.createElement("button");
    dismiss.type = "button";
    dismiss.className = "toast-dismiss";
    dismiss.setAttribute("aria-label", "Dismiss");
    dismiss.textContent = "×";
    dismiss.addEventListener("click", function () {
      toast.remove();
    });
    toast.appendChild(dismiss);
    region.appendChild(toast);

    window.setTimeout(function () {
      toast.classList.add("toast-out");
      window.setTimeout(function () {
        toast.remove();
      }, 200);
    }, 3500);
  }

  document.body.addEventListener("click", function (event) {
    var dismiss = event.target.closest(".flash-dismiss");
    if (dismiss) {
      var flash = dismiss.closest(".flash");
      if (flash) {
        flash.remove();
      }
      return;
    }

    var deleteBtn = event.target.closest(".js-confirm-delete");
    if (deleteBtn) {
      event.preventDefault();
      event.stopPropagation();
      if (!openConfirm(deleteBtn)) {
        // Fallback if dialog markup missing
        var message = deleteBtn.getAttribute("data-confirm") || "Are you sure?";
        if (window.confirm(message)) {
          htmx.trigger(deleteBtn, "confirmed-delete");
        }
      }
    }
  }, true);

  document.body.addEventListener("click", function (event) {
    if (event.target.closest("[data-confirm-cancel]")) {
      closeConfirm();
      return;
    }
    if (event.target.closest("[data-confirm-ok]")) {
      var el = pendingConfirmEl;
      closeConfirm();
      if (el && window.htmx) {
        htmx.trigger(el, "confirmed-delete");
      }
    }
  });

  var dialog = confirmDialog();
  if (dialog) {
    dialog.addEventListener("cancel", function () {
      pendingConfirmEl = null;
    });
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) {
        closeConfirm();
      }
    });
  }

  document.body.addEventListener("showToast", function (event) {
    var detail = event.detail || {};
    showToast(detail.message, detail.level);
  });

  document.body.addEventListener("htmx:config:request", function (event) {
    var meta = document.querySelector('meta[name="csrf-token"]');
    var ctx = event.detail && event.detail.ctx;
    var headers = ctx && ctx.request && ctx.request.headers;
    if (!meta || !headers) {
      return;
    }
    var token = meta.getAttribute("content");
    if (token && !headers["X-CSRF-Token"]) {
      headers["X-CSRF-Token"] = token;
    }
  });
})();
