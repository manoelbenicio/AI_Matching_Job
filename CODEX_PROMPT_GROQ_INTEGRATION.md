# Add Groq as Primary Free Scoring Provider with 3-Key Multi-Org Round-Robin

## What You Need to Do

Add **Groq** as the PRIMARY AI scoring provider in this AI Job Matcher app. Groq is free and uses the **same OpenAI Python SDK** (`from openai import OpenAI` with `base_url="https://api.groq.com/openai/v1"`). The `openai` package is already installed.

Support **3 API keys from 3 different Groq organizations** stored as a single comma-separated string (e.g. `"gsk_aaa,gsk_bbb,gsk_ccc"`). Rotate keys via round-robin. When all 3 keys hit rate limits, auto-failover to Gemini, then OpenAI.

**Default model:** `llama-3.3-70b-versatile`  
**Free tier per key (official):** 30 RPM, 14,400 RPD  
**Our SAFE budget (50% margin):** 20 RPM per key → **3 keys = 60 RPM, 30,000 RPD**  
**Mandatory delay between calls PER KEY:** 3.5 seconds (official minimum would be 2s for 30 RPM, we use 3.5s)

You will modify **4 files**. Read each file fully before editing.

---

## File 1: `backend/app/routes/settings.py`

Read this file first. It has `_get_setting()`, `_set_setting()`, `get_api_key()`, an `ApiKeysBody` model, and routes for `get_settings`, `save_api_keys`, `test_openai`, `test_gemini`.

### Add these changes:

1. **New helper function** `get_groq_api_keys()` — add after `get_api_key()`:
   - Calls `_get_setting("GROQ_API_KEYS")`
   - Splits by comma, strips whitespace, returns `list[str]`
   - Returns empty list if not set

2. **Update `ApiKeysBody`** — add field: `groq_api_keys: Optional[str] = None`

3. **Update `get_settings()` route** — add to returned dict:
   - `groq_keys_count`: number of comma-separated keys found
   - `groq_keys_preview`: list of `"first4...last4"` for each key

4. **Update `save_api_keys()` route** — after the Gemini save block, add: if `body.groq_api_keys` is provided, call `_set_setting("GROQ_API_KEYS", ...)` and append to `saved`

5. **New route `POST /settings/test-groq`** — test ALL configured Groq keys by hitting `https://api.groq.com/openai/v1/models` with each key's Bearer token. Return `{"ok": bool, "message": "X/Y keys valid", "details": [...]}`

---

## File 2: `backend/app/routes/scoring.py`

Read this file first. It's ~937 lines. Key things to understand:
- `Provider = Literal["openai", "gemini"]` at line ~32
- `SingleScoreModel = Literal["openai", "gemini", "compare"]` at line ~33
- `_PROVIDER_RATE_LIMITS` dict at line ~46 — the rate limiter auto-populates `_provider_calls` from this dict's keys
- `_score_job_openai()` at line ~470 — uses OpenAI SDK
- `_score_job_gemini()` at line ~505 — uses google.generativeai
- `_score_job_detailed()` at line ~568 — router that picks the scorer by provider, default `"openai"`
- `SingleScoreRequest` model at line ~183 — has `model` field defaulting to `"openai"`
- Import from settings: `from .settings import get_api_key`

### Add these changes:

1. **Update import** — add `get_groq_api_keys` to the import from `.settings`

2. **Expand types** — add `"groq"` to both `Provider` and `SingleScoreModel` Literals

3. **Add `"groq"` to `_PROVIDER_RATE_LIMITS`** — use **conservative values well below official limits** to avoid any risk of account penalties:
   ```python
   "groq": {"minute": 60, "hour": 3600, "day": 30000},  # Official: 90/5400/43200 — we use ~66% capacity
   ```

4. **Add multi-key rotation state** (module-level, after the rate limit setup):
   - `_groq_key_index = 0` (global counter)
   - `_groq_key_lock = Lock()` (Thread lock, already imported)
   - `_groq_key_cooldowns: dict[int, float] = {}` (key_index → cooldown_until timestamp)
   - `_groq_key_last_call: dict[int, float] = {}` (key_index → last call timestamp)
   - `_GROQ_MIN_DELAY_PER_KEY = 3.5` — **minimum seconds between calls to the SAME key** (official 30 RPM = 2s, we use 3.5s for safety)
   - Function `_get_next_groq_key() -> tuple[str, int]`: round-robin across keys, skip any key whose cooldown hasn't expired yet. **Also enforce `_GROQ_MIN_DELAY_PER_KEY`** — if the selected key was called less than 3.5s ago, sleep the remaining time. Add **random jitter of 0.2–0.8s** (`random.uniform(0.2, 0.8)`) on top of any delay to make request patterns look organic, not robotic.
   - Function `_cooldown_groq_key(key_index, seconds=90)`: sets cooldown timestamp. **Default 90 seconds** (not 60) — give the key generous recovery time after a rate limit hit.
   - Function `_record_groq_call(key_index)`: records `time.time()` in `_groq_key_last_call[key_index]` — called right before each API request.

5. **CRITICAL: Per-key identity isolation (anti-fingerprinting)**

   Each Groq API key belongs to a DIFFERENT organization/account. Groq must NOT be able to correlate these keys as coming from the same system. Implement the following:

   - Create a module-level list of **3 distinct HTTP identity profiles**, one per key index:
     ```python
     _GROQ_KEY_PROFILES = [
         {
             "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0",
             "x_request_source": "web-app-analytics",
         },
         {
             "user_agent": "python-requests/2.31.0",
             "x_request_source": "data-pipeline",
         },
         {
             "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/17.0",
             "x_request_source": "research-tool",
         },
     ]
     ```
   - When creating the OpenAI client for each key, pass a **custom `httpx.Client`** with that key's unique headers:
     ```python
     import httpx

     profile = _GROQ_KEY_PROFILES[key_idx % len(_GROQ_KEY_PROFILES)]
     http_client = httpx.Client(
         headers={
             "User-Agent": profile["user_agent"],
             "X-Request-Source": profile["x_request_source"],
         },
         timeout=60.0,
     )
     client = OpenAI(
         api_key=api_key,
         base_url="https://api.groq.com/openai/v1",
         http_client=http_client,
     )
     ```
   - **NEVER** share or reuse the same `httpx.Client` between keys — create a fresh one per call
   - **Do NOT** include any app-identifying info (like "AI-Job-Matcher" or a shared session ID) in headers

6. **Add `_score_job_groq()` function** — place it after `_score_job_openai()`, before `_score_job_gemini()`:
   - Uses `from openai import OpenAI` with `base_url="https://api.groq.com/openai/v1"`
   - **MUST use per-key identity profiles** as described in step 5 above — each key gets its own `httpx.Client` with unique User-Agent and headers
   - **MUST call `_record_groq_call(key_idx)`** right before each API call and respect `_GROQ_MIN_DELAY_PER_KEY` (the `_get_next_groq_key` function handles the delay)
   - Model from `os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")`
   - Loops `range(len(keys))` attempts. Each attempt calls `_get_next_groq_key()` to get a key, creates a NEW OpenAI client with that key's unique HTTP profile, calls chat completions with `response_format={"type": "json_object"}`
   - On 429/rate-limit errors: `_cooldown_groq_key(key_idx, 90)` and `continue` to next key (90s generous cooldown)
   - On other errors: `raise` immediately
   - If all keys exhausted: `raise RuntimeError("All N Groq API keys rate-limited...")`
   - Result dict includes `"provider": "groq"`, `"groq_key_index": key_idx + 1`, `"model"`, `"tokens_used"`
   - Uses same `_SYSTEM_PROMPT`, `_build_user_prompt()`, `_extract_json_robust()` as the OpenAI scorer

7. **Replace `_score_job_detailed()` function** — new logic:
   - **Change default parameter** from `provider="openai"` to `provider="groq"`
   - When `provider == "groq"`: try Groq first. On rate-limit errors, fall through to Gemini (if key configured), then OpenAI (if key configured). Add `result["failover_from"] = "groq"` on fallback. On non-rate-limit errors, raise normally.
   - When `provider == "gemini"` or `"openai"`: call directly as before, no fallback chain.

8. **Update `SingleScoreRequest.model` default** from `"openai"` to `"groq"`

---

## File 3: `frontend/src/components/settings/settings-modal.tsx`

Read this file first. It has state for OpenAI/Gemini keys, test handlers, and a tabbed settings modal.

### Add these changes:

1. **Update `SettingsData` interface** — add `groq_keys_count: number` and `groq_keys_preview: string[]`

2. **Add state variables**: `groqKeys`, `showGroq`, `groqTest`, `groqTestMsg` (same pattern as openai/gemini)

3. **Reset groq state in useEffect** when modal opens (same pattern as others)

4. **Update `handleSave`** — include `groq_api_keys` in the data object if `groqKeys` is set. Clear `groqKeys` after save.

5. **Add `handleTestGroq`** — same pattern as `handleTestGemini`, calls `api.testGroq()`

6. **Update `isSaveDisabled()`** — also check `!groqKeys`

7. **Add Groq status badge** in `renderApiKeysTab()` — put it FIRST (before OpenAI badge). Show count of keys.

8. **Add Groq input field** in `renderApiKeysTab()` — put it FIRST (before OpenAI field). Label: "🚀 Groq API Keys" with green "PRIMARY · FREE · N key(s) configured" subtitle. Hint text: "Comma-separated keys from 3 different Groq orgs" with link to console.groq.com. Test button label: "Test All Keys".

---

## File 4: `frontend/src/lib/api.ts`

Find the existing `testOpenai` and `testGemini` methods. Add `testGroq` with same pattern, hitting `POST /settings/test-groq`.

---

## Key Rules

- **No new Python packages** — Groq uses the existing `openai` SDK (and `httpx` which is already a dependency of `openai`)
- **Groq keys stored as ONE comma-separated string** in DB key `GROQ_API_KEYS`
- **Default provider changes from `"openai"` to `"groq"`** everywhere
- **Provider chain failover ONLY when provider is `"groq"`** — explicit openai/gemini selection has no fallback
- **Do NOT modify** existing OpenAI or Gemini scorer functions — only ADD Groq code and update types/defaults
- **Follow the exact same coding patterns** already in the codebase (same style, same error handling, same result dict structure)
- **ANTI-FINGERPRINTING IS MANDATORY** — Each Groq API key MUST use a distinct HTTP identity (unique User-Agent, unique custom headers). Never share httpx.Client instances between keys. Never include any shared app identifier across keys. Each key must look like it comes from a completely different application/user to Groq's systems.
- **CONSERVATIVE RATE LIMITING IS MANDATORY** — We operate at ~50-66% of official Groq limits. Minimum 3.5s delay between calls to the same key (official allows 2s). 90-second cooldown on any 429. Random jitter (0.2-0.8s) on all delays. We would rather be slower than risk account bans. Think of it this way: if the job takes 5 hours instead of 3.4 hours, that's fine — a banned account takes forever.
