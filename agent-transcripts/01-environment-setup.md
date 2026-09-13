# Incident 01 — Environment setup: Postgres/pgvector and macOS threading bug

## Context

No Docker runtime was installed on the build machine, so PostgreSQL + pgvector were set up
natively via Homebrew for real local verification, rather than relying entirely on
`docker compose` (which was still built and written correctly for evaluators who do have Docker,
but couldn't be smoke-tested end-to-end here).

## Failure 1 — pgvector built against the wrong Postgres version

**What happened:** `brew install postgresql@16 pgvector` succeeded, but connecting and running
`CREATE EXTENSION vector;` failed:

```
ERROR:  could not open extension control file
"/opt/homebrew/share/postgresql@14/extension/vector.control": No such file or directory
```

**Root cause:** the machine already had `postgresql@14` linked as the active Homebrew Postgres
(pre-existing, used by other projects on the machine). Homebrew's `pgvector` formula depends on
the *unversioned* `postgresql` formula, which at install time resolved to `postgresql@17`/`@18` -
not the `postgresql@16` this project had just installed. pgvector's compiled `.dylib` and control
files ended up under `postgresql@17`/`@18`'s share directory, matching neither the pre-existing
`@14` nor the newly-installed `@16`.

**Fix:** uninstalled the mismatched `postgresql@16`, restored `postgresql@14` as the machine's
default link (so other pre-existing projects on the machine were left untouched), and installed
`postgresql@17` instead - the version pgvector was actually built against - as a dedicated,
unlinked instance for this project only.

## Failure 2 — "postmaster became multithreaded during startup"

**What happened:** starting the dedicated Postgres 17 cluster failed outright:

```
FATAL:  postmaster became multithreaded during startup
HINT:  Set the LC_ALL environment variable to a valid locale.
```

This happened both with and without TCP listening enabled, ruling out a port/DNS-resolution
theory first.

**Root cause:** a known interaction on recent macOS builds where Postgres's startup-time
safety check (added to prevent unsafe `fork()` after threads have started) trips due to
locale/ICU initialization spawning a thread when no explicit `LC_ALL` is set.

**Fix:** exactly as the HINT said - setting `LC_ALL=en_US.UTF-8` (and `LANG`) before starting
`pg_ctl` resolved it immediately. Documented in the README's native-run troubleshooting section
so a future evaluator hitting the same thing on macOS doesn't have to re-derive it.

## Outcome

Ended up with a dedicated Postgres 17 + pgvector 0.8.6 instance on port 5544 (`postgresql://
postgres:lenny_dev_password@127.0.0.1:5544/lenny_growth_assistant`), isolated from the machine's
pre-existing `postgresql@14` service, used for every subsequent verification step in this build
(migrations, ingestion, retrieval, the full API test suite, and manual browser testing).
