# Security and incident response

## Incident handling

If a potential security issue is discovered, contact the maintainer immediately at the privacy/contact address listed in the app privacy policy. The response team should:

1. Acknowledge the report and preserve evidence.
2. Contain the issue by disabling affected access or credentials.
3. Investigate logs, access patterns, and affected data.
4. Notify relevant stakeholders within 72 hours when personal data may have been exposed.
5. Document the fix, remediation steps, and follow-up actions.

## Logging and monitoring

- Review request and application logs for unusual authentication or data-access patterns.
- Confirm that secrets remain in environment variables and are never committed to source control.
- Keep the deployment and database provider dashboards available for incident triage.
