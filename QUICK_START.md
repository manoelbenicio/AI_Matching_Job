# AI Job Matcher - Quick Start Guide (100% Python)

## 🚀 Quick Start

### 1. Start PostgreSQL + Metabase
```powershell
cd D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher
docker-compose -f docker-compose.postgres.yml up -d
```

### 2. Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment
```powershell
copy .env.example .env
# Edit .env with your OPENAI_API_KEY
```

### 4. Import Existing Data (Optional)
```powershell
python import_sheets_to_postgres.py --spreadsheet-id 1Xoq4aZ10RTL_6db7NiHnl35PIXGXAxml6_GUqpxvrmM
```

### 5. Run Job Matcher
```powershell
# Dry run (preview)
python job_matcher.py --dry-run

# Process 50 jobs
python job_matcher.py --batch-size 50

# View stats
python job_matcher.py --stats
```

### 6. Export Results to Excel
```powershell
python export_to_excel.py
```

---

## 📊 Database Connection

| Setting | Value |
|---------|-------|
| Host | localhost |
| Port | 5432 |
| Database | job_matcher |
| Username | job_matcher |
| Password | JobMatcher2024! |

---

## 💡 Cost Comparison

| Metric | Old n8n Workflow | Python Workflow |
|--------|-----------------|-----------------|
| AI Calls/Job | 18+ | 1-2 |
| Tokens/Job | 60K | 3.5K |
| Time/20 Jobs | 31 min | ~3 min |
| Cost/10K Jobs | ~$120 | ~$7 |
