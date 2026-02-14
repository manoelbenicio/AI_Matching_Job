# OPUS 4.6 — Consolidated Review Report

**Reviewer:** Antigravity  
**Date:** 2026-02-14  
**Sources reviewed:** `OPUS46_COPY_PASTE_PROMPT.md` + `OPUS46_HANDOFF.md`  
**Cross-checked against:** actual source code

---

## 1 — VERIFICATION RESULTS

Every Q1–Q4 claim in the handoff docs was **confirmed in the actual code**.  
No phantom claims. No missing implementations. All 7 workstreams coherent.

- ✅ **Q1 Freeze** — `cv_enhancer.py` isolated, not wired to runtime
- ✅ **Q2 Backend** — Prompt has `fit_assessment_label` + `gap_analysis` (scoring.py L539-551)
- ✅ **Q2 Frontend** — Uses AI signal directly (score-breakdown-tab.tsx L61-64)
- ✅ **Q3 KPI** — `dataRefreshVersion` in store + metrics-bar refetches
- ✅ **Q4 Gate** — `_validate_enhancement_for_export` active on 3 routes
- ✅ **Groq** — Provider + multi-key + failover chain all wired
- ✅ **3 Keys** — `.env` configured, comma-separated

---

## 2 — OPEN RCAs (4 items to fix)

---

### P0 — RCA-010 — Compare fallback missing Groq

- **Where:** `jobs.py` line 165
- **Problem:** Fallback only checks `("openai", "gemini")`, ignores `groq`
- **Fix:** Add `"groq"` to front of tuple
- **Effort:** 5 minutes, 1 line
- **Risk:** None

```python
# BEFORE:
first = next((k for k in ("openai", "gemini") if ...))

# AFTER:
first = next((k for k in ("groq", "openai", "gemini") if ...))
```

---

### P1 — RCA-008 — Integration test fixtures broken

- **Where:** `tests/test_cv_integration.py`
- **Problem:** Test fixtures lack required sections (e.g. `contact_information`)
- **Why:** Q4 gate now blocks exports with missing sections — tests weren't updated
- **Fix:** Add real section payloads to test fixtures
- **Effort:** 30 minutes
- **Risk:** Low (test-only change)

---

### P1 — RCA-007 — Enhancement test contract drift

- **Where:** `tests/test_cv_enhancer.py`
- **Problem:** Tests expect positional `_max_tokens`, code uses keyword `max_tokens=`
- **Why:** Enhancement is frozen — tests were written for future redesign
- **Recommended fix:** Skip tests with `@pytest.mark.skip("enhancement frozen")`
- **Effort:** 5 minutes
- **Risk:** None — enhancer is frozen anyway

---

### P2 — RCA-009 — Semantic export v2 not built yet

- **Where:** `premium_export.py`
- **Problem:** `_walk_html_to_docx` doesn't exist yet
- **Why:** v2 tests were written ahead of implementation
- **Recommended:** Defer. Current export path works fine.
- **Effort:** 2-4 hours when ready
- **Risk:** Medium (new code path)

---

## 3 — RESOLVED RCAs (6 items — all verified)

- **RCA-001** — Groq provider + failover chain → Confirmed in code
- **RCA-002** — Test default changed to `groq` → Pass
- **RCA-003** — `cv_enhancer.py` isolated → Confirmed
- **RCA-004** — Static interview override removed → Confirmed at L61-64
- **RCA-005** — Export quality gate active → Confirmed on 3 routes
- **RCA-006** — AI probability prioritized, fallback only if absent → Confirmed at L196-200

---

## 4 — HISTORICAL RCAs (7 items — all frozen by design)

All are part of the enhancement redesign stream.  
Intentionally frozen per Q1 decision. No action needed until redesign.

- **HIST-001** — CV truncation (single Gemini call limit)
- **HIST-002** — Monolithic prompt overload
- **HIST-003** — Semantic loss in export (HTML stripped)
- **HIST-004** — Weak output validation
- **HIST-005** — Scoring-enhancement disconnect
- **HIST-006** — Config-driven failures (SMTP, Drive, scheduler)
- **HIST-007** — Environment port overlap risk

---

## 5 — TEST SUITE STATUS

**Current:** 58 passed / 17 failed / 2 skipped

**After P0 + P1 fixes (expected):**

- ~70 passed
- ~5 failed (v2 semantic tests only)
- 2 skipped

---

## 6 — DECISIONS NEEDED FROM YOU

1. **Skip enhancer tests?**  
   Recommendation: YES. Fixing tests for frozen code is wasted work.

2. **Build semantic walker now or later?**  
   Recommendation: LATER. Current export works. Do it in redesign phase.

3. **OK with ~5 test failures until redesign?**  
   Recommendation: YES. All 5 are v2 tests for code that doesn't exist yet.

---

## 7 — EXECUTION ORDER

```
Step 1: Fix jobs.py L165 — add "groq" to compare fallback    (5 min)
Step 2: Fix test_cv_integration.py fixtures                   (30 min)
Step 3: Skip test_cv_enhancer.py tests                        (5 min)
Step 4: Run pytest tests -q → confirm ≤5 failures            (2 min)
Step 5: Run npm run build → confirm frontend clean            (1 min)
Step 6: UAT — score a real job, check AI labels render        (manual)
```

---

## 8 — RISKS NOT IN SOURCE DOCS

1. **Groq rate limits** — 3 keys may not be enough under load  
   → Failover to gemini/openai already works

2. **Old jobs lack new fields** — Pre-Q2 jobs won't show fit labels  
   → Frontend handles gracefully (empty string fallbacks)

3. **API keys in plaintext `.env`** — Security risk if repo leaked  
   → Verify `.gitignore` includes `.env`

4. **Enhancement redesign scope creep** — Frozen artifact may go stale  
   → Time-box redesign decision to 1 week
