# APL Demo Relay (P1 prototype)

**Not part of the P0 offline demo.** This is the reference control plane for
[docs/hosted_live_demo.md](../docs/hosted_live_demo.md): scenario allowlist,
per-IP/per-session rate limits, input length limit, daily cost cap, provider
pool config, and mock fallback.

```bash
python relay/relay_server.py   # loopback prototype on :8792
```

- The pool ships with **mock entries only**; live entries are examples,
  disabled, and reference credentials by env-var NAME only.
- The prototype serves curated mock answers in both modes; a production
  deployment swaps the pool call in at the marked point.
- No raw input storage; responses carry operational metadata only.
- Production additions: TLS, real client-IP extraction, durable counters,
  CAPTCHA, deployment target.
