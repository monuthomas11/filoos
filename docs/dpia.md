# Lightweight DPIA for Filoos

## Overview

Filoos processes personal and financial data for account and transaction management. The app stores identity data from Google sign-in, financial records entered by the user, and limited technical logs needed for reliability and abuse detection.

## Risks

- Unauthorized access to a user account or the underlying database.
- Accidental disclosure of financial records through logs or misconfigured access.
- Over-retention of data after account deletion or inactivity.

## Mitigations already in place

- Per-user data isolation through user-scoped queries.
- HTTPS/TLS, secure session cookies, and trusted-host protection.
- Secrets stored in environment variables rather than source code.
- Structured logs that avoid logging request bodies and personal data.
- Database backups with point-in-time recovery.

## Residual risk and review

Residual risk is low for a personal finance app, but the service should continue to review access controls, retention periods, and incident response procedures as usage grows.
