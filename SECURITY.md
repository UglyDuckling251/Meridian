# Security Policy

## Supported Versions

As Meridian is in early development, only the latest version on the `main` branch is supported with security updates.

| Version       | Supported |
|---------------|-----------|
| Latest `main` | Yes       |
| Older commits | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in Meridian, please report it responsibly. **Do not open a public issue.**

Instead, please email the maintainer directly at: **xxx**

Include as much detail as possible:

- A description of the vulnerability and its potential impact.
- Steps to reproduce the issue.
- Any relevant logs, screenshots, or proof-of-concept code.

You can expect an acknowledgment within **72 hours** and a resolution or status update within **14 days**.

## Scope

Meridian is a local desktop application. Security concerns most relevant to this project include:

- **Arbitrary code execution** through maliciously crafted ROM files or metadata.
- **Path traversal** in ROM directory scanning or file handling.
- **Dependency vulnerabilities** in third-party Python packages.

We take all reports seriously and appreciate your help in keeping Meridian safe for everyone.
