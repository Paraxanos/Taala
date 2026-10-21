# Security policy

Taala is an early beta and has **not been independently security-reviewed**.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's private
vulnerability reporting (the "Report a vulnerability" button under the Security tab of
this repository). We aim to reply within 7 days.

## What is in scope

- The code in `taala/`, including the localhost web page (`taala/web.py`).
- Any way a password could be written to a log, a URL, a file or the network.

## What to keep in mind

- Taala runs locally and sends nothing anywhere. The web page binds to 127.0.0.1 only
  and takes the password in a POST body. Do not expose it to a network or put it behind
  a public host.
- The strength estimate is a model, not a guarantee. A "Strong" result does not mean a
  password is safe.
- Never include a real password in a bug report.
