---
name: Filoos
description: A warm, thoughtful personal expense tracker with a beautiful dashboard and balance predictions.
colors:
  accent-50: "#eef2ff"
  accent-100: "#e0e7ff"
  accent-500: "#6366f1"
  accent-600: "#4f46e5"
  accent-700: "#4338ca"
  positive-500: "#22c55e"
  positive-600: "#16a34a"
  negative-500: "#ef4444"
  negative-600: "#dc2626"
  neutral-50: "#fafafa"
  neutral-100: "#f5f5f5"
  neutral-200: "#e5e5e5"
  neutral-300: "#d4d4d4"
  neutral-400: "#a3a3a3"
  neutral-500: "#737373"
  neutral-600: "#525252"
  neutral-700: "#404040"
  neutral-900: "#171717"
  neutral-950: "#0a0a0a"
typography:
  display:
    fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "clamp(1.5rem, 4vw, 2.25rem)"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: -0.02em
  title:
    fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "clamp(1.125rem, 2.5vw, 1.5rem)"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.01em
  body:
    fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0.02em
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent-600}"
    textColor: "#ffffff"
    rounded: "{rounded.lg}"
    padding: "12px 20px"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "{colors.accent-700}"
  card-default:
    backgroundColor: "#ffffff"
    textColor: "{colors.neutral-900}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
  card-dark:
    backgroundColor: "{colors.neutral-900}"
    textColor: "{colors.neutral-100}"
  input-text:
    backgroundColor: "#ffffff"
    textColor: "{colors.neutral-900}"
    rounded: "{rounded.lg}"
    padding: "8px 12px"
    typography: "{typography.body}"
---

# Design System: Filoos

## 1. Overview

**Creative North Star: "The Friendly Teller"**

Filoos feels like a helpful person walking you through your finances — approachable, conversational, and clear. The interface is thoughtful and minimal without feeling cold, warm without feeling cluttered. Numbers are friends, not verdicts. Every screen is built around the idea that expense tracking is a chore, and good design turns obligation into a small daily ritual.

The system explicitly rejects dense enterprise software — no crowded data tables, no overwhelming dashboards, no cold institutional banking aesthetics. Instead, it uses soft rounded corners, gentle shadows on interaction, a warm neutral palette with indigo as a single deliberate accent, and semantic green/red for income and expense.

**Key Characteristics:**
- **Warm minimalism.** Generous whitespace, clear hierarchy, nothing extraneous.
- **Soft and tactile.** Large rounded corners (12px), gentle hover lifts, friendly interaction shapes.
- **Lightly layered.** Cards rest at neutral-200 borders; hover reveals a subtle shadow-sm. Depth comes from gentle elevation, not aggressive drops.
- **Semantic color discipline.** Indigo is the single accent. Emerald is exclusively income/in-budget. Red is exclusively expense/over-budget. Never cross the streams.

## 2. Colors

A warm neutral palette anchored by a single indigo accent. Color carries meaning: green is always income-related, red is always expense-related, indigo is interactive.

### Primary
- **Indigo** (#4f46e5 / oklch(0.505 0.160 296.8)) — The single accent. Primary buttons, interactive links, focused borders, Chart.js line/bar fills. Used on ≤10% of any given screen. Its rarity is the point.

### Semantic
- **Emerald** (#16a34a / oklch(0.628 0.182 149.2)) — Income amounts, positive budget states, savings-rate badges. Never decorative.
- **Red** (#dc2626 / oklch(0.585 0.233 29.2)) — Expense amounts, delete actions, over-budget warnings, negative trend badges. Never decorative.

### Neutral
- **Neutral-50** (#fafafa) — Page background (light mode).
- **Neutral-100** (#f5f5f5) — Subtle card hover / secondary surface (light).
- **Neutral-200** (#e5e5e5) — Borders, dividers, input strokes (light).
- **Neutral-900** (#171717) — Primary body text (light mode).
- **Neutral-500** (#737373) — Muted/secondary text, placeholder text, footer links.
- **Neutral-400** (#a3a3a3) — Label text for minor metadata.
- **Neutral-950** (#0a0a0a) — Page background (dark mode).
- **Neutral-100** (#f5f5f5) — Primary body text (dark mode).
- **Neutral-800** (#262626) — Borders and dividers (dark mode).
- **Neutral-900** (#171717) — Card surface (dark mode).

### The Semantic Color Rule
Green and red are forbidden as decorative accent. They mean income and expense respectively — never anything else. A green button would confuse the user into thinking it means "income" or "profit." If a button needs emphasis, use the indigo accent or a neutral treatment.

## 3. Typography

**Display & Body Font:** System UI stack (system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif). No web fonts loaded — zero added latency, native feel on every platform.

**Mono Font:** UI monospace stack (ui-monospace, SFMono-Regular, Menlo, monospace) — used only for code-level references, never for financial amounts.

**Character:** The system font reads as inherently familiar and trustworthy. It doesn't compete for attention. The type hierarchy communicates clearly through weight and size contrast, not exotic faces.

### Hierarchy

- **Display** (600 weight, clamp(1.5rem, 4vw, 2.25rem), 1.15 line-height, -0.02em letter-spacing): Page-level headings (Dashboard, Accounts, Transactions). `text-wrap: balance`.
- **Title** (600 weight, clamp(1.125rem, 2.5vw, 1.5rem), 1.2 line-height, -0.01em letter-spacing): Section headings within pages, card titles.
- **Body** (400 weight, 0.875rem, 1.5 line-height): General content, descriptions, form labels.
- **Label** (500 weight, 0.75rem, 1.4 line-height, 0.02em letter-spacing): Small metadata labels, KPI card headers, account type badges, period labels. Often set in uppercase with wide tracking for visual density contrast.

Small print (amounts, dates, secondary metadata): 0.625–0.75rem (10–12px), neutral-500.

### Named Rules

**The Single Scale Rule.** There is one typographic scale. Headings use weight and size from the same family — no display face, no serif pairing. The system font is enough.

**The 75ch Rule.** Body text width is capped at 75 characters. Forms on dedicated pages are constrained to max-w-lg (512px) for comfortable reading.

## 4. Elevation

Filoos uses a **lightly layered** elevation system. Cards are flat at rest with a soft border (1px, neutral-200 / dark: neutral-800). Hover reveals a subtle shadow-sm to signal interactivity. The header uses backdrop blur (bg-white/80 backdrop-blur) for a frosted-glass effect that preserves scroll context.

No aggressive drops, no multiplanar depth. Surfaces are distinguished by border + background contrast, not shadow.

### Shadow Vocabulary
- **Interaction lift** (`box-shadow: 0 1px 2px rgba(0,0,0,0.05)`) — Tailwind's shadow-sm. Applied on card hover, button hover. Gentle; barely perceptible. Signals tappability without bouncing.
- **Modal/Dropdown** (`box-shadow: 0 4px 24px rgba(0,0,0,0.12)`) — Tailwind's shadow-lg. Reserved for overlays that break the flat plane: profile dropdown, confirmation dialogs.
- **Header blur** (`backdrop-filter: blur(12px)`) — The sticky header uses backdrop blur + semi-transparent background. Content scrolls behind it without jarring occlusion.

### Named Rules

**The Flat-At-Rest Rule.** Surfaces are flat by default. Shadows appear only as a response to state — hover, focus, or elevation above the page. At rest, borders do the work.

## 5. Components

### Buttons
- **Shape:** Generously rounded (12px radius). Full height for touch targets.
- **Primary:** Indigo-600 background, white text, 14px/500 weight. Hover deepens to indigo-700. No border — the fill is the affordance. `focus-visible:outline-2 outline-offset-2 outline-accent-600`.
- **Secondary / Ghost:** No background, neutral-700 text. Hover reveals a neutral-100 background. Used for "Cancel" links, secondary actions.
- **Icon-only:** 28×28px (h-7 w-7), 8px radius, transparent bg, neutral-400 icon. Hover reveals neutral-100 bg and neutral-700 icon. Delete variants hover on red-50 bg with red-600 icon.

### Cards / Containers
- **Corner Style:** 12px radius (rounded-lg).
- **Background:** White (light) / neutral-900 (dark). 1px border in neutral-200 (light) / neutral-800 (dark).
- **Shadow Strategy:** None at rest (see Elevation). `hover:shadow-sm` on actionable cards.
- **Internal Padding:** 12px on mobile (p-3), 16px on tablet+ (sm:p-4). Section-level containers (dashboard panels) use 20px (p-5).
- **Empty State:** Dashed border (border-dashed) in neutral-300, centered text with an action link.

### Inputs / Fields
- **Style:** 1px stroke in neutral-300 (light) / neutral-700 (dark). 12px radius. White bg (light) / neutral-900 (dark).
- **Text:** 14px/400, neutral-900 (light) / neutral-100 (dark). Placeholder at neutral-400.
- **Focus:** Border shifts to accent-500, 1px ring in accent-500. No glow.
- **Checkbox:** 16×16px, rounded (4px), accent-600 checked state. Hidden `value="false"` field precedes every checkbox to handle the unchecked case.
- **Color input:** Native `<input type="color">` at 32×48px, no border radius override. Accompanied by a live preview swatch.

### Navigation
- **Desktop:** Horizontal bar in the sticky header, 14px text, neutral-700 (light) / neutral-300 (dark). 8px rounded hover pill (neutral-100 bg).
- **Mobile:** Slide-down panel triggered by hamburger icon. Full-width links with 12px radius, 14px/500 text, neutral-700. Closes on link click or outside tap. Animated with Alpine.js x-transition (ease-out 200ms enter, ease-in 150ms leave).
- **Active state:** No persistent active indicator. Current page is implied by context (the user arrived there). Future: a subtle bottom-border or font-semibold on the matching nav link.

### Badges / Chips
- **Style:** Fully rounded (rounded-full), small horizontal padding (px-1.5 sm:px-2), 10–12px font, medium weight.
- **Active badge:** Tinted background from the entity's color at 15% opacity, text at 100% opacity. Preceded by a 6px dot in the entity's color for scannability.
- **Type badge (transaction):** 28×28px rounded icon container, tinted background per type (positive-500/10 for income, negative-500/10 for expense, accent-500/10 for transfer).
- **KPI labels:** 10–12px uppercase with wide tracking (tracking-wide), neutral-500. Always sits above the value for scanning consistency.

### Data Display / Charts
- **Bar Chart (Chart.js):** Single dataset, indigo-600 bars with 4px border radius. No legend. Grid lines at `rgba(0,0,0,0.06)` on y-axis, no x-axis grid.
- **Doughnut Chart:** Per-item colors from category data, no borders. Legend below chart in 11px font, 12px box width.
- **Line Chart (Trend):** Indigo-600 line at 2px stroke. Trend = solid, projection = dashed (6,3). Fill under trend at indigo-600 with 12% opacity. Tension 0.3 for gentle curves. No point dots.

## 6. Do's and Don'ts

### Do:
- **Do** use indigo as the single accent color for all interactive elements. Consistency builds familiarity.
- **Do** use emerald for income amounts and positive trends only — never for decoration.
- **Do** use red for expense amounts and negative trends only — never for decoration.
- **Do** prefer generous whitespace and clear hierarchy. When in doubt, remove rather than add.
- **Do** use 12px radius on all containers, buttons, and inputs for a soft, tactile feel.
- **Do** add subtle `hover:shadow-sm` to cards that are actionable — it signals tappability without bouncing.
- **Do** constrain form widths to max-w-lg (512px) for comfortable reading on dedicated pages.
- **Do** use `text-wrap: balance` on headings for even line lengths.
- **Do** use the system font stack. No web fonts, no extra latency.

### Don't:
- **Don't** use emerald or red as decorative accents — they carry semantic meaning and must only signal income/expense.
- **Don't** replicate dense enterprise software patterns: crowded tables, overwhelming dashboards, cold institutional tones.
- **Don't** use side-stripe borders (greater than 1px) as colored accents on cards or list items. Use full backgrounds or nothing.
- **Don't** use gradient text, glassmorphism, or decorative blurs. The aesthetic is warm and tactile, not glossy or ethereal.
- **Don't** use identical card grids with icon + heading + text repeated endlessly. Vary layout within the grid.
- **Don't** use tiny uppercase tracked eyebrow above every section — it's the saturated AI scaffold of 2023-era design. One deliberate kicker is voice; an eyebrow on every section is grammar.
- **Don't** use numbered section markers (01 / 02 / 03) as default scaffolding. Numbers earn their place when the section is actually a sequence.
- **Don't** use shadow in rest state. Surfaces are flat at rest; shadows only on hover or elevation.
- **Don't** nest cards. A card within a card means the system needs a different container strategy.
