// FutureFunds - small client-side helpers.
// Most interactivity is handled by HTMX + Alpine.

// Shared design-token palette used by Chart.js charts and dashboard widgets.
window.FF_COLORS = {
  accent: '#4f46e5',
  positive: '#16a34a',
  negative: '#dc2626',
  muted: '#737373',
};

// Fix Chromium datepicker icon visibility in dark mode.
// Chromium's native datepicker icon doesn't reliably respect `color-scheme`
// when the Tailwind Play CDN is present. Setting colorScheme via JS inline
// style bypasses all CSS cascade issues and also covers dynamically added
// inputs (e.g. HTMX partial swaps).
(function () {
  function syncDatePickers() {
    var isDark = document.documentElement.classList.contains('dark');
    document.querySelectorAll('input[type="date"]').forEach(function (el) {
      el.style.colorScheme = isDark ? 'dark' : 'light';
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    syncDatePickers();
    // Re-sync whenever the dark class toggles on <html>
    new MutationObserver(syncDatePickers).observe(
      document.documentElement,
      { attributes: true, attributeFilter: ['class'] }
    );
  });
})();

// Replace native datepicker indicator with a custom <i> icon in Chromium.
// Firefox renders its native icon correctly regardless of theme, so skip it.
(function () {
  var isChromium = /Chrome|Edg|CriOS/i.test(navigator.userAgent);
  if (!isChromium) return;

  function enhanceDatepicker(input) {
    if (input.dataset.datepickerEnhanced) return;
    input.dataset.datepickerEnhanced = 'true';

    var wrapper = document.createElement('span');
    wrapper.style.cssText = 'position:relative;display:inline-block';

    // Transfer top margin from input to wrapper so vertical spacing is preserved
    var mt = window.getComputedStyle(input).marginTop;
    if (mt && mt !== '0px') {
      input.style.marginTop = '0px';
      wrapper.style.marginTop = mt;
    }

    var icon = document.createElement('i');
    icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>';
    icon.style.cssText = 'position:absolute;right:7px;top:50%;transform:translateY(-50%);cursor:pointer;pointer-events:auto;display:flex;align-items:center;justify-content:center;width:20px;height:20px;opacity:.5;color:inherit';
    icon.addEventListener('mouseenter', function () { icon.style.opacity = '.8'; });
    icon.addEventListener('mouseleave', function () { icon.style.opacity = '.5'; });
    icon.addEventListener('click', function (e) {
      e.stopPropagation();
      if (input.showPicker) input.showPicker();
      else input.focus();
    });

    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);
    wrapper.appendChild(icon);
  }

  function syncAll() {
    document.querySelectorAll('input[type="date"]').forEach(enhanceDatepicker);
  }

  document.addEventListener('DOMContentLoaded', function () {
    syncAll();
    // Catch date inputs added by HTMX partial swaps
    var target = document.querySelector('main') || document.body;
    new MutationObserver(syncAll).observe(target, { childList: true, subtree: true });
  });
})();

console.debug("FutureFunds frontend ready.");
