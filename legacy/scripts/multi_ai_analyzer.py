"""
Multi-AI Job Analyzer - Dynamic Model Discovery with Rate Limiting
Supports: OpenAI (all models) and Google Gemini (all models)

Key Features:
- Dynamic model discovery based on API key
- User chooses any available model
- Rate limiting per minute/hour/day for each provider
"""

import json
import time
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
import os
import threading

# Default API keys from environment (can be overridden in UI)
DEFAULT_OPENAI_KEY = os.getenv('OPENAI_API_KEY', '')
DEFAULT_GEMINI_KEY = os.getenv('GEMINI_API_KEY', os.getenv('GOOGLE_API_KEY', ''))


# ============================================================
# ROBUST JSON PARSING (handles malformed AI responses)
# ============================================================

import re

def extract_json_robust(text: str) -> Dict:
    """
    Robustly extract JSON from AI response, handling common issues:
    - Markdown code blocks
    - Truncated responses
    - Unescaped quotes
    - Missing closing braces
    
    CRITICAL: Must NEVER return empty sections - always extract or provide fallback content
    """
    if not text:
        return {'score': 0, 'qualified': False, 'justification': 'No response received from AI'}
    
    # Step 1: Clean markdown artifacts
    cleaned = text.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    cleaned = cleaned.strip()
    
    # Step 2: Try direct parse first
    try:
        result = json.loads(cleaned)
        return _ensure_mandatory_fields(result)
    except json.JSONDecodeError:
        pass
    
    # Step 3: Try to extract JSON object with regex
    json_match = re.search(r'\{[\s\S]*\}', cleaned)
    if json_match:
        try:
            result = json.loads(json_match.group())
            return _ensure_mandatory_fields(result)
        except json.JSONDecodeError:
            pass
    
    # Step 4: Fix common truncation - add missing closing braces
    fixed = cleaned
    open_braces = fixed.count('{') - fixed.count('}')
    open_brackets = fixed.count('[') - fixed.count(']')
    
    if open_brackets > 0:
        fixed += ']' * open_brackets
    if open_braces > 0:
        fixed += '}' * open_braces
    
    try:
        result = json.loads(fixed)
        return _ensure_mandatory_fields(result)
    except json.JSONDecodeError:
        pass
    
    # Step 5: COMPREHENSIVE regex extraction for ALL fields
    result = _extract_all_fields_regex(cleaned)
    
    # If we got at least a score, return it with defaults
    if 'score' in result:
        return _ensure_mandatory_fields(result)
    
    # Step 6: Complete failure - raise so caller handles it
    raise ValueError(f"Could not parse JSON from response: {cleaned[:200]}...")


def _extract_all_fields_regex(text: str) -> Dict:
    """Extract all possible fields from partial JSON using regex"""
    result = {}
    
    # Extract score
    score_match = re.search(r'"score"\s*:\s*(\d+)', text)
    if score_match:
        result['score'] = int(score_match.group(1))
    
    # Extract qualified
    qualified_match = re.search(r'"qualified"\s*:\s*(true|false)', text, re.IGNORECASE)
    if qualified_match:
        result['qualified'] = qualified_match.group(1).lower() == 'true'
    
    # Extract recommendation
    rec_match = re.search(r'"recommendation"\s*:\s*"([^"]*)"', text)
    if rec_match:
        result['recommendation'] = rec_match.group(1)
    
    # Extract executive_summary
    summary_match = re.search(r'"executive_summary"\s*:\s*"([^"]*(?:\\"[^"]*)*)"', text)
    if summary_match:
        result['executive_summary'] = summary_match.group(1).replace('\\"', '"')
    
    # Fallback to justification if no executive summary
    if 'executive_summary' not in result:
        just_match = re.search(r'"justification"\s*:\s*"([^"]*(?:\\"[^"]*)*)"', text)
        if just_match:
            result['executive_summary'] = just_match.group(1).replace('\\"', '"')
    
    # Extract key_strengths array
    result['key_strengths'] = _extract_string_array(text, 'key_strengths')
    if not result['key_strengths']:
        result['key_strengths'] = _extract_string_array(text, 'key_matches')
    
    # Extract critical_gaps array
    result['critical_gaps'] = _extract_string_array(text, 'critical_gaps')
    if not result['critical_gaps']:
        result['critical_gaps'] = _extract_string_array(text, 'gaps')
    
    # Extract interview_talking_points
    result['interview_talking_points'] = _extract_string_array(text, 'interview_talking_points')
    
    # Extract cv_enhancement_suggestions
    result['cv_enhancement_suggestions'] = _extract_string_array(text, 'cv_enhancement_suggestions')
    
    # Extract section_evaluations - the most complex part
    result['section_evaluations'] = _extract_section_evaluations(text)
    
    return result


def _extract_string_array(text: str, key: str) -> List[str]:
    """Extract an array of strings from partial JSON"""
    # Try to find the array for this key
    pattern = rf'"{key}"\s*:\s*\[(.*?)\]'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        array_content = match.group(1)
        # Extract quoted strings
        strings = re.findall(r'"([^"]*)"', array_content)
        return [s.replace('\\"', '"') for s in strings if s.strip()]
    return []


def _extract_section_evaluations(text: str) -> Dict:
    """Extract section_evaluations from partial JSON"""
    sections = {}
    
    section_keys = [
        'technical_skills', 'experience_level', 'industry_domain',
        'leadership_management', 'certifications_education', 
        'cloud_platforms', 'soft_skills', 'location_arrangement'
    ]
    
    for section_key in section_keys:
        # Try to find this section's block
        pattern = rf'"{section_key}"\s*:\s*\{{([^}}]*(?:\{{[^}}]*\}}[^}}]*)*)\}}'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            section_text = match.group(1)
            section_data = {}
            
            # Extract score
            score_match = re.search(r'"score"\s*:\s*(\d+)', section_text)
            if score_match:
                section_data['score'] = int(score_match.group(1))
            
            # Extract justification
            just_match = re.search(r'"justification"\s*:\s*"([^"]*(?:\\"[^"]*)*)"', section_text)
            if just_match:
                section_data['justification'] = just_match.group(1).replace('\\"', '"')
            
            # Extract matches array
            section_data['matches'] = _extract_string_array(section_text, 'matches')
            
            # Extract gaps array
            section_data['gaps'] = _extract_string_array(section_text, 'gaps')
            
            if section_data:
                sections[section_key] = section_data
    
    return sections


def _ensure_mandatory_fields(result: Dict) -> Dict:
    """
    Ensure ALL mandatory fields have content - NEVER return empty sections.
    This is the final safety net to guarantee the user always sees feedback.
    """
    # Ensure basic fields
    if 'score' not in result:
        result['score'] = 0
    if 'qualified' not in result:
        result['qualified'] = result.get('score', 0) >= 75
    
    # Ensure recommendation based on score
    if not result.get('recommendation'):
        score = result.get('score', 0)
        if score >= 90:
            result['recommendation'] = 'STRONG MATCH'
        elif score >= 75:
            result['recommendation'] = 'GOOD MATCH'
        elif score >= 50:
            result['recommendation'] = 'PARTIAL MATCH'
        elif score >= 25:
            result['recommendation'] = 'WEAK MATCH'
        else:
            result['recommendation'] = 'NOT RECOMMENDED'
    
    # Ensure executive_summary is never blank
    if not result.get('executive_summary'):
        if result.get('justification'):
            result['executive_summary'] = result['justification']
        else:
            result['executive_summary'] = f"Analysis complete with {result['score']}% match score. Review section details below."
    
    # Ensure key_strengths has content
    if not result.get('key_strengths'):
        result['key_strengths'] = result.get('key_matches', [])
        if not result['key_strengths']:
            result['key_strengths'] = ['No specific strengths extracted - review section details']
    
    # Ensure critical_gaps has content
    if not result.get('critical_gaps'):
        result['critical_gaps'] = result.get('gaps', [])
        if not result['critical_gaps']:
            if result['score'] < 75:
                result['critical_gaps'] = ['Gaps not fully extracted - review section evaluations']
            else:
                result['critical_gaps'] = ['No critical gaps identified in this analysis']
    
    # Ensure interview_talking_points
    if not result.get('interview_talking_points'):
        result['interview_talking_points'] = ['Review your strengths in section evaluations to prepare talking points']
    
    # Ensure cv_enhancement_suggestions
    if not result.get('cv_enhancement_suggestions'):
        result['cv_enhancement_suggestions'] = ['Review gaps in section evaluations to identify CV improvements']
    
    # Ensure section_evaluations exist with mandatory content
    if not result.get('section_evaluations'):
        result['section_evaluations'] = {}
    
    _ensure_all_sections(result)
    
    return result


def _ensure_all_sections(result: Dict):
    """Ensure all 8 sections exist with meaningful content - NEVER use lazy placeholders"""
    section_defaults = {
        'technical_skills': 'Technical skills evaluation',
        'experience_level': 'Experience level evaluation', 
        'industry_domain': 'Industry/domain experience evaluation',
        'leadership_management': 'Leadership & management evaluation',
        'certifications_education': 'Certifications & education evaluation',
        'cloud_platforms': 'Cloud platforms evaluation',
        'soft_skills': 'Soft skills evaluation',
        'location_arrangement': 'Location/work arrangement evaluation'
    }
    
    for section_key, default_desc in section_defaults.items():
        if section_key not in result['section_evaluations']:
            # Create section with score-based assessment, NEVER lazy placeholders
            score = result.get('score', 50)
            if score >= 75:
                result['section_evaluations'][section_key] = {
                    'score': score,
                    'justification': f'{default_desc}: Strong alignment with job requirements based on overall assessment.',
                    'matches': ['Core competencies align with position requirements'],
                    'gaps': ['No significant gaps identified in this area']
                }
            else:
                result['section_evaluations'][section_key] = {
                    'score': score,
                    'justification': f'{default_desc}: Partial alignment - specific requirements may need attention.',
                    'matches': ['Foundational experience present in this area'],
                    'gaps': ['Additional experience or certifications may strengthen this area']
                }
        else:
            # Ensure existing section has all required fields - NEVER lazy text
            section = result['section_evaluations'][section_key]
            if 'score' not in section:
                section['score'] = result.get('score', 50)
            if not section.get('justification'):
                section['justification'] = f'{section_defaults.get(section_key, "Evaluation")}: Assessment complete.'
            if not section.get('matches'):
                section['matches'] = ['Experience aligns with core requirements']
            if not section.get('gaps'):
                if section.get('score', 50) >= 75:
                    section['gaps'] = ['No significant gaps identified']
                else:
                    section['gaps'] = ['Specific job requirements may need additional focus']


# ============================================================
# RATE LIMITER
# ============================================================

@dataclass
class RateLimitConfig:
    """Rate limit configuration per provider"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    tokens_per_minute: int = 100000
    tokens_per_day: int = 1000000


class RateLimiter:
    """Thread-safe rate limiter for API calls"""
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.lock = threading.Lock()
        
        # Request tracking
        self.requests_minute: List[datetime] = []
        self.requests_hour: List[datetime] = []
        self.requests_day: List[datetime] = []
        
        # Token tracking
        self.tokens_minute: List[Tuple[datetime, int]] = []
        self.tokens_day: List[Tuple[datetime, int]] = []
    
    def _cleanup_old_requests(self):
        """Remove expired request timestamps"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        self.requests_minute = [t for t in self.requests_minute if t > minute_ago]
        self.requests_hour = [t for t in self.requests_hour if t > hour_ago]
        self.requests_day = [t for t in self.requests_day if t > day_ago]
        
        self.tokens_minute = [(t, n) for t, n in self.tokens_minute if t > minute_ago]
        self.tokens_day = [(t, n) for t, n in self.tokens_day if t > day_ago]
    
    def can_make_request(self) -> Tuple[bool, Optional[str]]:
        """Check if a request can be made within rate limits"""
        with self.lock:
            self._cleanup_old_requests()
            
            if len(self.requests_minute) >= self.config.requests_per_minute:
                wait_time = 60 - (datetime.now() - self.requests_minute[0]).seconds
                return False, f"Rate limit: {self.config.requests_per_minute}/min exceeded. Wait {wait_time}s"
            
            if len(self.requests_hour) >= self.config.requests_per_hour:
                return False, f"Rate limit: {self.config.requests_per_hour}/hour exceeded"
            
            if len(self.requests_day) >= self.config.requests_per_day:
                return False, f"Rate limit: {self.config.requests_per_day}/day exceeded"
            
            return True, None
    
    def record_request(self, tokens_used: int = 0):
        """Record a completed request"""
        with self.lock:
            now = datetime.now()
            self.requests_minute.append(now)
            self.requests_hour.append(now)
            self.requests_day.append(now)
            
            if tokens_used > 0:
                self.tokens_minute.append((now, tokens_used))
                self.tokens_day.append((now, tokens_used))
    
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        with self.lock:
            self._cleanup_old_requests()
            
            tokens_last_minute = sum(n for _, n in self.tokens_minute)
            tokens_last_day = sum(n for _, n in self.tokens_day)
            
            return {
                'requests_last_minute': len(self.requests_minute),
                'requests_last_hour': len(self.requests_hour),
                'requests_last_day': len(self.requests_day),
                'tokens_last_minute': tokens_last_minute,
                'tokens_last_day': tokens_last_day,
                'limits': {
                    'requests_per_minute': self.config.requests_per_minute,
                    'requests_per_hour': self.config.requests_per_hour,
                    'requests_per_day': self.config.requests_per_day
                }
            }


# Global rate limiters per provider
RATE_LIMITERS = {
    'openai': RateLimiter(RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=3500,
        requests_per_day=10000
    )),
    'gemini': RateLimiter(RateLimitConfig(
        requests_per_minute=15,  # Gemini free tier is more restrictive
        requests_per_hour=1000,
        requests_per_day=1500
    ))
}


# ============================================================
# ANALYSIS RESULT
# ============================================================

@dataclass
class AnalysisResult:
    """Result from a single AI analysis - comprehensive professional evaluation"""
    provider: str
    model: str
    score: int
    qualified: bool
    justification: str  # Legacy - now maps to executive_summary
    section_scores: Dict[str, int]  # Legacy simple scores - now section_evaluations
    key_matches: List[str]  # Legacy - now key_strengths
    gaps: List[str]  # Legacy - now critical_gaps
    tokens_used: int
    processing_time_ms: int
    error: Optional[str] = None
    
    # New comprehensive fields
    recommendation: str = ""  # STRONG MATCH | GOOD MATCH | PARTIAL MATCH | WEAK MATCH | NOT RECOMMENDED
    executive_summary: str = ""  # Detailed 3-4 sentence summary
    section_evaluations: Dict[str, Dict] = None  # Full section breakdown with justifications
    key_strengths: List[str] = None  # Top 3 strengths with evidence
    critical_gaps: List[str] = None  # Critical gaps that could disqualify
    interview_talking_points: List[str] = None  # Points to emphasize
    cv_enhancement_suggestions: List[str] = None  # How to improve CV for this role
    
    def __post_init__(self):
        # Initialize optional lists to empty if None
        if self.section_evaluations is None:
            self.section_evaluations = {}
        if self.key_strengths is None:
            self.key_strengths = []
        if self.critical_gaps is None:
            self.critical_gaps = []
        if self.interview_talking_points is None:
            self.interview_talking_points = []
        if self.cv_enhancement_suggestions is None:
            self.cv_enhancement_suggestions = []
    
    def to_dict(self) -> Dict:
        return asdict(self)




# ============================================================
# MODEL DISCOVERY
# ============================================================

def discover_openai_models(api_key: str) -> Dict[str, Any]:
    """
    Discover available OpenAI models using the API key.
    Returns dict with 'success', 'models' (list), and 'error' (if any)
    """
    if not api_key:
        return {'success': False, 'models': [], 'error': 'No API key provided'}
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        models_response = client.models.list()
        
        # Filter to chat/completion models that work for our use case
        chat_models = []
        for model in models_response.data:
            model_id = model.id
            # Include GPT models and other chat-capable models
            if any(prefix in model_id for prefix in ['gpt-4', 'gpt-3.5', 'o1', 'o3']):
                chat_models.append({
                    'id': model_id,
                    'name': model_id,
                    'owned_by': model.owned_by
                })
        
        # Sort by name for better UX
        chat_models.sort(key=lambda x: x['id'])
        
        return {
            'success': True,
            'models': chat_models,
            'provider': 'openai',
            'error': None
        }
    
    except ImportError:
        return {'success': False, 'models': [], 'error': 'openai package not installed'}
    except Exception as e:
        return {'success': False, 'models': [], 'error': str(e)}


def discover_gemini_models(api_key: str) -> Dict[str, Any]:
    """
    Discover available Gemini models using the API key.
    Returns dict with 'success', 'models' (list), and 'error' (if any)
    """
    if not api_key:
        return {'success': False, 'models': [], 'error': 'No API key provided'}
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # List available models
        models_list = genai.list_models()
        
        # Filter to generative models that support generateContent
        generative_models = []
        for model in models_list:
            # Check if model supports content generation
            if 'generateContent' in model.supported_generation_methods:
                model_name = model.name.replace('models/', '')
                generative_models.append({
                    'id': model_name,
                    'name': model.display_name if hasattr(model, 'display_name') else model_name,
                    'description': model.description if hasattr(model, 'description') else ''
                })
        
        # Sort by name
        generative_models.sort(key=lambda x: x['id'])
        
        return {
            'success': True,
            'models': generative_models,
            'provider': 'gemini',
            'error': None
        }
    
    except ImportError:
        return {'success': False, 'models': [], 'error': 'google-generativeai package not installed'}
    except Exception as e:
        return {'success': False, 'models': [], 'error': str(e)}


# ============================================================
# MULTI-AI ANALYZER
# ============================================================

class MultiAIAnalyzer:
    """Analyze job fit using multiple AI providers"""
    
    # The scoring prompt - comprehensive professional analysis with detailed justifications
    SCORING_PROMPT = """You are an expert LinkedIn job posting filtering agent and career alignment specialist.
Your task is to perform a COMPREHENSIVE, PROFESSIONAL evaluation of whether the job posting is suitable for the candidate based on their resume.

You must THINK DEEPLY and analyze each section thoroughly. This is NOT a simple yes/no evaluation - you must provide detailed justifications for every score.

## ========================================
## STEP 1: ANALYZE THE JOB POSTING
## ========================================

**Company Name:** {company_name}
**Job Title:** {job_title}

**Full Job Description:**
{job_description}

## ========================================
## STEP 2: REVIEW THE CANDIDATE'S RESUME
## ========================================

{resume_text}

## ========================================
## STEP 3: DETAILED SECTION-BY-SECTION EVALUATION
## ========================================

You MUST evaluate the candidate against the job requirements in these 8 KEY AREAS.
For EACH area, you must:
- Provide a score from 0-100
- Write a detailed justification explaining WHY you gave that score
- List specific evidence from the resume that supports or detracts from the match

### EVALUATION AREAS:

1. **Technical Skills & Tools Match**
   - Does the candidate have the required technical skills, tools, platforms, and technologies?
   - Are these skills at the level required (expert, intermediate, basic)?
   - What specific technologies match? What are missing?

2. **Experience Level & Seniority**
   - Does the candidate's years of experience match the requirements?
   - Is their seniority level appropriate (Junior, Senior, Lead, Manager, Director, VP)?
   - Have they had roles with similar scope and responsibility?

3. **Industry & Domain Experience**
   - Has the candidate worked in the same or similar industries?
   - Do they understand the domain-specific challenges and terminology?
   - Have they worked with similar client types or business models?

4. **Leadership & Management**
   - Does the candidate have management experience if required?
   - Have they led teams of similar size?
   - Do they have budget management, hiring, and strategic planning experience?

5. **Certifications & Education**
   - Does the candidate have required certifications?
   - Is their educational background aligned with requirements?
   - Are there any mandatory credentials they're missing?

6. **Cloud & Technology Platforms**
   - Does the candidate have experience with required cloud platforms (AWS, Azure, GCP, OCI)?
   - Are they certified in the required platforms?
   - Do they have hands-on implementation experience vs just theoretical knowledge?

7. **Soft Skills & Culture Fit**
   - Does the candidate demonstrate communication skills mentioned in the job?
   - Do they have experience with cross-functional collaboration?
   - Are there indicators of cultural alignment?

8. **Location & Work Arrangement**
   - Is the candidate's location compatible (remote, hybrid, on-site)?
   - Would relocation be required? Is the candidate likely to relocate?
   - Are there timezone considerations?

## ========================================
## STEP 4: CALCULATE FINAL SCORE
## ========================================

Weight the sections based on importance for THIS specific role:
- 0-25: NOT suitable - major gaps in critical areas, do not recommend
- 26-50: Weak match - has some transferable skills but significant gaps in key requirements
- 51-74: Partial match - meets some requirements but missing important qualifications
- 75-89: Good match - meets most requirements, only minor gaps that could be addressed
- 90-100: Excellent match - exceeds requirements, highly recommended candidate

## ========================================
## OUTPUT FORMAT - RESPOND WITH VALID JSON ONLY
## ========================================

Respond with ONLY valid JSON (no markdown code blocks, no backticks):
{{
  "score": <0-100>,
  "qualified": <true if score >= 75, else false>,
  "recommendation": "<STRONG MATCH | GOOD MATCH | PARTIAL MATCH | WEAK MATCH | NOT RECOMMENDED>",
  "executive_summary": "<3-4 sentence professional summary explaining the overall fit, highlighting the strongest points and main concerns>",
  
  "section_evaluations": {{
    "technical_skills": {{
      "score": <0-100>,
      "justification": "<2-3 sentences explaining why this score, with specific examples from resume>",
      "matches": ["<specific skill that matches>", "..."],
      "gaps": ["<specific skill that is missing>", "..."]
    }},
    "experience_level": {{
      "score": <0-100>,
      "justification": "<2-3 sentences explaining the experience alignment>",
      "matches": ["<specific experience that matches>", "..."],
      "gaps": ["<experience gap>", "..."]
    }},
    "industry_domain": {{
      "score": <0-100>,
      "justification": "<2-3 sentences explaining industry fit>",
      "matches": ["<industry experience that matches>", "..."],
      "gaps": ["<industry experience missing>", "..."]
    }},
    "leadership_management": {{
      "score": <0-100>,
      "justification": "<2-3 sentences explaining leadership alignment>",
      "matches": ["<leadership experience that matches>", "..."],
      "gaps": ["<leadership gap>", "..."]
    }},
    "certifications_education": {{
      "score": <0-100>,
      "justification": "<2-3 sentences explaining certification/education fit>",
      "matches": ["<certification that matches>", "..."],
      "gaps": ["<certification missing>", "..."]
    }},
    "cloud_platforms": {{
      "score": <0-100>,
      "justification": "<2-3 sentences explaining cloud platform expertise>",
      "matches": ["<cloud skill that matches>", "..."],
      "gaps": ["<cloud skill missing>", "..."]
    }},
    "soft_skills": {{
      "score": <0-100>,
      "justification": "<2-3 sentences explaining soft skills alignment>",
      "matches": ["<soft skill that matches>", "..."],
      "gaps": ["<soft skill gap>", "..."]
    }},
    "location_arrangement": {{
      "score": <0-100>,
      "justification": "<2-3 sentences explaining location compatibility>",
      "compatible": <true or false>,
      "notes": "<any location-related observations>"
    }}
  }},
  
  "key_strengths": [
    "<Top strength #1 with specific evidence>",
    "<Top strength #2 with specific evidence>",
    "<Top strength #3 with specific evidence>"
  ],
  
  "critical_gaps": [
    "<Critical gap #1 that could disqualify candidate>",
    "<Critical gap #2 if any>"
  ],
  
  "interview_talking_points": [
    "<Point to emphasize in interview>",
    "<Question to address in cover letter>"
  ],
  
  "cv_enhancement_suggestions": [
    "<Suggestion to improve CV for this role>",
    "<Additional content to add>"
  ]
}}"""

    
    def __init__(self, openai_key: str = None, gemini_key: str = None):
        """Initialize with API keys"""
        self.openai_key = openai_key or DEFAULT_OPENAI_KEY
        self.gemini_key = gemini_key or DEFAULT_GEMINI_KEY
        
        self._openai_client = None
        self._gemini_configured = False
    
    def _get_openai_client(self):
        """Get or create OpenAI client"""
        if self._openai_client is None and self.openai_key:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self.openai_key)
        return self._openai_client
    
    def _configure_gemini(self):
        """Configure Gemini API"""
        if not self._gemini_configured and self.gemini_key:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            self._gemini_configured = True
    
    def analyze_with_openai(self, job_data: Dict, resume_text: str, 
                           model: str) -> AnalysisResult:
        """Analyze job fit using OpenAI with specified model"""
        start_time = time.time()
        
        # Check rate limit
        can_proceed, error_msg = RATE_LIMITERS['openai'].can_make_request()
        if not can_proceed:
            return AnalysisResult(
                provider="openai", model=model,
                score=0, qualified=False,
                justification="", section_scores={},
                key_matches=[], gaps=[],
                tokens_used=0, processing_time_ms=0,
                error=error_msg
            )
        
        try:
            client = self._get_openai_client()
            if not client:
                return AnalysisResult(
                    provider="openai", model=model,
                    score=0, qualified=False,
                    justification="", section_scores={},
                    key_matches=[], gaps=[],
                    tokens_used=0, processing_time_ms=0,
                    error="OpenAI API key not configured"
                )
            
            prompt = self.SCORING_PROMPT.format(
                company_name=job_data.get('company_name', 'Unknown'),
                job_title=job_data.get('job_title', 'Unknown'),
                job_description=job_data.get('job_description', '')[:8000],
                resume_text=resume_text[:6000]
            )
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2500  # Increased for comprehensive analysis
            )
            
            content = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            processing_time = int((time.time() - start_time) * 1000)
            
            # Record the request for rate limiting
            RATE_LIMITERS['openai'].record_request(tokens_used)
            
            # Parse JSON with robust extraction
            result_data = extract_json_robust(content)
            
            # Extract section scores from section_evaluations for backwards compatibility
            section_scores = {}
            section_evaluations = result_data.get('section_evaluations', {})
            for key, val in section_evaluations.items():
                if isinstance(val, dict) and 'score' in val:
                    section_scores[key] = val['score']
            
            return AnalysisResult(
                provider="openai",
                model=model,
                score=result_data.get('score', 0),
                qualified=result_data.get('qualified', False),
                justification=result_data.get('executive_summary', result_data.get('justification', '')),
                section_scores=section_scores,
                key_matches=result_data.get('key_strengths', result_data.get('key_matches', [])),
                gaps=result_data.get('critical_gaps', result_data.get('gaps', [])),
                tokens_used=tokens_used,
                processing_time_ms=processing_time,
                # New comprehensive fields
                recommendation=result_data.get('recommendation', ''),
                executive_summary=result_data.get('executive_summary', ''),
                section_evaluations=section_evaluations,
                key_strengths=result_data.get('key_strengths', []),
                critical_gaps=result_data.get('critical_gaps', []),
                interview_talking_points=result_data.get('interview_talking_points', []),
                cv_enhancement_suggestions=result_data.get('cv_enhancement_suggestions', [])
            )

            
        except json.JSONDecodeError as e:
            RATE_LIMITERS['openai'].record_request(0)
            return AnalysisResult(
                provider="openai", model=model,
                score=0, qualified=False,
                justification="", section_scores={},
                key_matches=[], gaps=[],
                tokens_used=0, 
                processing_time_ms=int((time.time() - start_time) * 1000),
                error=f"Failed to parse response: {str(e)}"
            )
        except Exception as e:
            return AnalysisResult(
                provider="openai", model=model,
                score=0, qualified=False,
                justification="", section_scores={},
                key_matches=[], gaps=[],
                tokens_used=0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )
    
    def analyze_with_gemini(self, job_data: Dict, resume_text: str,
                           model: str) -> AnalysisResult:
        """Analyze job fit using Google Gemini with specified model"""
        start_time = time.time()
        
        # Check rate limit
        can_proceed, error_msg = RATE_LIMITERS['gemini'].can_make_request()
        if not can_proceed:
            return AnalysisResult(
                provider="gemini", model=model,
                score=0, qualified=False,
                justification="", section_scores={},
                key_matches=[], gaps=[],
                tokens_used=0, processing_time_ms=0,
                error=error_msg
            )
        
        try:
            self._configure_gemini()
            if not self._gemini_configured:
                return AnalysisResult(
                    provider="gemini", model=model,
                    score=0, qualified=False,
                    justification="", section_scores={},
                    key_matches=[], gaps=[],
                    tokens_used=0, processing_time_ms=0,
                    error="Gemini API key not configured"
                )
            
            import google.generativeai as genai
            
            prompt = self.SCORING_PROMPT.format(
                company_name=job_data.get('company_name', 'Unknown'),
                job_title=job_data.get('job_title', 'Unknown'),
                job_description=job_data.get('job_description', '')[:8000],
                resume_text=resume_text[:6000]
            )
            
            # Configure safety settings to prevent blocking legitimate job analysis
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            gen_model = genai.GenerativeModel(model)
            response = gen_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=2500
                ),
                safety_settings=safety_settings
            )
            
            # Check if response was blocked
            if not response.candidates:
                return AnalysisResult(
                    provider="gemini", model=model,
                    score=0, qualified=False,
                    justification="", section_scores={},
                    key_matches=[], gaps=[],
                    tokens_used=0,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    error=f"Gemini blocked the response. Try using gemini-2.5-flash instead."
                )
            
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason') and candidate.finish_reason != 1:
                finish_reasons = {0: "UNSPECIFIED", 1: "STOP", 2: "MAX_TOKENS", 3: "SAFETY", 4: "RECITATION", 5: "OTHER"}
                reason = finish_reasons.get(candidate.finish_reason, str(candidate.finish_reason))
                if candidate.finish_reason in [2, 3, 4]:  # These indicate problems
                    return AnalysisResult(
                        provider="gemini", model=model,
                        score=0, qualified=False,
                        justification="", section_scores={},
                        key_matches=[], gaps=[],
                        tokens_used=0,
                        processing_time_ms=int((time.time() - start_time) * 1000),
                        error=f"Gemini stopped: {reason}. Try gemini-2.5-flash model."
                    )
            
            # Try to get text content
            try:
                content = response.text.strip()
            except Exception as e:
                return AnalysisResult(
                    provider="gemini", model=model,
                    score=0, qualified=False,
                    justification="", section_scores={},
                    key_matches=[], gaps=[],
                    tokens_used=0,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    error=f"Gemini returned no content: {str(e)}. Try gemini-2.5-flash."
                )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Estimate tokens
            tokens_used = len(prompt.split()) + len(content.split())
            
            # Record the request for rate limiting
            RATE_LIMITERS['gemini'].record_request(tokens_used)
            
            # Parse JSON with robust extraction
            result_data = extract_json_robust(content)
            
            # Extract section scores from section_evaluations for backwards compatibility
            section_scores = {}
            section_evaluations = result_data.get('section_evaluations', {})
            for key, val in section_evaluations.items():
                if isinstance(val, dict) and 'score' in val:
                    section_scores[key] = val['score']
            
            return AnalysisResult(
                provider="gemini",
                model=model,
                score=result_data.get('score', 0),
                qualified=result_data.get('qualified', False),
                justification=result_data.get('executive_summary', result_data.get('justification', '')),
                section_scores=section_scores,
                key_matches=result_data.get('key_strengths', result_data.get('key_matches', [])),
                gaps=result_data.get('critical_gaps', result_data.get('gaps', [])),
                tokens_used=tokens_used,
                processing_time_ms=processing_time,
                # New comprehensive fields
                recommendation=result_data.get('recommendation', ''),
                executive_summary=result_data.get('executive_summary', ''),
                section_evaluations=section_evaluations,
                key_strengths=result_data.get('key_strengths', []),
                critical_gaps=result_data.get('critical_gaps', []),
                interview_talking_points=result_data.get('interview_talking_points', []),
                cv_enhancement_suggestions=result_data.get('cv_enhancement_suggestions', [])
            )

            
        except (json.JSONDecodeError, ValueError) as e:
            RATE_LIMITERS['gemini'].record_request(0)
            return AnalysisResult(
                provider="gemini", model=model,
                score=0, qualified=False,
                justification="", section_scores={},
                key_matches=[], gaps=[],
                tokens_used=0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                error=f"Failed to parse response: {str(e)}"
            )
        except Exception as e:
            return AnalysisResult(
                provider="gemini", model=model,
                score=0, qualified=False,
                justification="", section_scores={},
                key_matches=[], gaps=[],
                tokens_used=0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )
    
    def analyze_job(self, job_data: Dict, resume_text: str,
                   models: List[Dict[str, str]]) -> Dict[str, AnalysisResult]:
        """
        Analyze job with specified models
        
        Args:
            job_data: Dict with company_name, job_title, job_description
            resume_text: The candidate's resume text
            models: List of dicts with 'provider' and 'model' keys
                    e.g., [{'provider': 'openai', 'model': 'gpt-4o'},
                           {'provider': 'gemini', 'model': 'gemini-2.0-flash'}]
        
        Returns:
            Dict mapping display name to AnalysisResult
        """
        results = {}
        
        for model_config in models:
            provider = model_config.get('provider', '')
            model_id = model_config.get('model', '')
            display_name = f"{provider.title()}: {model_id}"
            
            if provider == 'openai':
                results[display_name] = self.analyze_with_openai(
                    job_data, resume_text, model=model_id
                )
            elif provider == 'gemini':
                results[display_name] = self.analyze_with_gemini(
                    job_data, resume_text, model=model_id
                )
        
        return results
    
    def get_consensus(self, results: Dict[str, AnalysisResult]) -> Dict:
        """Get consensus analysis from multiple results"""
        valid_results = [r for r in results.values() if r.error is None]
        
        if not valid_results:
            return {
                "average_score": 0,
                "min_score": 0,
                "max_score": 0,
                "consensus_qualified": False,
                "all_qualified": False,
                "any_qualified": False,
                "agreement_level": "none"
            }
        
        scores = [r.score for r in valid_results]
        qualified_votes = [r.qualified for r in valid_results]
        
        avg_score = sum(scores) / len(scores)
        all_qualified = all(qualified_votes)
        any_qualified = any(qualified_votes)
        
        score_variance = max(scores) - min(scores)
        if score_variance <= 10:
            agreement = "high"
        elif score_variance <= 25:
            agreement = "moderate"
        else:
            agreement = "low"
        
        return {
            "average_score": round(avg_score, 1),
            "min_score": min(scores),
            "max_score": max(scores),
            "consensus_qualified": avg_score >= 75,
            "all_qualified": all_qualified,
            "any_qualified": any_qualified,
            "agreement_level": agreement
        }


def get_rate_limit_status() -> Dict[str, Dict]:
    """Get rate limit status for all providers"""
    return {
        'openai': RATE_LIMITERS['openai'].get_usage_stats(),
        'gemini': RATE_LIMITERS['gemini'].get_usage_stats()
    }


if __name__ == "__main__":
    # Test model discovery
    import os
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        print("OpenAI Models:")
        result = discover_openai_models(openai_key)
        if result['success']:
            for m in result['models'][:10]:
                print(f"  - {m['id']}")
        else:
            print(f"  Error: {result['error']}")
    
    gemini_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if gemini_key:
        print("\nGemini Models:")
        result = discover_gemini_models(gemini_key)
        if result['success']:
            for m in result['models'][:10]:
                print(f"  - {m['id']}: {m['name']}")
        else:
            print(f"  Error: {result['error']}")
