# OPUS 4.6 - Final Architecture Prompt (Consolidated)

Last update: 2026-02-14  
Prepared by: Codex  
Project: AI Job Matcher

## 1) Objective

Close all open technical doubts and approve a final architecture path to ship fast and safely.

Business priority:
- Groq must be primary provider (zero-cost preference).
- OpenAI must be backup (paid, lower priority).
- System must support high volume (10k+ jobs) with stable scoring and predictable behavior.
- CV Enhancement stream is under redesign and should not receive ad-hoc hotfixes outside approved plan.

---

## 2) Current Delivered Scope (Implemented)

### 2.1 Groq as primary scoring provider
- Added Groq provider support in backend scoring.
- Default single-score provider changed to `groq`.
- Fallback chain for Groq flow:
  - `groq` -> `gemini` -> `openai`
- Explicit `openai` or `gemini` selection still runs directly (no forced fallback chain).

### 2.2 Multi-key Groq rotation
- Added `GROQ_API_KEYS` as comma-separated key storage.
- Added helper to parse and rotate keys in round-robin.
- Added per-key cooldown and per-key pacing controls.

### 2.3 Settings and observability
- Added Groq fields to settings API response:
  - key count
  - masked key previews
- Added save support for `groq_api_keys`.
- Added endpoint: `POST /settings/test-groq` (validates all configured keys).

### 2.4 Frontend integration
- Settings modal now includes Groq as first-class provider.
- Input supports comma-separated keys.
- Added "Test All Keys" action.
- Status badges show Groq key count.

### 2.5 Validation executed
- Backend compile: pass
- Frontend build: pass
- Scoring contract test updated to Groq default: pass

---

## 3) Confirmed Technical Position

1. Groq replacing OpenAI as primary is already implemented and active by default.
2. OpenAI is now backup in the Groq failover path.
3. This aligns with cost strategy: free first, paid fallback only.

---

## 4) Open Questions for Opus 4.6 (Decision Required)

### Q1 - Enhancement redesign stream freeze policy
Current state:
- User requested no further enhancement-system modifications while redesign is in progress.
- There is a standalone file `backend/app/services/cv_enhancer.py` not yet wired to production flow.

Decision needed:
- A) Keep file as redesign artifact (not used in runtime) until architecture approval.
- B) Remove file now for strict freeze hygiene.

Recommended:
- A (keep), but explicitly mark as "experimental/not in runtime path".

### Q2 - Chance label coherence vs score
Observed issue from user:
- Cases like score 85 shown with "Medium Chance" are perceived as incoherent.

Decision needed:
- Approve a single deterministic mapping policy (score -> chance label) with exact thresholds.

Recommended baseline:
- 0-59: Low
- 60-79: Medium
- 80-100: High

### Q3 - Fit Score KPI source of truth
Observed issue from user:
- Top KPIs and detail panel can diverge after scoring/enhancement.

Decision needed:
- Define canonical source and refresh protocol:
  - job-level score source
  - enhancement fit source
  - event-driven UI refresh after each action

Recommended:
- Use backend persisted values only (no local derived fallback for final display).

### Q4 - Enhancement export quality gate
Observed issue from user:
- DOCX/HTML exports may contain malformed payload artifacts if enhancement payload shape is unexpected.

Decision needed:
- Enforce strict normalization + reject-on-invalid before export.

Recommended:
- Add hard gate:
  - required sections present
  - no JSON wrapper leakage
  - semantic HTML validation pass

---

## 5) Architecture Risks and Mitigations

### R1 - Rate limit exhaustion on Groq keys
Mitigation:
- Conservative pacing, per-key cooldown, round-robin across keys.
- Fallback to Gemini/OpenAI when Groq is rate-limited.

### R2 - Configuration drift (keys and providers)
Mitigation:
- Single settings endpoint as source of truth.
- Health/test endpoints per provider.
- Explicit UI state with key count + validation result.

### R3 - Enhancement instability (known stream)
Mitigation:
- Keep redesign isolated.
- No partial hotfixes without architecture sign-off.
- Promote only when contract tests and export tests pass end-to-end.

---

## 6) Recommended Final Plan (ASAP Closure)

### Phase A - Ship scoring provider migration (now)
- Keep Groq default in production.
- Keep OpenAI as fallback only.
- Run smoke test:
  - settings save + test-groq
  - single score with Groq
  - forced fallback test

### Phase B - Freeze and formalize enhancement redesign
- Lock current enhancement code path.
- Approve architecture from `docs/CV_ENHANCEMENT_SYSTEM_PLAN.md`.
- Implement redesign behind feature flag.

### Phase C - Go-live criteria
- All scoring contract tests green.
- Provider failover verified.
- KPI coherence checks pass.
- Enhancement/export path validated on agreed test cases.

---

## 7) Definition of Done (Project Closure)

Project considered closed when:
1. Groq primary + backup chain is stable in production.
2. No unresolved contract mismatches in tests.
3. KPI and chance labels are coherent and deterministic.
4. Enhancement redesign path is approved, tested, and released (or explicitly moved to next release cycle with owner sign-off).
5. RCA and status documentation is complete and current.

---

## 8) References

- `docs/OPUS46_HANDOFF.md` (current status + RCA ledger)
- `docs/CV_ENHANCEMENT_SYSTEM_PLAN.md` (enhancement redesign technical plan)
- `docs/STATUS_REPORT_360.md` (historical project status)
- `docs/OPERATIONS_GUIDE.md` (runbook and troubleshooting)

