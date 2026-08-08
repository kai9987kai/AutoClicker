# Security Policy

We take the security of our software seriously. If you believe you have found a security vulnerability, please report it to us as soon as possible so we can investigate and address it responsibly.

## Supported Versions

We provide security updates for the following versions:

| Version | Supported |
| ------- | --------- |
| V11.0   | ✅        |
| V10.1   | ✅        |
| V10.0   | ❌        |
| < V10   | ❌        |

Only the versions marked as supported will receive security fixes.

## Reporting a Vulnerability

Please report security vulnerabilities privately through
[GitHub Security Advisories](https://github.com/kai9987kai/AutoClicker/security/advisories/new)
on this repository. That keeps the report private until a fix is available.

Include as much detail as possible, such as:

- A description of the issue
- Steps to reproduce the vulnerability
- Any affected versions
- Proof of concept code, screenshots, or logs if available
- The potential impact of the issue

We ask that you do not publicly disclose the vulnerability until we have had a reasonable opportunity to investigate and respond.

## What to Expect

After receiving a report, we will:

- Acknowledge receipt within **5 business days**
- Review and validate the issue
- Provide a status update within **10 business days**
- Fix confirmed vulnerabilities in a future release or issue a mitigation if needed

If the report is accepted, we will work to remediate it as quickly as reasonably possible based on severity and impact.

If the report is declined, we will explain why, when appropriate.

## Responsible Disclosure

We appreciate responsible disclosure practices and ask that reporters:

- Avoid accessing, modifying, or deleting data that does not belong to them
- Avoid disruptive testing against production systems
- Avoid public disclosure until a fix is available or we have agreed on a disclosure timeline

## Scope

This policy applies to security issues in the main project codebase and officially supported releases.

This project automates mouse and keyboard input on the local machine. Reports about it
*being able* to send input are out of scope — that is the entire purpose of the tool.
In-scope examples include: code execution from a crafted profile, recording or sequence
file; secrets written to disk or into a support bundle; and a run that cannot be stopped
by the documented stop controls.

Issues in unsupported versions may be reviewed on a best-effort basis, but security fixes are not guaranteed.

## Recognition

With your permission, we may acknowledge security researchers who responsibly report valid issues.

Thank you for helping keep this project secure.
