# Filoos — Pre-Launch Privacy & GDPR Readiness Plan

> Companion to `PLAN.md`, `STATUS.md`, and `deployment.md`.
> This document captures the **go-live privacy checklist**, a **GDPR review**
> of the current codebase, a **prioritized remediation plan**, and a **draft
> Privacy Policy** to be shipped as a real page in the app.

---

## 1. Before you launch — check these 10 things

✅ **Privacy policy (GDPR/CCPA)**
    Protect yourself, not just your app. The moment you collect user data you're in legal territory (GDPR, CCPA). Have a privacy policy. Know where user data lives.

✅ **Row Level Security (RLS) / data isolation**
    Without isolation, anyone can open DevTools and read your entire database. Supabase → Auth → Policies. Zero policies means your app is naked. (Filoos uses app-level `user_id` scoping — see §3.2.)

✅ **Test failure paths, not just happy paths**
    Wrong password 5x. Reset for an email that doesn't exist. Verification link clicked twice. Signup with an existing email. Catches 80% of auth bugs.

✅ **Security headers**
    Review the app as a security specialist and make sure there are strong security headers and a solid baseline security posture.

✅ **OWASP security review**
    Review the app against OWASP standards and highlight vulnerabilities.

✅ **Server-side validation**

✅ **No API keys or secrets in the frontend**

---

## 2. GDPR review of the current Filoos codebase

Filoos is a **personal expense tracker** that processes personal and financial
data. Under the GDPR this is **special-category-adjacent** processing (financial
data is sensitive even if not formally Article 9 special category), so the bar
for transparency, user rights, and safeguards is high.

### 2.1 What personal data Filoos collects

| Category | Data points | Source | Where stored |
|---|---|---|---|
| Identity | `email`, `name`, `google_sub` | Google OAuth (`openid email profile` scope) | `users` table (Postgres/SQLite) |
| Account metadata | `last_login_at`, `created_at`, `updated_at` | App | `users` table |
| Financial data | accounts, balances, transactions, descriptions, notes, budgets, categories, recurring rules | User input | `accounts`, `transactions`, `categories`, `budgets`, `recurring_rules` tables |
| Session | `user_id` | App | Signed session cookie (client-side) |
| Technical | request method, path, status, `request_id`, duration | Request-logging middleware | Server stdout logs (Render log viewer, 7-day retention) |

### 2.2 Findings (GDPR gaps)

| # | Finding | GDPR article | Severity |
|---|---|---|---|
| F1 | **No Privacy Policy exists.** `login.html:181` links `Privacy Policy` (and `Terms of Service`) to `#` — dead links. No `/privacy` route, no template. | Art. 13/14 (transparency) | **High** |
| F2 | **No data subject rights implemented.** Users cannot export (Art. 20), cannot delete their account/all data (Art. 17), cannot rectify profile data (Art. 16). `deployment.md` lists "Per-user data export" as deferred to v2. | Art. 15, 16, 17, 20 | **High** |
| F3 | **No "delete my account" flow.** `auth.py` has `/auth/logout` (clears session only). Nothing deletes the `User` row or cascades to their financial data. Users can delete individual accounts/transactions but not themselves. | Art. 17 (right to erasure) | **High** |
| F4 | **No cookie notice/consent.** The ePrivacy Directive + GDPR require informing users about cookies. The session cookie is *strictly necessary* (exempt from consent) but this must be disclosed. No banner/notice present. | ePrivacy + Art. 13 | **Medium** |
| F5 | **Third-party processors not disclosed.** Personal data flows to: Google (OAuth + `gstatic.com` logo asset on login), `unpkg.com`/`cdn.jsdelivr.net` (JS CDNs), Render (hosting), Neon (database). None listed in a privacy policy. | Art. 13(1)(e), Art. 28 (processors) | **High** |
| F6 | **International data transfers undocumented.** Google (US), CDN providers (US/global), Render/Neon regions vary. No Standard Contractual Clauses or transfer safeguards documented. | Art. 44–49 | **Medium** |
| F7 | **No legal basis stated.** Processing of email/name/financial data has no documented lawful basis (legitimate interest / contract / consent). | Art. 6 | **High** |
| F8 | **No data retention policy.** Financial data is retained indefinitely with no documented retention period or auto-purge. Session cookie max-age is 14 days but not disclosed. | Art. 5(1)(e) (storage limitation) | **Medium** |
| F9 | **No privacy contact / DPO channel.** No email or form for data subject requests (DSAR). Footer credits "Created by ❤️ Monu Thomas" but gives no privacy contact. | Art. 13(1)(b), Art. 37–39 | **Medium** |
| F10 | **`last_login_at` never set.** `auth.py:79` sets `user.last_login_at = None` on every login instead of `datetime.now(timezone.utc)`. Login-tracking metadata is collected incorrectly (silent bug). | Art. 5(1)(d) (accuracy) | **Low** |
| F11 | **No breach notification procedure.** No documented 72-hour authority-notification process. | Art. 33–34 | **Medium** |
| F12 | **No DPIA for financial-data processing.** While not formally Article 35 mandatory, a lightweight DPIA is best practice given the sensitivity of financial data. | Art. 35 | **Low** |
| F13 | **No age-gate.** Google OAuth allows any account. Art. 8 requires parental consent for under-16s. No age info is collected, so this is hard to enforce, but the policy must address it. | Art. 8 | **Low** |
| F14 | **OpenAPI docs (`/docs`, `/redoc`) publicly reachable.** Schema disclosure (already noted in `deployment.md` §5). Not a GDPR issue per se but a security-posture item that affects personal-data exposure. | Art. 32 (security) | **Low** |

### 2.3 What's already done well

- ✅ **Per-user data isolation** — every CRUD function scopes by `user_id`; cross-user access returns 404 (`deployment.md` §8, test coverage in `test_auth.py`).
- ✅ **Session cookie is `Secure` + `HttpOnly` + `SameSite=Lax`** in production (`main.py:55`, `config.py:120`).
- ✅ **HTTPS enforced** in production via `HTTPSRedirectMiddleware` (`main.py:62`).
- ✅ **`TrustedHostMiddleware`** blocks host-header attacks (`main.py:64`).
- ✅ **Secrets out of the repo** — `.env` is gitignored (verified), `.env.example` carries no real secrets, Docker build excludes `.env`.
- ✅ **Server-side validation** — Pydantic schemas + router-layer amount checks.
- ✅ **No API keys in frontend** — `static/js/app.js` is a placeholder; all secrets server-side.
- ✅ **Structured logging** without dumping request bodies/PII into logs.
- ✅ **Backups** — Neon PITR (7-day) + planned `pg_dump`.

---

## 3. Remediation plan (prioritized)

### Phase P0 — Must-do before any public launch

| # | Task | Files | Effort |
|---|---|---|---|
| P0.1 | **Ship a real Privacy Policy page** (see §4 to-do + §5 draft) | new `templates/privacy.html`, new route in `routers/pages.py`, fix `login.html` dead links, add footer link in `base.html` | 1–2 h |
| P0.2 | **Wire the dead links.** Point `login.html` "Privacy Policy" → `/privacy`, "Terms of Service" → `/terms` (create a minimal Terms stub or remove the ToS link until a real ToS exists). | `login.html` | 5 min |
| P0.3 | **Add a privacy contact.** Define a `FF_PRIVACY_EMAIL` setting (or reuse owner email) and surface it in the policy + footer. | `config.py`, `base.html`, `privacy.html` | 15 min |
| P0.4 | **State the lawful basis** in the policy (contract for core features; legitimate interest for security logging; consent not used since auth is OAuth). | `privacy.html` content | — |
| P0.5 | **Disclose all third-party processors + transfer basis** (Google, Render, Neon, unpkg, jsdelivr). | `privacy.html` content | — |

### Phase P1 — Data subject rights (ship shortly after launch)

| # | Task | Files | Effort |
|---|---|---|---|
| P1.1 | **Right to erasure — "Delete account" flow.** New `POST /auth/delete-account` that deletes the `User` and cascades (or hard-deletes all owned rows) then clears the session. Add a confirmation page + CSRF-safe form. Consider a soft-delete + 30-day grace period. | `routers/auth.py`, `crud/`, new `templates/account/delete.html` | 2–3 h |
| P1.2 | **Right to data portability — data export.** New `GET /api/account/export` returning JSON (and/or CSV) of all the user's accounts, transactions, categories, budgets, recurring rules. Add a "Download my data" button on a settings/account page. | `routers/`, `crud/`, new settings page | 2–3 h |
| P1.3 | **Right to access (DSAR) endpoint.** A read-only summary view (could reuse the export) plus a documented `mailto:` path for manual requests. | `privacy.html` + export | 0.5 h |
| P1.4 | **Fix `last_login_at` bug.** Set `user.last_login_at = datetime.now(timezone.utc)` on successful login. | `routers/auth.py:79` | 5 min |

### Phase P2 — Transparency & hardening

| # | Task | Files | Effort |
|---|---|---|---|
| P2.1 | **Cookie notice.** A minimal, non-blocking banner stating that a strictly-necessary session cookie is used (no consent modal needed since no non-essential cookies are set). Link to `/privacy`. | new `partials/cookie_notice.html`, `base.html` | 1 h |
| P2.2 | **Data retention policy.** Document retention (e.g., data kept while account active; deleted on account deletion; logs 7 days; session 14 days). Optionally add a cron to purge dormant accounts. | `privacy.html` content | 0.5 h |
| P2.3 | **Lock down `/docs` & `/redoc`** behind auth or disable in production (`docs_url=None` when `not is_development`). | `main.py` | 10 min |
| P2.4 | **Breach-notification runbook.** Add a short `SECURITY.md` or section in `deployment.md` covering the 72-hour rule, who to contact, and log-review steps. | `deployment.md` or new `SECURITY.md` | 1 h |
| P2.5 | **Lightweight DPIA.** One-page risk assessment for financial-data processing (threats, likelihood, mitigations already in place). | new `docs/dpia.md` | 1 h |
| P2.6 | **Self-host CDN assets (optional but recommended).** Vendor HTMX/Alpine/Chart.js locally to remove the unpkg/jsdelivr third-party request (reduces processor surface + faster). | `static/vendor/`, `base.html` | 1 h |

### Phase P3 — Nice-to-have / v2

- Age-gate statement + under-16 handling (Art. 8).
- Per-field rectification UI for profile (name) beyond what Google provides.
- Webhook/event log for DSAR requests (audit trail).
- Regional data residency options if EU users demand EU-only storage.

---

## 4. TO-DO: Add a Privacy Policy to the app

> **Status: ☐ not started.** This is the headline item from the launch checklist
> (§1) and the top remediation task (P0.1). Until this ships, the app is **not
> GDPR-compliant** for a public launch.

### Deliverables

1. **New template:** `backend/app/templates/privacy.html` — extends `base.html`,
   renders the policy in §5 below. Should be reachable **without authentication**
   (it's a transparency document; prospects/visitors must read it pre-login).
2. **New route:** `GET /privacy` in `backend/app/routers/pages.py` — **no
   `get_current_user` dependency** so anonymous visitors can view it.
3. **Fix dead links:** in `login.html` change `Privacy Policy` href from `#` to
   `/privacy`. Either create a minimal `/terms` stub or remove the ToS link.
4. **Footer link:** add a "Privacy" link to the footer in `base.html` so the
   policy is reachable from every authenticated page.
5. **Config:** add `FF_PRIVACY_EMAIL` / `FF_SUPPORT_EMAIL` to `config.py` and
   `.env.example`; reference it in the policy's "Contact" section instead of
   hard-coding an address.
6. **Policy content:** use the draft in §5. Fill the `{{ app_name }}`,
   `{{ privacy_email }}`, effective-date, and processor list placeholders against
   the real deployment (Render region, Neon region, etc.).
7. **Effective-date + changelog:** keep a "Last updated" line at the top of the
   policy and a short changelog at the bottom; bump the date whenever the policy
   or processing changes (GDPR requires informing users of material changes).
8. **Tests:** add `tests/test_privacy.py` — `GET /privacy` returns 200
   unauthenticated, contains key sections ("What we collect", "Your rights",
   "Contact"), and the `login.html` link points at `/privacy`.

### Acceptance criteria

- [ ] `GET /privacy` returns 200 for an anonymous (logged-out) request.
- [ ] `login.html` "Privacy Policy" link resolves to `/privacy` (not `#`).
- [ ] Footer on every page links to `/privacy`.
- [ ] Policy lists every third-party processor actually used.
- [ ] Policy states lawful basis, retention, user rights, and a contact email.
- [ ] `pytest` green; `ruff check .` clean.

---

## 5. Draft Privacy Policy (content for `privacy.html`)

> Replace `{{ ... }}` placeholders with real values before publishing.
> Effective date should be the launch date. Keep the "Last updated" line current.

```markdown
# Privacy Policy

**Last updated:** {{ YYYY-MM-DD }}
**Applies to:** {{ app_name }} (the "Service"), operated by Monu Thomas
("we", "us", or "our").

This Privacy Policy explains what personal data we collect, why we collect it,
how we use it, who has access to it, and the rights you have over it. By using
{{ app_name }}, you agree to the practices described here.

## 1. Who we are

{{ app_name }} is a personal expense-tracking web application operated by
Monu Thomas. For any privacy question or data request, contact us at
**{{ privacy_email }}**.

We are the **data controller** for the personal data you submit through the
Service.

## 2. What personal data we collect

| Category | Examples |
|---|---|
| Account / identity | Your Google email address, display name, and a stable Google account identifier (`sub`). |
| Financial data you enter | Account names/types/balances, transactions (amounts, dates, descriptions, notes), categories, budgets, and recurring rules. |
| Usage / technical | Request method, path, HTTP status, request ID, and duration — recorded in server logs for security and reliability. |
| Cookies | A single strictly-necessary session cookie that keeps you signed in. |

We **do not** collect: payment card numbers, bank login credentials, government
IDs, biometric data, precise geolocation, or marketing-tracking data. We never
sell your data.

## 3. How we get your data

- **Identity data** is obtained from Google when you sign in with Google
  (OAuth scope: `openid email profile`).
- **Financial data** is provided by you directly when you create accounts,
  transactions, budgets, etc.
- **Technical/log data** is generated automatically by the server on each
  request.

## 4. Why we use your data — lawful basis

We process your personal data on the following lawful bases under the GDPR:

| Purpose | Data | Lawful basis |
|---|---|---|
| Provide the expense-tracking Service you signed up for | Identity + financial data | **Contract** (Art. 6(1)(b)) — necessary to deliver the service you requested. |
| Keep you signed in securely | Session cookie + identity | **Contract**. |
| Detect abuse, debug errors, keep the Service reliable | Technical/log data | **Legitimate interest** (Art. 6(1)(f)) — security and stability. |
| Create your account on first sign-in | Google identity | **Contract** — taking steps before entering the contract. |

We do **not** rely on consent for core processing, and we do **not** perform
profiling or automated decision-making with legal effects.

## 5. Third parties who process your data

We use the following service providers ("processors"). Each may access limited
personal data only to deliver their service to us.

| Provider | Role | Data accessed | Location |
|---|---|---|---|
| **Google LLC** | Authentication (Google Sign-In) | Email, name, account ID | United States (Google) |
| **{{ hosting_provider, e.g. Render }}** | Web hosting | All data processed by the app | {{ region }} |
| **{{ db_provider, e.g. Neon }}** | Managed database | All stored app data | {{ region }} |
| **unpkg.com / jsdelivr.com** | CDN for front-end libraries (HTMX, Alpine.js, Chart.js) | IP address (as with any HTTP request); no account data | Global / US |

We do not transfer your data to any other third party, and we never sell it.

**International transfers.** Because Google and the CDN providers operate from
the United States (and other regions), your data may be transferred outside the
EU/EEA. We rely on the EU–US Data Privacy Framework (where the provider is
certified) and Standard Contractual Clauses as appropriate safeguards, together
with the technical measures described in §7.

## 6. How long we keep your data

| Data | Retention |
|---|---|
| Your account + financial data | Until you delete your account (see §8). |
| Server logs | ~7 days (hosting-provider retention). |
| Session cookie | 14 days of inactivity, then it expires. |
| Database backups | 7 days point-in-time recovery (provider-managed). |

You can request earlier deletion at any time (§8).

## 7. Security

We protect your data with: HTTPS/TLS for all traffic; signed, `HttpOnly`,
`Secure`, `SameSite` session cookies; per-user data isolation (you can only ever
see your own data); parameterized database queries; secrets stored as encrypted
hosting-provider environment variables (never in the source code); and
database backups with point-in-time recovery. No method of transmission or
storage is 100% secure, but we apply industry-standard safeguards.

## 8. Your rights (GDPR)

You have the following rights regarding your personal data:

- **Access** — request a copy of the data we hold about you.
- **Rectification** — correct inaccurate data.
- **Erasure** — request deletion of your account and all associated data
  ("right to be forgotten").
- **Restriction / objection** — ask us to limit or stop certain processing.
- **Data portability** — receive your data in a structured, machine-readable
  format (JSON/CSV).
- **Withdraw consent** — not applicable to core processing (which relies on
  contract / legitimate interest, not consent), but you can sign out at any time.
- **Lodge a complaint** with your local data-protection authority (e.g.,
  <https://edpb.europa.eu/>).

To exercise any right, email **{{ privacy_email }}**. We respond within
30 days. You can also delete your account directly from the app's
**Settings → Delete account** action.

## 9. Cookies

The Service uses a **single strictly-necessary session cookie** to keep you
signed in. This cookie is essential to the Service and is **not** used for
tracking or advertising. Because it is strictly necessary, no consent banner is
required, but we inform you about it here. The cookie is cleared when you sign
out or after 14 days of inactivity. We do not use third-party tracking,
analytics, or advertising cookies.

## 10. Children's data

The Service is not directed to children under 16. We do not knowingly collect
data from anyone under 16. If you believe a minor has provided us with personal
data, contact us and we will delete it.

## 11. Changes to this policy

We may update this policy from time to time. We will notify you of material
changes (e.g., new processing or new processors) via the app or by email. The
"Last updated" date at the top always reflects the current version.

## 12. Contact

For privacy questions, data requests, or to exercise any right above, contact:

**{{ privacy_email }}**

### Changelog
- {{ YYYY-MM-DD }} — Initial version published with the launch of {{ app_name }}.
```

---

## 6. Quick-reference: data-flow map (for the DPIA / Art. 30 record)

```
User (browser)
   │  HTTPS (Render terminates TLS)
   ▼
Render web service (FastAPI container)  ── logs (stdout, 7-day) ──▶ Render log viewer
   │
   ├── Google OAuth (accounts.google.com)  ◀── email, name, sub  (US)
   │
   ├── CDN assets (unpkg / jsdelivr)  ◀── IP only (no account data)  (US/global)
   │
   ▼
Neon Postgres (managed DB)  ◀── all stored app data  ({{ region }})
   │
   └── PITR backups (7-day) + weekly pg_dump artifacts (90-day)
```

---

## 7. Summary

The app's **technical security posture is strong** (isolation, TLS, secure
cookies, secrets out of repo, validation). The **gap is legal transparency**:
no privacy policy, no user-facing data-rights tooling, and undisclosed
processors. Shipping the Privacy Policy (§4 to-do) plus the P1 data-rights
features (account deletion + export) closes the highest-severity GDPR findings
(F1–F3, F5, F7) and brings Filoos to a launch-ready privacy baseline.
