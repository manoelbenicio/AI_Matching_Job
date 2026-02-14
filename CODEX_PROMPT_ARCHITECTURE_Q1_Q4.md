# Architecture Decisions Q1–Q4 — Implementation Instructions

You are implementing 4 architecture decisions for a Fortune 500-grade AI Job Matcher system. This system uses LLMs to perform deep, 8-dimension analysis of candidate resumes against real job positions. Every decision must reflect that these are **real people's careers** — the system must provide intelligent, contextual, actionable feedback, never static/dumb mappings.

Read each referenced file fully before editing.

---

## Q1 — Enhancement Freeze Policy

### Decision: Keep `backend/app/services/cv_enhancer.py` as an isolated redesign artifact

**Do NOT delete it. Do NOT wire it to any runtime flow.**

### Changes Required

#### `backend/app/services/cv_enhancer.py`
- Add a module-level docstring at the very top:
  ```python
  """
  CV Enhancement Service — REDESIGN IN PROGRESS
  ===============================================
  Status: ISOLATED — Not wired to runtime application flow.
  This module is under active redesign and must NOT be imported
  or called from any route, scheduler, or service until the
  redesign is approved and test suite passes.

  Owner: Architecture team
  Freeze date: 2026-02-14
  """
  ```

#### `backend/app/routes/cv.py`
- Search for any import of `cv_enhancer`. If found, ensure it is ONLY used in explicitly-marked enhancement endpoints, NOT in scoring or general CV retrieval flows.
- If there's any automatic/background call to cv_enhancer, **comment it out** with `# FREEZE: Enhancement redesign in progress — do not auto-invoke`.

No other files should be touched for Q1.

---

## Q2 — AI-Driven Contextual Fit Assessment (CRITICAL FIX)

### The Bug

In `frontend/src/components/detail-panel/score-breakdown-tab.tsx`, lines 61-63:
```tsx
const rawInterview = String(breakdown.interview_probability ?? breakdown.interview_probability_model ?? '').toUpperCase();
const interviewProbability: 'HIGH' | 'MEDIUM' | 'LOW' =
    breakdown.overall_score >= 80 ? 'HIGH' : breakdown.overall_score >= 60 ? 'MEDIUM' : 'LOW';
```

**The AI model generates `interview_probability` based on deep 8-dimension analysis, but the frontend DISCARDS it and replaces it with a dumb static ternary.** This means a candidate with score 72 who has exceptional domain expertise but lacks one certification shows "MEDIUM Chance" — identical to a candidate at 72 who is fundamentally mismatched on experience level. This is unacceptable.

Additionally, the AI prompt already generates `overall_justification` (2-3 sentence summary explaining the overall fit) but the frontend **never displays it**. The user sees a number and a color dot with no explanation of WHY.

### Decision: The "Chance" label and justification MUST come from the AI model itself

### Changes Required

#### 1. `backend/app/routes/scoring.py` — Enhance the `_SYSTEM_PROMPT`

Find the JSON schema section in `_SYSTEM_PROMPT` (around line 504-527). **Replace** the `interview_probability` field and add two new fields:

**Replace:**
```
"interview_probability": "HIGH|MEDIUM|LOW",
```

**With:**
```
"interview_probability": "HIGH|MEDIUM|LOW",
"fit_assessment_label": "A concise 3-8 word contextual label that captures the nature of the fit. Examples: 'Strong Technical Fit — Needs Cloud Certs', 'Excellent Match — Overqualified for Role', 'Partial Fit — Critical Domain Gap', 'Near-Perfect Alignment'. This must NOT be a generic label derived from the score number — it must reflect YOUR specific analytical findings about this candidate-job pair.",
"gap_analysis": {
    "total_gap_percentage": 28,
    "gap_breakdown": [
        {"category": "Technical Skills", "gap_points": 10, "reason": "Missing required AWS and Kubernetes certifications"},
        {"category": "Industry & Domain", "gap_points": 8, "reason": "No direct insurance industry experience, though financial services background is transferable"},
        {"category": "Keywords & ATS", "gap_points": 5, "reason": "Resume lacks 'actuarial', 'underwriting', and 'claims processing' keywords"},
        {"category": "Education", "gap_points": 5, "reason": "Role prefers MBA; candidate has MSc in Computer Science (partial match)"}
    ],
    "improvement_actions": [
        "Priority 1: Obtain AWS Solutions Architect certification (closes 6 of 10 technical gap points)",
        "Priority 2: Add insurance domain terminology to experience descriptions",
        "Priority 3: Complete any LOMA designation for industry credibility"
    ]
}
```

**IMPORTANT:** Keep `interview_probability` as-is (HIGH/MEDIUM/LOW) for backward compatibility. The new `fit_assessment_label` is the contextual label, and `gap_analysis` provides the structured justification.

#### 2. `backend/app/routes/scoring.py` — Update result coercion

Find where the AI response JSON is parsed and the result dict is built (in `_score_job_openai`, `_score_job_groq`, `_score_job_gemini` functions). Ensure `fit_assessment_label` and `gap_analysis` are preserved from the AI response into the result dict. Add fallback defaults:
```python
result["fit_assessment_label"] = parsed.get("fit_assessment_label", "")
result["gap_analysis"] = parsed.get("gap_analysis", {})
```

#### 3. `frontend/src/lib/types.ts` — Update ScoreBreakdown type

Find the `ScoreBreakdown` interface. Add:
```typescript
fit_assessment_label?: string;
gap_analysis?: {
    total_gap_percentage: number;
    gap_breakdown: Array<{
        category: string;
        gap_points: number;
        reason: string;
    }>;
    improvement_actions: string[];
};
```

#### 4. `frontend/src/components/detail-panel/score-breakdown-tab.tsx` — The main fix

**A) Fix the interview probability override (lines 61-63):**

Replace:
```tsx
const rawInterview = String(breakdown.interview_probability ?? breakdown.interview_probability_model ?? '').toUpperCase();
const interviewProbability: 'HIGH' | 'MEDIUM' | 'LOW' =
    breakdown.overall_score >= 80 ? 'HIGH' : breakdown.overall_score >= 60 ? 'MEDIUM' : 'LOW';
```

With:
```tsx
const interviewProbability: string =
    String(breakdown.interview_probability ?? breakdown.interview_probability_model ?? '').toUpperCase() || 'N/A';
const fitLabel = breakdown.fit_assessment_label || '';
const gapAnalysis = breakdown.gap_analysis;
```

**B) Update the hero badge (around line 80-87) — show AI-generated contextual label:**

Replace the badge span with:
```tsx
<div className="score-breakdown__fit-assessment">
    <span
        className={`score-breakdown__interview-badge score-breakdown__interview-badge--${interviewProbability}`}
    >
        {interviewProbability === 'HIGH' && '🟢'}
        {interviewProbability === 'MEDIUM' && '🟡'}
        {interviewProbability === 'LOW' && '🔴'}
        {interviewProbability} Chance
    </span>
    {fitLabel && (
        <span className="score-breakdown__fit-label">{fitLabel}</span>
    )}
</div>
```

**C) Display overall_justification (after the hero card, before section bars):**

Add after the hero `</div>` (around line 88):
```tsx
{breakdown.overall_justification && (
    <div className="score-breakdown__justification">
        <p>{breakdown.overall_justification}</p>
    </div>
)}
```

**D) Display gap analysis (after CV Enhancement Priorities section, around line 178):**

Add a new section:
```tsx
{gapAnalysis && gapAnalysis.gap_breakdown && gapAnalysis.gap_breakdown.length > 0 && (
    <div className="score-breakdown__meta score-breakdown__gap-analysis">
        <h4>📊 Gap Analysis — {gapAnalysis.total_gap_percentage ?? (100 - breakdown.overall_score)} points to close</h4>
        <div className="score-breakdown__gap-list">
            {gapAnalysis.gap_breakdown.map((gap, i) => (
                <div key={i} className="score-breakdown__gap-item">
                    <div className="score-breakdown__gap-header">
                        <span className="score-breakdown__gap-category">{gap.category}</span>
                        <span className="score-breakdown__gap-points">-{gap.gap_points} pts</span>
                    </div>
                    <p className="score-breakdown__gap-reason">{gap.reason}</p>
                </div>
            ))}
        </div>
        {gapAnalysis.improvement_actions && gapAnalysis.improvement_actions.length > 0 && (
            <>
                <h5>🎯 Prioritized Actions to Close Gaps</h5>
                <div className="score-breakdown__items">
                    {gapAnalysis.improvement_actions.map((action, i) => (
                        <div key={i} className="score-breakdown__item score-breakdown__item--rec">{action}</div>
                    ))}
                </div>
            </>
        )}
    </div>
)}
```

**E) Remove the "AI Raw Signal" section at lines 194-206** — it's no longer needed since we're using the AI's actual signal now, not overriding it.

#### 5. `frontend/src/components/detail-panel/score-breakdown-tab.css` — Add styles

Add these styles:
```css
.score-breakdown__fit-assessment {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
}

.score-breakdown__fit-label {
    font-size: 0.7rem;
    color: var(--text-secondary, #94a3b8);
    font-style: italic;
    max-width: 180px;
    text-align: right;
    line-height: 1.3;
}

.score-breakdown__justification {
    padding: 12px 16px;
    background: var(--surface-elevated, rgba(255,255,255,0.03));
    border-left: 3px solid var(--accent, #6366f1);
    border-radius: 0 8px 8px 0;
    margin-bottom: 16px;
}

.score-breakdown__justification p {
    margin: 0;
    font-size: 0.85rem;
    color: var(--text-primary, #e2e8f0);
    line-height: 1.6;
}

.score-breakdown__gap-analysis {
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 10px;
    padding: 16px;
}

.score-breakdown__gap-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin: 10px 0;
}

.score-breakdown__gap-item {
    padding: 10px 12px;
    background: var(--surface-elevated, rgba(255,255,255,0.02));
    border-radius: 8px;
    border-left: 3px solid var(--score-partial, #f59e0b);
}

.score-breakdown__gap-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.score-breakdown__gap-category {
    font-weight: 600;
    font-size: 0.8rem;
    color: var(--text-primary, #e2e8f0);
}

.score-breakdown__gap-points {
    font-weight: 700;
    font-size: 0.8rem;
    color: var(--score-partial, #f59e0b);
}

.score-breakdown__gap-reason {
    margin: 0;
    font-size: 0.78rem;
    color: var(--text-secondary, #94a3b8);
    line-height: 1.5;
}
```

#### 6. `frontend/src/components/quick-add/quick-add-bar.tsx`

Find where `getInterviewBadge(scoreResult.interview_probability)` is used. Ensure it reads from the AI's raw `interview_probability` field, NOT from a recalculated value. If there's similar static override logic here, fix it the same way — use the AI model's value directly.

Also display `fit_assessment_label` if present in the score result, as a small secondary text under the interview badge.

---

## Q3 — Fit Score KPI Source of Truth

### Decision: Backend persisted values are the SOLE source of truth

### The Problem
KPI inconsistencies between the top metrics bar and detail panel. The metrics bar may recalculate or use stale local state while the detail panel reads from persisted data.

### Changes Required

#### `frontend/src/components/layout/metrics-bar.tsx`
- Verify that ALL score/fit-related KPIs read from the same data source as the detail panel (the jobs array from the backend API)
- No local recalculations of fit_score, qualified count, or average score
- If any KPI value is derived client-side, replace it with the backend-persisted value
- After a scoring or enhancement operation completes, the metrics bar MUST re-fetch or receive updated data through the store — not recompute from local state

#### `frontend/src/stores/app-store.ts`
- Verify the scoring completion handler triggers a data refresh that propagates to the metrics bar
- The flow must be: scoring completes → backend persists result → frontend re-fetches jobs data → metrics bar renders from fresh data
- No intermediate client-side score caching that could go stale

---

## Q4 — Enhancement Export Quality Gate

### Decision: Hard validation gates before any DOCX/HTML export

### Changes Required

#### `backend/app/services/premium_export.py` (or wherever DOCX/HTML export logic lives)

Add a validation function that runs BEFORE any export operation:

```python
def _validate_enhancement_for_export(enhanced_content: dict) -> tuple[bool, list[str]]:
    """
    Validates enhanced CV content before export to DOCX/HTML.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    # Gate 1: Required sections present
    required_sections = [
        "professional_summary", "core_competencies", "professional_experience",
        "education", "contact_information"
    ]
    content_text = str(enhanced_content).lower()
    for section in required_sections:
        if section.replace("_", " ") not in content_text and section not in content_text:
            errors.append(f"Required section missing: {section}")

    # Gate 2: No JSON-wrapper leakage
    json_leak_patterns = [
        '```json', '```', '{"', '"}', "\\n\\n", "\\u00",
        '"sections":', '"content":', # raw JSON structure in output
    ]
    # Check the RENDERED output, not the parsed structure
    rendered = enhanced_content.get("rendered_text", "") or enhanced_content.get("content", "")
    for pattern in json_leak_patterns:
        if pattern in str(rendered):
            errors.append(f"JSON/code leakage detected: '{pattern}' found in rendered output")

    # Gate 3: Semantic HTML validation (for HTML exports)
    if enhanced_content.get("format") == "html":
        html_content = enhanced_content.get("html", "")
        if html_content:
            if "<h1" not in html_content and "<h2" not in html_content:
                errors.append("HTML export lacks heading structure (no h1/h2 tags)")
            if html_content.count("<") < 5:
                errors.append("HTML export appears to be plain text, not semantic HTML")
            # Check for unclosed tags (basic)
            for tag in ["div", "section", "ul", "ol", "table"]:
                opens = html_content.lower().count(f"<{tag}")
                closes = html_content.lower().count(f"</{tag}")
                if opens != closes:
                    errors.append(f"HTML validation: mismatched <{tag}> tags ({opens} open, {closes} close)")

    return len(errors) == 0, errors
```

Add the gate call before the export:
```python
is_valid, validation_errors = _validate_enhancement_for_export(enhanced_content)
if not is_valid:
    raise ValueError(
        f"Export blocked — quality gate failed with {len(validation_errors)} error(s): "
        + "; ".join(validation_errors)
    )
```

Log validation failures for monitoring but never silently produce malformed output. A failed export with a clear error message is infinitely better than a corrupted DOCX that the candidate submits to an employer.

---

## Key Rules

- **Q2 is the most critical change** — it affects every scored job in the system. Test with multiple jobs after implementation.
- **Never override AI model output with static logic.** If the model says HIGH and the score is 65, the model has a reason. Show both.
- **Backward compatibility:** old scored jobs won't have `fit_assessment_label` or `gap_analysis` — use `|| ''` / `?? {}` fallbacks. They still show the score and interview probability as before.
- **The prompt change in Q2 affects ALL providers** (Groq, OpenAI, Gemini) since they share `_SYSTEM_PROMPT`. This is intentional.
- **Do not touch the Groq multi-key, anti-fingerprinting, or rate limiting code** — that's already implemented and stable.
