/* Marquez 0.51.1 public UI presentation overlay; not an API security boundary. */
(function () {
  'use strict';
  var orig = window.fetch;
  if (typeof orig === 'function') window.fetch = function (resource, options) {
    var url = typeof resource === 'string' ? resource : resource && resource.url;
    var method = String((options && options.method) || (resource && resource.method) || 'GET').toUpperCase();
    var pathname;
    try { pathname = new URL(url, window.location.href).pathname; }
    catch (_) { return Promise.reject(Error('Invalid URL')); }
    if (/^\/api\/(?:v1|v2beta)(?:\/|$)/i.test(pathname) && method !== 'GET' && method !== 'HEAD')
      return Promise.reject(Error('Public Web forbids write operations'));
    return orig.apply(this, arguments);
  };
  var mutating = /^(delete(?:\s+(?:job|dataset|tag))?|effacer|eliminar|usunąć|删除|edit\s+tag|submit|save(?:\s+changes)?)$/i;
  function hide() {
    document.querySelectorAll('button,[role="button"]').forEach(function (b) {
      var text = (b.textContent || '').trim().replace(/\s+/g, ' ');
      var title = (b.getAttribute('aria-label') || b.getAttribute('title') || '').trim();
      if ((mutating.test(text) || mutating.test(title)) && !b.hidden) {
        b.hidden = true;
        // MUI Button author styles can override the HTML hidden attribute.
        if (b.style) b.style.setProperty('display', 'none', 'important');
        b.setAttribute('aria-hidden', 'true');
      }
    });
    document.querySelectorAll('input#dataset-tags').forEach(function (input) {
      if (!input.disabled) input.disabled = true;
      if (input.tabIndex !== -1) input.tabIndex = -1;
      var parent = input.closest('.MuiAutocomplete-root');
      if (parent && !parent.classList.contains('public-readonly-tags')) parent.classList.add('public-readonly-tags');
    });
    var events = document.getElementById('eventsButton');
    if (events && !events.hidden) events.hidden = true;
  }
  function run() {
    hide();
    new MutationObserver(hide).observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run, { once: true });
  else run();
})();
