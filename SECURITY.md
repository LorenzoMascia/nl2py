# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within NL2Py, please follow these steps:

### Do NOT

- Open a public GitHub issue for security vulnerabilities
- Disclose the vulnerability publicly before it has been addressed

### Do

1. **Email the maintainers** with details about the vulnerability
2. Include the following information:
   - Type of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Initial Assessment**: Within 7 days
- **Resolution Timeline**: Depends on severity, typically 30-90 days
- **Credit**: We will credit you in the release notes (unless you prefer anonymity)

## Security Best Practices

When using NL2Py:

### Configuration Files

- Never commit `nl2py.conf` to version control
- Use environment variables for sensitive credentials
- Keep configuration files with restricted permissions (chmod 600)

### API Keys and Secrets

```ini
# BAD - hardcoded in code
api_key = "sk-1234567890"

# GOOD - use environment variables
api_key = ${AWS_ACCESS_KEY_ID}
```

### Running in Production

- Use dedicated service accounts with minimal permissions
- Enable audit logging where available
- Regularly rotate credentials
- Use secret management tools (Vault, AWS Secrets Manager, etc.)

### Module-Specific Security

| Module | Security Considerations |
|--------|------------------------|
| AWS/GCP/Azure | Use IAM roles instead of access keys when possible |
| Database modules | Use read-only credentials for query-only operations |
| SSH | Use key-based authentication, avoid password auth |
| Vault | Enable TLS, use AppRole for automation |
| JWT | Use strong secrets, short expiration times |

## Known Security Considerations

### Code Generation

NL2Py generates Python code from natural language. This code should be:
- Reviewed before execution in production
- Not used with untrusted user input without sanitization
- Executed in sandboxed environments when possible

### Credential Handling

The configuration file (`nl2py.conf`) may contain sensitive credentials:
- This file is gitignored by default
- Use the `.example` version as a template
- Never share configuration files containing real credentials

## Security Updates

Security updates will be released as patch versions (e.g., 0.1.1, 0.1.2).

Subscribe to GitHub releases to be notified of security updates.
