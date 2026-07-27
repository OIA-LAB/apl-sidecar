# Local Playground

```bash
apl playground
# then open http://127.0.0.1:8791/app/local_playground/
```

- Loopback only; the server refuses nothing because it never leaves 127.0.0.1.
- Loads the two example fixtures from this repo. Zero network calls.
- The Verify buttons run REAL verification in your browser: canonical-JSON
  hash recomputation + Ed25519 via WebCrypto, against the repo demo public
  key in `spec/`. The tampered receipt must fail.
- If your browser lacks WebCrypto Ed25519 (older browsers), the playground
  says so and points you to `apl verify`.
