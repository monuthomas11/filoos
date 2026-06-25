# Profile Dropdown Alignment Fix — Prompt for Another Model

## Context

I have a personal finance web app called "Filoos" built with:
- **Backend:** Python FastAPI with Jinja2 templates
- **Frontend:** Tailwind CSS v3.4, Alpine.js v3.13, HTMX
- **Template file:** `backend/app/templates/base.html` — the master layout with the header/nav

## Current State

The header has a profile avatar button (circle with user's first initial, 36×36px). When clicked, a dropdown menu appears below it showing user name, email, and a "Sign out" button.

The dropdown uses **pure CSS positioning** (no JavaScript):
```html
<div class="relative" @click.outside="profileOpen = false">
  <button class="inline-flex h-9 w-9 items-center justify-center rounded-full ...">
    {{ cu.name[:1] | upper }}
  </button>
  <div class="absolute right-0 top-full z-50 mt-2 w-56 origin-top-right rounded-lg ...">
    <!-- dropdown content: name, email, sign out -->
  </div>
</div>
```

## The Problem

The dropdown is 224px wide (`w-56`). With `absolute right-0`, its right edge aligns with the parent `div`'s right edge — which is only 36px wide (same as the avatar button). This means the dropdown extends **188px to the LEFT** of the avatar, visually covering the area to the left of the avatar.

**The user wants:** The dropdown should appear directly below the avatar, with its **right edge aligned to the avatar's right edge**, extending to the left. This is standard dropdown behavior (like Gmail, GitHub, etc.). The current CSS technically does this, but the user perceives it as "covering" the avatar because:
1. The vertical gap (`mt-2` = 8px) is too small — the dropdown looks like it's touching/overlapping the avatar
2. During scale transitions, the dropdown briefly appears to overlap

## What I Need

1. **Align the dropdown's right edge with the avatar's right edge** — this is already done with `absolute right-0`, but ensure it works correctly
2. **Add sufficient vertical spacing** so the dropdown is clearly below the avatar, not touching it
3. **Smooth transition** that doesn't make the dropdown appear to overlap the avatar during animation
4. **Cross-browser compatibility** — must work in both Chrome and Firefox
5. **Responsive** — must stay correctly positioned when browser DevTools are opened/closed, window is resized, or viewport changes
6. **No JavaScript positioning** — use pure CSS only. JavaScript-calculated `position: fixed` becomes stale on viewport changes

## Constraints

- The header is `position: sticky; z-index: 30`
- The avatar button is inside a flex container: `<div class="flex items-center gap-2">`
- The dropdown must have `z-index: 50` to appear above all page content
- Must support dark mode (classes: `dark:border-neutral-700 dark:bg-neutral-900`)
- The `[x-cloak]` style is defined: `[x-cloak] { display: none !important; }`
- Alpine.js handles show/hide with `x-show` and transitions

## Files to Edit

- `backend/app/templates/base.html` — the only file that needs changes (the profile dropdown section, lines ~60-105)

## Test Command

```bash
cd backend && python -m pytest --tb=short -q
```

All 246 tests must pass after changes.

## Desired Visual Result

When the avatar "M" is clicked, a dropdown should appear:
- **Vertically:** Below the avatar with ~8-12px gap (clearly separated, not touching)
- **Horizontally:** Right-aligned with the avatar's right edge (dropdown extends to the left)
- The dropdown should smoothly fade/scale in without appearing to overlap the avatar
- Must stay in correct position when DevTools panel opens/closes or window resizes
