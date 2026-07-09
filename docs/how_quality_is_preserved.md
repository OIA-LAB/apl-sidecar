# How Answer Quality Is Preserved

Masking that destroys the task produces useless answers. APL's masking model
is about **keeping the task signal while dropping the sensitive specifics**.

## The bad pattern

```
I want to build [REDACTED] for [REDACTED] using [REDACTED].
```

Nothing useful can come back from that.

## The preferred pattern

Preserve abstract task signals:

- task type ("position an early developer tool");
- target class ("GitHub users", not the actual customer);
- desired output format ("README structure", "bug fix + test");
- constraints ("privacy-sensitive", "no account required");
- quality criteria ("earn trust", "reproducible").

Keep sensitive specifics local:

- the exact product idea;
- the project name;
- the real target customer;
- the secret mechanism;
- pricing;
- roadmap.

## Core product statement

> APL Sidecar P0 demonstrates how sensitive AI tasks can preserve useful task
> signals while reducing full-context exposure.

The two flagship examples each show this concretely: the provider payloads are
real, answerable questions — and the rehydrated final answer shows how the
local-only specifics are reintroduced on your machine, not theirs.
