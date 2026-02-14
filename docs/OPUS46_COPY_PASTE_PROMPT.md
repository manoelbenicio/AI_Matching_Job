# OPUS 4.6 — Copy/Paste Prompt (RCA Consolidado)

Use este prompt como entrada única para continuidade arquitetural.

## Contexto
Projeto: **AI Job Matcher**  
Data referência: **2026-02-14**  
Fonte oficial de status e RCA: `docs/OPUS46_HANDOFF.md`

## O que já foi implementado (Q1–Q4)
1. **Q1 Freeze policy**: `backend/app/services/cv_enhancer.py` marcado como artefato isolado (não acoplado ao runtime).
2. **Q2 Fit contextual por IA**:
   - `interview_probability` não é mais sobrescrito por regra estática na UI.
   - `fit_assessment_label`, `overall_justification`, `gap_analysis` exibidos no frontend.
   - `_SYSTEM_PROMPT` expandido e normalização ajustada no backend.
3. **Q3 KPI source of truth**:
   - refresh signal no store para forçar refetch dos KPIs com dados persistidos do backend.
4. **Q4 Export quality gate**:
   - validação rígida antes de DOCX/HTML, bloqueando export inválido com erro explícito.

## RCAs abertos (tratamento obrigatório)
### RCA-2026-02-14-007 (High)
- Área: `cv_enhancer` vs suite de testes
- Sintoma: falhas de contrato/assinatura e validação em `tests/test_cv_enhancer.py`
- Causa: drift entre contrato esperado nos testes e implementação atual isolada
- Ação esperada:
  1. Congelar assinatura pública de `_call_gemini_section(prompt, max_tokens=...)`
  2. Compatibilizar testes/implementação sem quebrar freeze do fluxo runtime

### RCA-2026-02-14-008 (High)
- Área: integração export
- Sintoma: `422` em `tests/test_cv_integration.py` após quality gate
- Causa: fixtures não atendem seções obrigatórias (ex.: contact_information)
- Ação esperada:
  1. Atualizar fixtures para payload production-like
  2. Manter gate ativo em produção

### RCA-2026-02-14-009 (Medium)
- Área: semantic export v2
- Sintoma: `tests/test_premium_export_v2.py` falham por ausência de `_walk_html_to_docx`/`_DocxHtmlWalker`
- Causa: pipeline atual ainda usa normalização texto + reconstrução
- Ação esperada:
  1. Implementar API semântica HTML->DOCX mínima (h1/h2/h3, p, ul/li, strong, em)
  2. Integrar por feature-flag até cobertura total

### RCA-2026-02-14-010 (Medium)
- Área: compare mode normalization
- Sintoma: fallback determinístico em `jobs.py` ainda prioriza `(openai, gemini)`
- Causa: legado não atualizado para Groq-first
- Ação esperada:
  1. Incluir `groq` no fallback de `detailed_score`
  2. Validar render compare-mode com resultados Groq

## Divergências fora do planejado detectadas
1. Full suite atual: `58 passed, 17 failed, 2 skipped`
2. Falhas concentradas em:
   - `tests/test_cv_enhancer.py`
   - `tests/test_cv_integration.py`
   - `tests/test_premium_export_v2.py`
3. Escopo scoring/UI principal (Q1–Q4): validado com build frontend e testes contratuais principais.

## Requisitos de entrega esperados do Opus
1. Plano de correção P0/P1 com owner e ETA por RCA.
2. Patch proposto para os 4 RCAs abertos.
3. Estratégia de compatibilidade regressiva (sem quebrar runtime atual).
4. Atualização obrigatória em `docs/OPUS46_HANDOFF.md` com:
   - timestamp
   - owner
   - decisão
   - evidência de validação (comando + resultado)

## Comandos de validação obrigatórios
```bash
cd AI_Job_Matcher/backend
python -m pytest tests -q

cd ../frontend
npm run -s build
```

## Critério de aceite
- Nenhum override estático de sinal da IA no frontend.
- Gate de qualidade de export ativo e coberto por testes.
- Contratos de teste alinhados com arquitetura congelada.
- Status e RCA 100% atualizados no handoff.
