---
topic: [agent-security]
id: root-security-posture-baseline
title: Security Posture Baseline — Approved-Safe Expected Values
record_type: reference
desk: root
area: security
status: active
created_at: 2026-06-18
updated_at: 2026-06-18
---

# Security Posture Baseline

> Records the **approved-safe expected value** for each of the 12 posture surfaces this
> port carries forward (of the donor's original 13 — see check 9 below for the one dropped).
> A future change in any surface should be a *deliberate commit to this file* — the
> scanner diffs against these values. If a value changes without a commit here, that
> is drift, not a planned update.
>
> Established 2026-06-18 from the scoping-pass findings in the donor system's
> `state/projects/dashboard/helm/records/2026-06-18-bucket3-scoping.md` (B6 section) — ⛔ that
> record was never ported (helm is operator-personal, see the cowork-migration triage); named
> here only for provenance, not as a live citation into this repo.
> All 13 surfaces were APPROVED_SAFE at baseline establishment in the donor system.

## 1. hook-registration

**Check:** All `.sh` paths registered in `~/.claude/settings.json` hooks must exist on disk.

**Approved-safe baseline (2026-06-18):** 21 hook paths registered in the donor system, all
existing in that clone's own copy of `system/hooks/` ✅ (this repo has its own `system/hooks/`
too, but the 21-count itself is donor-specific and has not been re-baselined post-port — treat
the current scan's own count as the working baseline until someone commits a fresh one here).

**What triggers DRIFT:** Any registered hook path that no longer exists on disk.

---

## 2. hook-file-integrity

**Check:** `git status --porcelain system/hooks/` on the clone must be clean.

**Approved-safe baseline (2026-06-18):** Output is empty — all hook files committed, no
uncommitted modifications or untracked files.

**What triggers DRIFT:** Any uncommitted edit to a hook file (modified/added/deleted vs HEAD).

---

## 3. helm-bind-address

**Check:** The Helm server on port 8080 must be bound to `127.0.0.1`, never `0.0.0.0`.

**Approved-safe baseline (2026-06-18):** `127.0.0.1:8080` (pid 6825). Process is a Python
process — Helm's `server.py`.

**What triggers DRIFT:** Port 8080 bound to `0.0.0.0` or `*` (exposed beyond localhost).

---

## 4. tailscale-serve

**Check:** `tailscale serve status` must return `No serve config`.

**Approved-safe baseline (2026-06-18):** Output is exactly `No serve config` — nothing
is exposed via Tailscale Serve/Funnel.

**What triggers DRIFT:** Any non-empty serve configuration appearing.

---

## 5. mcp-surface

**Check:** `claude_desktop_config.json` mcpServers must be `{}`, and no `.mcp.json` must
exist in the Drive ClaudeOps root.

**Approved-safe baseline (2026-06-18):** `mcpServers: {}` in claude_desktop_config.json.
No `.mcp.json` in Drive root. The Asana/Gmail/Google Calendar/Drive tools visible in
Claude Code are **claude.ai native integrations**, NOT local MCP servers — they do not
appear here.

**What triggers DRIFT:** Any non-empty mcpServers dict, or a `.mcp.json` appearing in Drive root.

---

## 6. obsidian-brain-pin

**Check:** `npx obsidian-brain --version` must return `1.7.24`.

**Approved-safe baseline (2026-06-18):** Version `1.7.24`. The read-only deny list in
`settings.json` was audited against this exact version's tool set. Bumping the pin
requires re-auditing the registered tools (a new version could add a vault-write tool
not yet in the deny list).

**What triggers DRIFT:** Any version other than `1.7.24`.

---

## 7. gws-cred-isolation

**Check:** `~/.config/gws-cron` must exist AND must resolve to a different real path
than `~/.config/gws`.

**Approved-safe baseline (2026-06-18):** Both directories exist at distinct real paths.
The isolation prevents a cron-path gws failure from touching or deleting the interactive
`~/.config/gws/credentials.enc` (the keychain-backed creds that every window uses).

**What triggers DRIFT:** `gws-cron` absent, or symlinked / hardlinked to point at the
same underlying directory as `gws`.

---

## 8. launchd-bootstrap

**Check:** `launchctl list` must include `ai.claudeops.bootstrap`.

**Approved-safe baseline (2026-06-18):** `ai.claudeops.bootstrap` listed (PID `-`, which
is normal for a periodic launchd job that is not currently running).

**What triggers DRIFT:** The label absent from launchctl output (plist was unloaded).

---

## 9. [DROPPED] git-remote

⚖ **PORT NOTE:** the donor's check #9 asserted the clone's own git remote was a PRIVATE repo —
the opposite of what this repo (`~/.claude/skills/ClaudeOps`) is BY DESIGN, since it ships publicly on purpose.
Not portable without hardcoding the operator's own GitHub handle into a public repo, so it was
dropped rather than neutered — see `system/tools/security-posture-scan.sh` ⏳ unruled — not yet ported to this repo, own port note.
The scanner now runs 12 checks, not 13.

---

## 10. settings-self-modify-deny

**Check:** `~/.claude/settings.json` permissions.deny must contain both
`Write(~/.claude/settings.json)` and `Edit(~/.claude/settings.json)`.

**Approved-safe baseline (2026-06-18):** Both deny rules present. This prevents Claude
from overwriting its own constraints — the self-amend attack surface.

**What triggers DRIFT:** Either rule missing from the deny list.

---

## 11. ssh-gpg-aws-deny

**Check:** permissions.deny must include Read/Write/Edit for `~/.ssh/**`, `~/.gnupg/**`,
and `~/.aws/**` (9 rules total).

**Approved-safe baseline (2026-06-18):** All 9 rules present. Verified list:
`Read(~/.ssh/**)`, `Edit(~/.ssh/**)`, `Write(~/.ssh/**)`,
`Read(~/.gnupg/**)`, `Edit(~/.gnupg/**)`, `Write(~/.gnupg/**)`,
`Read(~/.aws/**)`, `Edit(~/.aws/**)`, `Write(~/.aws/**)`.

**What triggers DRIFT:** Any of the 9 rules missing.

---

## 12. pulse-job-state

**Check:** In `system/pulse-config.md`: `emily-breakdown` enabled=`yes`;
`supabase-keepalive` and `supabase-backup` both enabled=`no`.

**Approved-safe baseline (2026-06-18):** emily-breakdown=yes (active ingest pipeline);
supabase-keepalive=no and supabase-backup=no (managed by launchd, disabled in Pulse
to avoid double-execution).

**What triggers DRIFT:** emily-breakdown flipped off (ingest silently dead), or a
supabase job accidentally flipped on (double-execution).

---

## 13. claudeops-perms

**Check:** `~/.config/claudeops` directory perms must be 700 or 750; no file inside
may be world-readable (others-read bit set).

**Approved-safe baseline (2026-06-18):** Directory at 0o700. All files non-world-readable:
`gws-credentials.json` (0o600), `claude-oauth-token` (0o600), `secrets/` (0o700),
state files (0o644 — user+group readable, no others-exec). No world-readable files.

**What triggers DRIFT:** Directory mode changed to 755/777, or any file gaining the
others-read bit (mode & 0o004 != 0).
