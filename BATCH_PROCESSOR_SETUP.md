# AI Job Matcher - Batch Processor Setup Guide

## Quick Start

### 1. Import the Workflow
1. Open n8n
2. Go to **Workflows** → **Import from File**
3. Select: `Batch_Processor_Workflow.json`

### 2. Configure Credentials
Update these nodes with your credentials:

| Node | Credential Type | Your Credential Name |
|------|-----------------|---------------------|
| Get Pending Jobs | Google Sheets OAuth2 | `Google Sheets account` |
| Mark as Processing | Google Sheets OAuth2 | `Google Sheets account` |
| Update Final Status | Google Sheets OAuth2 | `Google Sheets account` |
| Get Resume | Google Docs OAuth2 | `Google Docs account` |
| GPT-4o-mini | OpenAI API | `OpenAi account` |

### 3. Update Sheet Configuration
In nodes `Get Pending Jobs`, `Mark as Processing`, and `Update Final Status`:
- **Document ID**: `1Zbnlkf7Z_aCFQqd7Ipi6nUoosf0WkY4zMhXbQb_UO_M`
- **Sheet**: `linkedin_jobs_FINAL_unified`

### 4. Add Status Column to Your Sheet
Add a new column called `status` to your Google Sheet with default value: `pending`

Required columns for queue management:
- `status` - Job processing state
- `processed_at` - Timestamp when completed
- `batch_id` - Which batch processed this job
- `match_score` - AI rating (0-100)
- `ai_match_reasons` - AI explanation
- `score_justification` - Detailed scoring

---

## Workflow Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│  BATCH PROCESSOR WORKFLOW                                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ⏰ Queue Processor (30s)  ──► 📋 Get Pending Jobs                      │
│                                       │                                  │
│                                       ▼                                  │
│                              🔢 Batch Selector (15 jobs)                │
│                                       │                                  │
│                                       ▼                                  │
│                              📝 Batch Controller                         │
│                                       │                                  │
│                                       ▼                                  │
│                              ✏️ Mark as Processing                       │
│                                       │                                  │
│                                       ▼                                  │
│                              ⏱️ Rate Limiter (2s)                        │
│                                       │                                  │
│                                       ▼                                  │
│                              🔄 Schema Mapper                            │
│                                       │                                  │
│                                       ▼                                  │
│                              ➕ Merge Job + Resume ◄── 📄 Get Resume     │
│                                       │                                  │
│                                       ▼                                  │
│                              🤖 Job Matching Agent                       │
│                                       │                                  │
│                                       ▼                                  │
│                              📊 Score Processor                          │
│                                       │                                  │
│                                       ▼                                  │
│                              💾 Update Final Status                      │
│                                       │                                  │
│                                       ▼                                  │
│                              ❓ Qualified? (≥70%)                        │
│                                 │           │                            │
│                           ✅ Yes         ❌ No                           │
│                                 │           │                            │
│                                 └─────┬─────┘                            │
│                                       ▼                                  │
│                              📋 Batch Summary                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Processing Metrics

| Metric | Value |
|--------|-------|
| Batch size | 15 jobs |
| Delay between AI calls | 2 seconds |
| Processor interval | Every 30 seconds |
| Jobs per hour | ~900 |
| Time for 7,500 jobs | ~8-9 hours |

---

## Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Waiting in queue |
| `processing` | Currently with AI |
| `qualified` | Score ≥ 70% |
| `rejected` | Score < 70% |
| `failed` | Max retries exceeded |

---

## Testing Steps

1. **Set 10 jobs to `pending`** in your Sheet
2. **Run Manual Batch Trigger** in n8n
3. **Watch the Sheet** - statuses should update in real-time
4. **Check logs** for any errors
5. **Activate workflow** once confirmed working
