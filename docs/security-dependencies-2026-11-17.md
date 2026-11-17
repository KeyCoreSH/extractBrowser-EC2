# Security dependency maintenance — 2026-11-17

Updated Flask, Flask-CORS, python-multipart, Gunicorn, Requests, python-dotenv and Werkzeug to patched releases. Werkzeug 3.1.9 also addresses an additional advisory found during the post-update audit.

Validation in an isolated Python 3.11 environment:
- Dependency installation and compatibility check passed.
- Four offline HTTP smoke tests passed: health/CORS, JSON login/session, form login, authentication and empty uploads.
- Existing prompt-generation smoke checks and Python compilation passed.
- `pip-audit` of the installed environment reported no known vulnerabilities.

Run `python -m unittest discover -s tests -v` for the added regression checks. They create a temporary database and mock AWS/OpenAI clients. Real document extraction against AWS/OpenAI and production deployment were not executed. The audit result is a dated dependency snapshot, not a complete application security guarantee.
