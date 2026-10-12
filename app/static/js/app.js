(function () {
  "use strict";

  if (window.htmx) {
    window.htmx.config.allowEval = false;
    window.htmx.config.selfRequestsOnly = true;
  }

  document.addEventListener("DOMContentLoaded", function () {
    // Handle form auto-submit without inline event handlers
    var autoSubmitElements = document.querySelectorAll(
      "select[data-auto-submit], input[data-auto-submit]"
    );
    autoSubmitElements.forEach(function (el) {
      el.addEventListener("change", function () {
        if (el.form) {
          el.form.submit();
        }
      });
    });
  });
})();
