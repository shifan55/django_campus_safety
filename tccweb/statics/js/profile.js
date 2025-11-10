(function () {
  function focusFirstInput(form) {
    if (!form) {
      return;
    }
    var focusable = form.querySelector('input:not([type="hidden"]), textarea, select');
    if (focusable) {
      requestAnimationFrame(function () {
        try {
          focusable.focus({ preventScroll: true });
        } catch (error) {
          focusable.focus();
        }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    var editButton = document.getElementById('edit-profile-button');
    var form = document.getElementById('edit-profile-form');

    if (editButton && form) {
      editButton.addEventListener('click', function (event) {
        if (editButton.getAttribute('href') === '#') {
          event.preventDefault();
        }
        form.scrollIntoView({ behavior: 'smooth', block: 'start' });
        focusFirstInput(form);
      });
    }

    document.querySelectorAll('[data-profile-delete]').forEach(function (deleteForm) {
      if (!deleteForm.hasAttribute('data-confirm')) {
        deleteForm.setAttribute('data-confirm', 'Deleting your account is permanent. Are you sure you want to continue?');
      }
    });

    document.querySelectorAll('[data-profile-action]').forEach(function (actionForm) {
      if (!actionForm.hasAttribute('data-confirm')) {
        actionForm.setAttribute('data-confirm', 'Confirm this administrative action?');
      }
    });

    document.querySelectorAll('[data-profile-toggle]').forEach(function (button) {
      var targetId = button.getAttribute('data-profile-toggle');
      var target = targetId ? document.getElementById(targetId) : null;
      if (!target) {
        return;
      }
      button.addEventListener('click', function (event) {
        event.preventDefault();
        var expanded = button.getAttribute('aria-expanded') === 'true';
        button.setAttribute('aria-expanded', String(!expanded));
        target.hidden = expanded;
        if (!expanded) {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  });
})();