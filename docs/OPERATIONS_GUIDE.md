# AI Job Matcher — System Operations Guide

| Campo | Valor |
|-------|-------|
| **Document Owner** | Platform Engineering |
| **Last Updated** | 2026-02-11 |
| **Classificação** | Internal — Day 2 Operations |

---

## 1. System Overview

| # | Camada | Tecnologia | Propósito |
|---|--------|-----------|-----------|
| 1 | Frontend | Next.js 16 (TypeScript) | Dashboard moderno: Data Table + Kanban + CV Analysis |
| 2 | Backend API | FastAPI (Python 3.12) | REST API: CRUD operations, CV enhancement, audit logging |
| 3 | Database | PostgreSQL 16 | Data store primário: jobs, CV versions, audit trail |
| 4 | Analytics | Metabase v0.48 | Dashboards de business intelligence |
| 5 | AI Services | Google Gemini + OpenAI GPT-4o-mini | Job scoring, CV enhancement, multi-AI analysis |
| 6 | Automation | n8n (opcional, cloud) | LinkedIn scraping workflows |
| 7 | Notifications | Telegram Bot | Alertas de batch processing |
| 8 | Legacy Scripts | Python CLI tools | Batch scoring, Excel import/export, CV generation |

---

## 2. Architecture Diagram

```mermaid
graph TB
    subgraph "User Browser"
        FE["Next.js Frontend<br/>:3000"]
    end

    subgraph "Docker Host"
        subgraph "docker-compose.yml"
            BE["FastAPI Backend<br/>:8000"]
            DB["PostgreSQL 16<br/>:5432"]
        end
        
        subgraph "docker-compose.postgres.yml"
            DB_LEGACY["PostgreSQL 15<br/>:5432"]
            MB["Postgres/>:3000"]
        end
    end

    subgraph "External Services"
        GEMINI["Google Gemini API"]
        OPENAI["OpenAI GPT-4o-mini"]
        TELEGRAM["Telegram Bot API"]
        N8N["n8n Cloud"]
        LINKEDIN["LinkedIn"]
    end

    FE -->|"REST API"| BE
    BE -->|"SQL"| DB
    BE -->|"AI Enhancement"| GEMINI
    MB -->|"Read-Only SQL"| DB_LEGACY
    N8N -->|"Scrape"| LINKEDIN
    N8N -->|"Insert"| DB_LEGACY

    style FE fill:#3b82f6,color:#fff
    style BE fill:#22c55e,color:#fff
    style DB fill:#f59e0b,color:#000
    style MB fill:#8b5cf6,color:#fff
    style GEMINI fill:#ef4444,color:#fff
    style OPENAI fill:#ef4444,color:#fff
```

---

## 3. Docker Containers

| # | Container | Image | Porta Host | Volume | Propósito | Compose File |
|---|-----------|-------|-----------|--------|-----------|-------------|
| 1 | db | postgres:16-alpine | 5432 | pgdata:/var/lib/postgresql/data | Database primário | docker-compose.yml |
| 2 | backend | Custom Python 3.12 | 8000 | ./backend:/app (live reload) | REST API server | docker-compose.yml |
| 3 | frontend | Custom Node 20 | 3000 | ./frontend:/app (live reload) | Web UI dev server | docker-compose.yml |
| 4 | job_matcher_postgres | postgres:15-alpine | 5432 | postgres_data | Database legado | docker-compose.postgres.yml |
| 5 | job_matcher_metabase | metabase/metabase:v0.48.0 | 3000 | metabase_data | Analytics dashboard | docker-compose.postgres.yml |

| ⚠️ AVISO | Conflito de porta: Ambos compose files mapeiam porta 5432 (PostgreSQL) e 3000 (frontend vs Metabase). Rodar apenas UM compose file por vez, ou reatribuir portas. |
|----------|------|

---

## 4. API Endpoints

| # | Método | Endpoint | Descrição | Auth |
|---|--------|----------|-----------|------|
| 1 | GET | /api/jobs | Listar jobs (paginado, filtrado, ordenado) | None |
| 2 | GET | /api/jobs/:id | Detalhes de um job | None |
| 3 | PATCH | /api/jobs/:id | Atualizar status/campos do job | None |
| 4 | GET | /api/jobs/stats | Métricas agregadas (contagens por status) | None |
| 5 | POST | /api/cv/enhance | AI-enhance CV para um job | None |
| 6 | GET | /api/cv/versions/:job_id | Histórico de versões do CV | None |
| 7 | GET | /api/audit/:job_id | Audit trail de um job | None |
| 8 | GET | /api/stats | Estatísticas do dashboard | None |
| 9 | GET | /health | Health check | None |

---

## 5. Database Tables

| # | Tabela | Propósito | Colunas Principais | Status |
|---|--------|-----------|-------------------|--------|
| 1 | jobs | Todos os LinkedIn jobs + scores | id, job_title, company_name, status, score, job_url | ✅ Ativa |
| 2 | processing_logs | Histórico de batch processing | id, job_id, status, error_message | ✅ Ativa |
| 3 | schema_migrations | Tracking de migrations | version, applied_at | ✅ Ativa |
| 4 | cv_versions | Versões de CV enhancement | id, job_id, original_text, enhanced_text, fit_score | ⚠️ Pendente migration |
| 5 | audit_log | Todos os eventos de state-change | id, job_id, action, old_value, new_value, timestamp | ⚠️ Pendente migration |

---

## 6. Legacy Python Scripts

| # | Script | Propósito | Dependências |
|---|--------|-----------|-------------|
| 1 | job_matcher.py (43KB) | Pipeline principal de batch scoring | OpenAI, Gemini, PostgreSQL, Telegram |
| 2 | multi_ai_analyzer.py (47KB) | Análise multi-modelo AI | OpenAI, Gemini |
| 3 | premium_cv_generator.py (32KB) | Geração de CV HTML premium | OpenAI, pdfkit |
| 4 | dashboard.py (88KB) | DEPRECATED — UI Streamlit | streamlit, plotly |
| 5 | import_jobs_smart.py (14KB) | Import inteligente Excel/CSV | psycopg2, openpyxl |
| 6 | import_sheets_to_postgres.py (9KB) | Import Google Sheets | google-api-python-client |
| 7 | export_to_excel.py (5KB) | Export jobs qualificados | openpyxl, pandas |
| 8 | linkedin_job_fetcher.py (9KB) | Scraper LinkedIn direto | beautifulsoup4, requests |
| 9 | migrate_from_linkedin_db.py (5KB) | Migrar do LinkedIn DB | psycopg2 |
| 10 | reprocess_scored_jobs.py (8KB) | Re-score jobs existentes | OpenAI, Gemini |
| 11 | run_batch_score.py (1KB) | Launcher de batch scoring | job_matcher |
| 12 | check_excel.py (1KB) | Validação de Excel | openpyxl |
| 13 | discard_technical_jobs.py (4KB) | Filtrar jobs técnicos | psycopg2 |

---

## 7. Network & IP Addresses

### Docker Network (Legacy — docker-compose.postgres.yml)

| # | Serviço | IP Address | Hostname | Porta |
|---|---------|-----------|----------|-------|
| 1 | PostgreSQL | 172.20.0.2 | postgres | 5432 |
| 2 | Metabase | 172.20.0.3 | metabase | 3000 |
| 3 | n8n (opcional) | 172.20.0.4 | n8n | 5678 |
| 4 | **Network** | **172.20.0.0/16** | **job_matcher_network** | — |

### Docker Network (New — docker-compose.yml)

| # | Serviço | Hostname | Porta Host | Porta Container |
|---|---------|----------|-----------|----------------|
| 1 | PostgreSQL | db | 5432 | 5432 |
| 2 | Backend | backend | 8000 | 8000 |
| 3 | Frontend | frontend | 3000 | 3000 |
| 4 | **Network** | **Default bridge** | — | — |

### Host Access URLs

| # | Serviço | URL | Notas |
|---|---------|-----|-------|
| 1 | Frontend (Next.js) | http://localhost:3000 | Dashboard principal |
| 2 | Backend API | http://localhost:8000 | REST API |
| 3 | Swagger/OpenAPI | http://localhost:8000/docs | Docs auto-gerados do FastAPI |
| 4 | Metabase | http://localhost:3000 | Só se usando legacy compose |
| 5 | Streamlit (deprecated) | http://localhost:8501 | Dashboard legado |

### External Services

| # | Serviço | Endpoint | Auth |
|---|---------|----------|------|
| 1 | OpenAI API | https://api.openai.com/v1 | API Key no .env (OPENAI_API_KEY) |
| 2 | Google Gemini | https://generativelanguage.googleapis.com | API Key no .env (GEMINI_API_KEY) |
| 3 | Telegram Bot | https://api.telegram.org/bot{TOKEN} | Token no .env (TELEGRAM_BOT_TOKEN) |
| 4 | n8n Cloud | https://your-instance.app.n8n.cloud | Login credentials |

---

## 8. Bootstrap — Starting Everything

### Pré-requisitos

| # | Requisito | Como Verificar |
|---|-----------|---------------|
| 1 | Docker Desktop rodando | docker info |
| 2 | Node.js 20+ instalado | node -v |
| 3 | Python 3.12+ com pip | python --version |
| 4 | .env configurado | Ver Seção 10 |

### Opção A: Full Stack (Nova Arquitetura) — RECOMENDADO

```powershell
# ═══════════════════════════════════════════════════════════
# AI Job Matcher — FULL STACK BOOTSTRAP (PowerShell)
# Starts: PostgreSQL + FastAPI Backend + Next.js Frontend
# ═══════════════════════════════════════════════════════════

cd "D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher"

# 1. Verificar Docker
docker info | Select-String "Server Version"

# 2. Build e start de todos containers
docker compose up --build -d

# 3. Aguardar PostgreSQL ficar healthy
Write-Host "Waiting for PostgreSQL..." -ForegroundColor Yellow
do {
    Start-Sleep -Seconds 2
    $health = docker inspect --format='{{.State.Health.Status}}' (docker compose ps -q db) 2>$null
} while ($health -ne "healthy")
Write-Host "PostgreSQL is ready!" -ForegroundColor Green

# 4. Aplicar database migrations
docker compose cp backend/migrations/001_add_version_cv_versions_audit_log.sql db:/tmp/migration.sql
docker compose exec db psql -U job_matcher -d job_matcher -f /tmp/migration.sql

# 5. Verificar containers rodando
docker compose ps

# 6. Abrir no browser
Start-Process "http://localhost:3000"
Start-Process "http://localhost:8000/docs"
```

### Opção B: Legacy Stack (Metabase + Streamlit)

```powershell
# ═══════════════════════════════════════════════════════════
# AI Job Matcher — LEGACY BOOTSTRAP (PowerShell)
# Starts: PostgreSQL + Metabase + Streamlit
# ═══════════════════════════════════════════════════════════

cd "D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher"

docker compose -f docker-compose.postgres.yml up -d
Start-Sleep -Seconds 15
pip install -r requirements.txt --quiet
Start-Process cmd -ArgumentList "/c streamlit run dashboard.py --server.port 8501 --server.headless true"
Start-Sleep -Seconds 5
Start-Process "http://localhost:8501"
Start-Process "http://localhost:3000"
```

### Opção C: Frontend Dev Only (sem Docker)

```powershell
# ═══════════════════════════════════════════════════════════
# Frontend-only dev (assume backend + DB já rodando)
# ═══════════════════════════════════════════════════════════

cd "D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher\frontend"
npm install
npm run dev
# Frontend em http://localhost:3000
```

---

## 9. Shutdown Procedure

```powershell
cd "D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher"

# Parar novo stack
docker compose down

# Parar legacy stack (se rodando)
docker compose -f docker-compose.postgres.yml down

# Matar processos órfãos
Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "streamlit" -ErrorAction SilentlyContinue | Stop-Process -Force
```

| ⚠️ CUIDADO | NÃO use `docker compose down -v` a menos que queira DESTRUIR todos os dados do banco. O flag -v remove named volumes incluindo pgdata. |
|------------|------|

---

## 10. Configuration Reference (.env)

| # | Variável | Exemplo | Usado Por | Obrigatório |
|---|----------|---------|-----------|-------------|
| 1 | DB_HOST | 127.0.0.1 | Scripts legados | ✅ Sim |
| 2 | DB_PORT | 5432 | Scripts legados | ✅ Sim |
| 3 | DB_NAME | job_matcher | Scripts legados | ✅ Sim |
| 4 | DB_USER | job_matcher | Scripts legados | ✅ Sim |
| 5 | DB_PASSWORD | JobMatcher2024! | Scripts legados | ✅ Sim |
| 6 | DATABASE_URL | postgresql://job_matcher:...@127.0.0.1:5432/job_matcher | FastAPI (host mode) | ✅ Sim |
| 7 | OPENAI_API_KEY | sk-proj-... | job_matcher.py, premium_cv_generator.py | ✅ Sim |
| 8 | OPENAI_MODEL | gpt-4o-mini | Scripts legados | ✅ Sim |
| 9 | GEMINI_API_KEY | AIza... | FastAPI CV enhancement | ⚠️ FALTANDO |
| 10 | TELEGRAM_BOT_TOKEN | 8522... | job_matcher.py notifications | Opcional |
| 11 | TELEGRAM_CHAT_ID | 999264527 | job_matcher.py notifications | Opcional |
| 12 | RESUME_DOC_ID | 1qdj... | Google Docs integration | Opcional |
| 13 | RESUME_FOLDER_ID | 1yic... | Google Drive integration | Opcional |

| ⚠️ IMPORTANTE | GEMINI_API_KEY não está configurada no .env. É obrigatória para o CV enhancement. Obter key em https://aistudio.google.com/apikey |
|---------------|------|

---

## 11. Database Operations

### Conectar ao PostgreSQL

| # | Método | Comando |
|---|--------|---------|
| 1 | Via Docker (novo stack) | docker compose exec db psql -U job_matcher -d job_matcher |
| 2 | Via Docker (legacy stack) | docker exec -it job_matcher_postgres psql -U job_matcher -d job_matcher |
| 3 | Via host (psql local) | psql -h 127.0.0.1 -U job_matcher -d job_matcher (password: JobMatcher2024!) |

### Queries Comuns

| # | Query | Propósito |
|---|-------|-----------|
| 1 | SELECT status, COUNT(*) FROM jobs GROUP BY status ORDER BY COUNT(*) DESC | Contagem de jobs por status |
| 2 | SELECT job_title, company_name, score, status FROM jobs WHERE score IS NOT NULL ORDER BY score DESC LIMIT 20 | Top scoring jobs |
| 3 | SELECT * FROM cv_versions ORDER BY created_at DESC LIMIT 10 | Últimas versões de CV (após migration) |
| 4 | SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 20 | Últimos eventos de audit (após migration) |

### Aplicar Migration Pendente

| # | Passo | Comando |
|---|-------|---------|
| 1 | Copiar migration para container | docker compose cp backend/migrations/001_add_version_cv_versions_audit_log.sql db:/tmp/migration.sql |
| 2 | Executar migration | docker compose exec db psql -U job_matcher -d job_matcher -f /tmp/migration.sql |
| 3 | Verificar tabelas criadas | docker compose exec db psql -U job_matcher -d job_matcher -c "\dt" |

---

## 12. Troubleshooting Guide

| # | Sintoma | Causa Provável | Solução |
|---|---------|---------------|---------|
| 1 | docker compose up falha | Docker Desktop não rodando | Iniciar Docker Desktop, esperar 30s, tentar novamente |
| 2 | Frontend mostra página em branco | Backend inacessível | Verificar NEXT_PUBLIC_API_URL=http://localhost:8000 |
| 3 | API retorna connection refused | PostgreSQL não pronto | Esperar health check; verificar docker compose logs db |
| 4 | Porta 3000 já em uso | Metabase rodando na mesma porta | Parar legacy compose: docker compose -f docker-compose.postgres.yml down |
| 5 | Porta 5432 já em uso | Container PostgreSQL legado ativo | docker stop job_matcher_postgres |
| 6 | CV enhancement retorna erro | GEMINI_API_KEY não configurada | Adicionar key ao .env; reiniciar backend |
| 7 | Frontend npm ci falha | Versão do Node incorreta | Verificar Node 20+: node -v |
| 8 | Backend import error | Package Python faltando | docker compose exec backend pip install PACKAGE |
| 9 | Migration falha com already exists | Migration parcialmente aplicada | Verificar se tabela existe: \dt no psql; pular se já existir |
| 10 | Kanban cards não movem | API PATCH endpoint fora | Verificar docker compose logs backend |

### Comandos de Log

| # | Propósito | Comando |
|---|-----------|---------|
| 1 | Todos os logs (últimas 100 linhas) | docker compose logs --tail=100 |
| 2 | Logs do backend (follow mode) | docker compose logs -f backend |
| 3 | Logs do frontend (follow mode) | docker compose logs -f frontend |
| 4 | Logs do database (follow mode) | docker compose logs -f db |
| 5 | Apenas erros Python do backend | docker compose logs backend 2>&1 \| Select-String -Pattern "ERROR\|Exception\|Traceback" |
| 6 | Queries ativas no banco | docker compose exec db psql -U job_matcher -c "SELECT * FROM pg_stat_activity WHERE state = 'active';" |
| 7 | Uso de recursos dos containers | docker stats --no-stream |

---

## 13. Monitoring & Observability

| # | Camada | O Que Monitorar | Como | Threshold de Alerta |
|---|--------|----------------|------|---------------------|
| 1 | Frontend | Page load time (LCP) | Browser DevTools → Lighthouse | > 2.5s |
| 2 | Frontend | JavaScript errors | Browser Console | Qualquer uncaught exception |
| 3 | Backend | Request latency | FastAPI logs (uvicorn) | > 2s para endpoints não-AI |
| 4 | Backend | Error rate (5xx) | docker compose logs backend | Qualquer erro 500 |
| 5 | Backend | AI API latency | FastAPI logs | > 30s para chamadas Gemini |
| 6 | Database | Connection count | SELECT count(*) FROM pg_stat_activity | > 50 |
| 7 | Database | Disk usage | docker system df | > 80% |
| 8 | Docker | Container health | docker compose ps | Qualquer unhealthy ou exited |
| 9 | Docker | Memory usage | docker stats | > 2GB por container |

---

## 14. Data Flow — Job Processing Pipeline

| # | Etapa | De | Para | Ação |
|---|-------|-----|------|------|
| 1 | Data Ingestion | LinkedIn | PostgreSQL | n8n scrape → insert jobs (status: pending) |
| 2 | Batch Scoring | PostgreSQL | PostgreSQL | job_matcher.py → OpenAI/Gemini → score + justification → update status |
| 3 | User Review | Dashboard | PostgreSQL | Usuário muda status via Kanban drag-drop ou tabela |
| 4 | CV Enhancement | Dashboard | Gemini API → PostgreSQL | Upload CV → click Enhance → Gemini gera CV tailored → salvo em cv_versions |
| 5 | Export | Dashboard | generated_cvs/ | Usuário aplica para job com CV enhanced → HTML output |

---

## 15. File System Layout

| # | Caminho | Tipo | Propósito |
|---|---------|------|-----------|
| 1 | docs/ | 📁 Dir | Documentação consolidada |
| 2 | docs/STATUS_REPORT_360.md | 📄 Arquivo | Project health dashboard |
| 3 | docs/OPERATIONS_GUIDE.md | 📄 Arquivo | Este documento |
| 4 | backend/ | 📁 Dir | FastAPI Backend |
| 5 | backend/Dockerfile | 📄 Arquivo | Python 3.12-slim image |
| 6 | backend/requirements.txt | 📄 Arquivo | FastAPI, psycopg2, google-generativeai |
| 7 | backend/app/main.py | 📄 Arquivo | FastAPI app, CORS, startup |
| 8 | backend/app/db.py | 📄 Arquivo | psycopg2 connection pool |
| 9 | backend/app/routes/jobs.py | 📄 Arquivo | CRUD endpoints + audit logging |
| 10 | backend/app/routes/cv.py | 📄 Arquivo | CV enhance + Gemini service |
| 11 | backend/app/routes/audit.py | 📄 Arquivo | Audit trail endpoint |
| 12 | backend/app/routes/stats.py | 📄 Arquivo | Dashboard statistics |
| 13 | backend/migrations/ | 📁 Dir | Database migrations (2 arquivos, PENDENTES) |
| 14 | frontend/ | 📁 Dir | Next.js 16 Frontend |
| 15 | frontend/Dockerfile | 📄 Arquivo | Node 20-alpine image |
| 16 | frontend/src/app/ | 📁 Dir | App Router pages (layout, page, providers, globals.css) |
| 17 | frontend/src/components/data-table/ | 📁 Dir | TanStack Table |
| 18 | frontend/src/components/kanban/ | 📁 Dir | @dnd-kit Kanban |
| 19 | frontend/src/components/detail-panel/ | 📁 Dir | Job detail drawer + tabs |
| 20 | frontend/src/components/cv/ | 📁 Dir | CV analysis widgets |
| 21 | frontend/src/components/layout/ | 📁 Dir | Header, metrics bar |
| 22 | frontend/src/components/ui/ | 📁 Dir | Button, Badge, Toast, Score |
| 23 | frontend/src/hooks/ | 📁 Dir | React Query + keyboard hooks |
| 24 | frontend/src/stores/ | 📁 Dir | Zustand state management |
| 25 | frontend/src/lib/ | 📁 Dir | API client, types, utils |
| 26 | scripts/ | 📁 Dir | Automation scripts (N8N/Ngrok) |
| 27 | migrations/ | 📁 Dir | Root-level DB migrations (001_initial_schema.sql) |
| 28 | generated_cvs/ | 📁 Dir | Output: Enhanced CV HTML files |
| 29 | docker-compose.yml | 📄 Arquivo | New stack (db + backend + frontend) |
| 30 | docker-compose.postgres.yml | 📄 Arquivo | Legacy stack (postgres + metabase) |
| 31 | .env | 📄 Arquivo | Environment variables |
| 32 | start.bat / stop.bat | 📄 Arquivo | Legacy bootstrap/shutdown (DESATUALIZADO) |
