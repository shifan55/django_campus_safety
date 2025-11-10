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
    var avatarInput = document.querySelector('[data-avatar-input]');
    var avatarPreview = document.querySelector('[data-avatar-preview]');

    if (editButton && form) {
      editButton.addEventListener('click', function (event) {
        if (editButton.getAttribute('href') === '#') {
          event.preventDefault();
        }
        form.scrollIntoView({ behavior: 'smooth', block: 'start' });
        focusFirstInput(form);
      });
    }

    if (avatarInput && avatarPreview) {
      var fallbackSrc = avatarPreview.getAttribute('src');
      var allowedTypes = (avatarInput.getAttribute('data-avatar-allowed') || '').split(',');
      var maxSize = parseInt(avatarInput.getAttribute('data-avatar-max-size'), 10) || (5 * 1024 * 1024);

      avatarInput.addEventListener('change', function () {
        var file = avatarInput.files && avatarInput.files[0];
        avatarInput.setCustomValidity('');
        if (!file) {
          avatarPreview.setAttribute('src', fallbackSrc);
          return;
        }
        var typeValid = !allowedTypes[0] || allowedTypes.indexOf(file.type) !== -1;
        var sizeValid = !file.size || file.size <= maxSize;
        if (!typeValid) {
          avatarInput.setCustomValidity('Please choose a JPG, PNG, or GIF image.');
        } else if (!sizeValid) {
          avatarInput.setCustomValidity('Please choose an image smaller than 5 MB.');
        }
        if (!typeValid || !sizeValid) {
          avatarInput.value = '';
          avatarPreview.setAttribute('src', fallbackSrc);
          avatarInput.reportValidity();
          return;
        }
        var reader = new FileReader();
        reader.addEventListener('load', function (event) {
          if (typeof event.target.result === 'string') {
            avatarPreview.setAttribute('src', event.target.result);
            fallbackSrc = avatarPreview.getAttribute('src');
          }
        });
        reader.readAsDataURL(file);
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