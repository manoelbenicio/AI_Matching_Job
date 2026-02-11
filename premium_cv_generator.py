"""
Premium CV Generator - Fortune 500 Quality PDF Resume Generator
Generates professionally styled, job-tailored PDF resumes in multiple formats:
- ATS-Proof (Black & White, simple formatting)
- Fortune 500 Premium HTML (Colorful, styled)
- Fortune 500 Premium PDF (Professional print-ready)
"""

import os
import re
import openai
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv

load_dotenv()

# ATS-Proof CV Template - Black & White, Simple, ATS-Friendly
ATS_CV_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Arial, Helvetica, sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #000000;
            background: white;
        }
        
        .container {
            max-width: 8.5in;
            margin: 0 auto;
            padding: 0.5in 0.75in;
        }
        
        .header {
            text-align: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #000000;
        }
        
        .name {
            font-size: 20pt;
            font-weight: bold;
            color: #000000;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .title {
            font-size: 12pt;
            font-weight: normal;
            color: #000000;
            margin-bottom: 8px;
        }
        
        .contact-info {
            font-size: 10pt;
            color: #000000;
        }
        
        .section {
            margin-bottom: 12px;
        }
        
        .section-title {
            font-size: 12pt;
            font-weight: bold;
            color: #000000;
            text-transform: uppercase;
            margin-bottom: 6px;
            padding-bottom: 3px;
            border-bottom: 1px solid #000000;
        }
        
        .summary {
            font-size: 11pt;
            color: #000000;
            text-align: justify;
        }
        
        .competencies {
            font-size: 10pt;
            color: #000000;
        }
        
        .experience-item {
            margin-bottom: 10px;
        }
        
        .exp-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 3px;
        }
        
        .exp-title {
            font-size: 11pt;
            font-weight: bold;
            color: #000000;
        }
        
        .exp-dates {
            font-size: 10pt;
            color: #000000;
        }
        
        .exp-company {
            font-size: 10pt;
            font-style: italic;
            color: #000000;
            margin-bottom: 4px;
        }
        
        .exp-achievements {
            list-style: disc;
            padding-left: 20px;
            margin: 0;
        }
        
        .exp-achievements li {
            font-size: 10pt;
            color: #000000;
            margin-bottom: 2px;
        }
        
        .cert-item {
            font-size: 10pt;
            margin-bottom: 3px;
            color: #000000;
        }
        
        .skills-grid {
            font-size: 10pt;
            color: #000000;
        }
        
        .skill-category {
            margin-bottom: 4px;
        }
        
        .skill-label {
            font-weight: bold;
        }
        
        @media print {
            .container { padding: 0.4in 0.6in; }
        }
    </style>
</head>
<body>
    <div class="container">
        {{CONTENT}}
    </div>
</body>
</html>
"""

# Premium CV HTML Template - Modern, Clean, Professional
PREMIUM_CV_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 10pt;
            line-height: 1.5;
            color: #1a1a2e;
            background: white;
        }
        
        .container {
            max-width: 8.5in;
            margin: 0 auto;
            padding: 0.5in 0.6in;
        }
        
        /* Header - Name and Contact */
        .header {
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #2c3e7b;
        }
        
        .name {
            font-size: 28pt;
            font-weight: 700;
            color: #1a1a2e;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        
        .title {
            font-size: 12pt;
            font-weight: 500;
            color: #2c3e7b;
            margin-bottom: 10px;
        }
        
        .contact-info {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 15px;
            font-size: 9pt;
            color: #4a5568;
        }
        
        .contact-item {
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        
        /* Sections */
        .section {
            margin-bottom: 18px;
        }
        
        .section-title {
            font-size: 11pt;
            font-weight: 700;
            color: #2c3e7b;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 1px solid #e2e8f0;
        }
        
        /* Professional Summary */
        .summary {
            font-size: 10pt;
            color: #2d3748;
            text-align: justify;
            line-height: 1.6;
        }
        
        /* Core Competencies */
        .competencies {
            display: flex;
            flex-wrap: wrap;
            gap: 8px 15px;
        }
        
        .competency-item {
            font-size: 9pt;
            padding: 4px 12px;
            background: linear-gradient(135deg, #f0f4ff 0%, #e8efff 100%);
            border-radius: 15px;
            color: #2c3e7b;
            font-weight: 500;
            border: 1px solid #d0daf0;
        }
        
        /* Experience */
        .experience-item {
            margin-bottom: 15px;
            page-break-inside: avoid;
        }
        
        .exp-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 5px;
        }
        
        .exp-title {
            font-size: 11pt;
            font-weight: 600;
            color: #1a1a2e;
        }
        
        .exp-dates {
            font-size: 9pt;
            color: #718096;
            font-weight: 500;
        }
        
        .exp-company {
            font-size: 10pt;
            color: #4a5568;
            font-style: italic;
            margin-bottom: 6px;
        }
        
        .exp-achievements {
            list-style: none;
            padding-left: 0;
        }
        
        .exp-achievements li {
            position: relative;
            padding-left: 15px;
            margin-bottom: 4px;
            font-size: 9.5pt;
            color: #2d3748;
        }
        
        .exp-achievements li::before {
            content: "▸";
            position: absolute;
            left: 0;
            color: #2c3e7b;
            font-weight: bold;
        }
        
        /* Highlight keywords */
        .highlight {
            background: linear-gradient(180deg, transparent 60%, #fef3c7 60%);
            font-weight: 500;
        }
        
        /* Education & Certifications */
        .edu-cert-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .cert-item {
            font-size: 9pt;
            padding: 5px 0;
            border-left: 2px solid #2c3e7b;
            padding-left: 10px;
            margin-bottom: 5px;
        }
        
        .cert-name {
            font-weight: 600;
            color: #1a1a2e;
        }
        
        .cert-issuer {
            color: #718096;
            font-size: 8.5pt;
        }
        
        /* Skills Grid */
        .skills-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
        }
        
        .skill-category {
            margin-bottom: 8px;
        }
        
        .skill-label {
            font-weight: 600;
            font-size: 9pt;
            color: #2c3e7b;
        }
        
        .skill-items {
            font-size: 9pt;
            color: #4a5568;
        }
        
        /* Job Match Banner */
        .match-banner {
            background: linear-gradient(135deg, #2c3e7b 0%, #1a1a2e 100%);
            color: white;
            padding: 12px 20px;
            margin-bottom: 20px;
            border-radius: 6px;
            text-align: center;
        }
        
        .match-title {
            font-size: 10pt;
            font-weight: 600;
            margin-bottom: 3px;
        }
        
        .match-company {
            font-size: 12pt;
            font-weight: 700;
        }
        
        /* Footer */
        .footer {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #e2e8f0;
            text-align: center;
            font-size: 8pt;
            color: #a0aec0;
        }
        
        @media print {
            body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            .container { padding: 0.4in 0.5in; }
        }
    </style>
</head>
<body>
    <div class="container">
        {{CONTENT}}
    </div>
</body>
</html>
"""


class PremiumCVGenerator:
    """Generate Fortune 500 quality PDF resumes tailored to specific jobs"""
    
    def __init__(self, gemini_api_key: str = None):
        # Use Gemini instead of OpenAI (user preference due to quota)
        # Accept API key as parameter (dashboard passes via session state)
        import google.generativeai as genai
        self.gemini_key = gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
        self.output_dir = os.path.join(os.path.dirname(__file__), "generated_cvs")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_tailored_cv(self, candidate_resume: str, job: Dict) -> Dict:
        """
        Generate tailored CVs in 3 formats:
        1. ATS-Proof (Black & White, simple formatting)
        2. Fortune 500 Premium HTML (Colorful, styled)
        3. Fortune 500 Premium PDF (Professional print-ready)
        
        Returns dict with all versions and metadata.
        """
        company = job.get('company_name', 'Unknown')
        title = job.get('job_title', 'Unknown')
        description = job.get('job_description', '')
        
        # Use GPT-4 to create a perfectly tailored resume
        prompt = f"""You are an expert executive resume writer specializing in Fortune 500 applications.

TASK: Create a tailored professional resume that positions this candidate as the PERFECT match for this specific role.

TARGET POSITION:
Company: {company}
Title: {title}
Job Description:
{description[:4000]}

CANDIDATE'S ORIGINAL RESUME:
{candidate_resume}

INSTRUCTIONS:
1. Analyze the job requirements and identify KEY SKILLS, TECHNOLOGIES, and QUALIFICATIONS they're looking for
2. Rewrite the resume to emphasize matching experience - use EXACT keywords from the job posting
3. Quantify achievements wherever possible ($X, X%, X years, etc.)
4. Reorder and prioritize experiences that best match this role
5. Add relevant skills/competencies mentioned in job posting that the candidate likely has
6. Make the Professional Summary laser-focused on this specific role
7. Keep it to 1-2 pages maximum
8. Use action verbs and achievement-focused language

OUTPUT FORMAT (use these exact section markers):
[NAME]
Manoel Benicio Filho

[TITLE]
Professional title aligned with target role

[CONTACT]
manoel.benicio@icloud.com | +55 11 99364-4444 | São Paulo, Brazil | linkedin.com/in/manoel-benicio-filho

[SUMMARY]
3-4 sentence powerful summary tailored to this role

[COMPETENCIES]
skill1, skill2, skill3 (8-12 key skills matching the job, comma-separated)

[EXPERIENCE]
TITLE | COMPANY | DATES
- Achievement 1 with metrics
- Achievement 2 with metrics
- Achievement 3 with metrics

(repeat for each role, 3-4 roles maximum)

[EDUCATION]
Degree | School | Year

[CERTIFICATIONS]
Certification Name | Issuer
(list only relevant certifications)

[SKILLS]
Category: skill1, skill2, skill3
(2-3 categories)

CRITICAL: Use EXACT terminology from the job posting. If they say "cloud migration", use "cloud migration" not "cloud transformation". Mirror their language precisely."""

        # Use Gemini for CV generation (user preference)
        import google.generativeai as genai
        
        if not self.gemini_key:
            raise ValueError("Gemini API key not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
        
        # Safety settings to prevent blocking
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            f"You are an elite executive resume writer who creates Fortune 500 winning resumes.\n\n{prompt}",
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=3000
            ),
            safety_settings=safety_settings
        )
        
        tailored_content = response.text
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"{self._sanitize_filename(company)}_{self._sanitize_filename(title)}_{timestamp}"
        
        # Parse sections once for all versions
        sections = self._parse_sections(tailored_content)
        
        # 1. Generate ATS-Proof Version (Black & White)
        ats_html_content = self._convert_to_ats_html(sections, company, title)
        ats_full_html = ATS_CV_TEMPLATE.replace("{{CONTENT}}", ats_html_content)
        ats_html_path = os.path.join(self.output_dir, f"{base_filename}_ATS.html")
        with open(ats_html_path, 'w', encoding='utf-8') as f:
            f.write(ats_full_html)
        
        # Generate ATS PDF using pdfkit (works on Windows with wkhtmltopdf)
        ats_pdf_path = os.path.join(self.output_dir, f"{base_filename}_ATS.pdf")
        try:
            import pdfkit
            # Configure pdfkit for Windows
            config = None
            wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
            if os.path.exists(wkhtmltopdf_path):
                config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
            options = {
                'page-size': 'Letter',
                'margin-top': '0.5in',
                'margin-right': '0.5in',
                'margin-bottom': '0.5in',
                'margin-left': '0.5in',
                'encoding': 'UTF-8',
                'enable-local-file-access': None,
                'quiet': ''
            }
            pdfkit.from_string(ats_full_html, ats_pdf_path, options=options, configuration=config)
            ats_pdf_generated = True
        except Exception as e:
            print(f"ATS PDF generation failed: {e}")
            ats_pdf_generated = False
            ats_pdf_path = None
        
        # 2. Generate Fortune 500 Premium HTML Version
        premium_html_content = self._convert_to_premium_html(tailored_content, company, title)
        premium_full_html = PREMIUM_CV_TEMPLATE.replace("{{CONTENT}}", premium_html_content)
        premium_html_path = os.path.join(self.output_dir, f"{base_filename}_Premium.html")
        with open(premium_html_path, 'w', encoding='utf-8') as f:
            f.write(premium_full_html)
        
        # 3. Generate Fortune 500 Premium PDF Version using pdfkit
        premium_pdf_path = os.path.join(self.output_dir, f"{base_filename}_Premium.pdf")
        try:
            import pdfkit
            # Configure pdfkit for Windows
            config = None
            wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
            if os.path.exists(wkhtmltopdf_path):
                config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
            options = {
                'page-size': 'Letter',
                'margin-top': '0.5in',
                'margin-right': '0.5in',
                'margin-bottom': '0.5in',
                'margin-left': '0.5in',
                'encoding': 'UTF-8',
                'enable-local-file-access': None,
                'quiet': ''
            }
            pdfkit.from_string(premium_full_html, premium_pdf_path, options=options, configuration=config)
            premium_pdf_generated = True
        except Exception as e:
            print(f"Premium PDF generation failed: {e}")
            premium_pdf_generated = False
            premium_pdf_path = None
        
        return {
            # ATS Version
            'ats_html': ats_full_html,
            'ats_html_path': ats_html_path,
            'ats_pdf_path': ats_pdf_path,
            'ats_pdf_generated': ats_pdf_generated,
            # Premium HTML Version
            'premium_html': premium_full_html,
            'premium_html_path': premium_html_path,
            # Premium PDF Version
            'premium_pdf_path': premium_pdf_path,
            'premium_pdf_generated': premium_pdf_generated,
            # Legacy compatibility
            'html': premium_full_html,
            'html_path': premium_html_path,
            'pdf_path': premium_pdf_path,
            'pdf_generated': premium_pdf_generated,
            # Metadata
            'company': company,
            'title': title,
            'tailored_content': tailored_content,
            'tokens_used': response.usage.total_tokens
        }
    
    def _convert_to_ats_html(self, sections: Dict, company: str, title: str) -> str:
        """Convert parsed resume content to ATS-friendly HTML (black & white, simple)"""
        html_parts = []
        
        # Header (no banner for ATS - keep it simple)
        name = sections.get('NAME', 'Manoel Benicio Filho').strip()
        prof_title = sections.get('TITLE', 'Professional').strip()
        contact = sections.get('CONTACT', 'manoel.benicio@icloud.com | +55 11 99364-4444 | São Paulo, Brazil | linkedin.com/in/manoel-benicio-filho').strip()
        
        html_parts.append(f'''
        <div class="header">
            <div class="name">{name}</div>
            <div class="title">{prof_title}</div>
            <div class="contact-info">{contact.replace('|', ' • ')}</div>
        </div>
        ''')
        
        # Professional Summary
        if 'SUMMARY' in sections:
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Professional Summary</div>
                <div class="summary">{sections['SUMMARY'].strip()}</div>
            </div>
            ''')
        
        # Core Competencies (simple text list for ATS)
        if 'COMPETENCIES' in sections:
            competencies = sections['COMPETENCIES'].strip()
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Core Competencies</div>
                <div class="competencies">{competencies}</div>
            </div>
            ''')
        
        # Experience
        if 'EXPERIENCE' in sections:
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Professional Experience</div>
                {self._format_experience(sections['EXPERIENCE'])}
            </div>
            ''')
        
        # Education
        if 'EDUCATION' in sections:
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Education</div>
                {self._format_education(sections['EDUCATION'])}
            </div>
            ''')
        
        # Certifications
        if 'CERTIFICATIONS' in sections:
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Certifications</div>
                {self._format_certifications(sections['CERTIFICATIONS'])}
            </div>
            ''')
        
        # Skills
        if 'SKILLS' in sections:
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Technical Skills</div>
                {self._format_skills(sections['SKILLS'])}
            </div>
            ''')
        
        return '\n'.join(html_parts)
    
    def _convert_to_premium_html(self, content: str, company: str, title: str) -> str:
        """Convert parsed resume content to premium HTML format"""
        
        html_parts = []
        
        # Job Match Banner
        html_parts.append(f'''
        <div class="match-banner">
            <div class="match-title">Resume Tailored For</div>
            <div class="match-company">{company} — {title}</div>
        </div>
        ''')
        
        # Parse sections
        sections = self._parse_sections(content)
        
        # Header
        name = sections.get('NAME', 'Manoel Benicio Filho').strip()
        prof_title = sections.get('TITLE', 'Professional').strip()
        contact = sections.get('CONTACT', 'manoel.benicio@icloud.com | +55 11 99364-4444 | São Paulo, Brazil | linkedin.com/in/manoel-benicio-filho').strip()
        
        html_parts.append(f'''
        <div class="header">
            <div class="name">{name}</div>
            <div class="title">{prof_title}</div>
            <div class="contact-info">
                {self._format_contact(contact)}
            </div>
        </div>
        ''')
        
        # Professional Summary
        if 'SUMMARY' in sections:
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Professional Summary</div>
                <div class="summary">{sections['SUMMARY'].strip()}</div>
            </div>
            ''')
        
        # Core Competencies
        if 'COMPETENCIES' in sections:
            competencies = [c.strip() for c in sections['COMPETENCIES'].split(',') if c.strip()]
            comp_html = ''.join([f'<span class="competency-item">{c}</span>' for c in competencies])
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Core Competencies</div>
                <div class="competencies">{comp_html}</div>
            </div>
            ''')
        
        # Experience
        if 'EXPERIENCE' in sections:
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Professional Experience</div>
                {self._format_experience(sections['EXPERIENCE'])}
            </div>
            ''')
        
        # Education
        if 'EDUCATION' in sections:
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Education</div>
                {self._format_education(sections['EDUCATION'])}
            </div>
            ''')
        
        # Certifications
        if 'CERTIFICATIONS' in sections:
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Certifications</div>
                {self._format_certifications(sections['CERTIFICATIONS'])}
            </div>
            ''')
        
        # Skills
        if 'SKILLS' in sections:
            html_parts.append(f'''
            <div class="section">
                <div class="section-title">Technical Skills</div>
                {self._format_skills(sections['SKILLS'])}
            </div>
            ''')
        
        return '\n'.join(html_parts)
    
    def _parse_sections(self, content: str) -> Dict[str, str]:
        """Parse section markers from GPT output"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            # Check for section marker
            match = re.match(r'\[([A-Z]+)\]', line.strip())
            if match:
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = match.group(1)
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _format_contact(self, contact: str) -> str:
        """Format contact info as HTML"""
        parts = [p.strip() for p in contact.replace('|', '').split() if p.strip() and len(p.strip()) > 2]
        # Reconstruct with proper separators
        items = contact.split('|')
        return ' '.join([f'<span class="contact-item">{item.strip()}</span>' for item in items if item.strip()])
    
    def _format_experience(self, exp_text: str) -> str:
        """Format experience section"""
        html_parts = []
        current_role = None
        achievements = []
        
        lines = exp_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a role header (contains | for separators)
            if '|' in line and not line.startswith('-'):
                # Save previous role
                if current_role and achievements:
                    html_parts.append(self._build_exp_item(current_role, achievements))
                
                parts = [p.strip() for p in line.split('|')]
                current_role = {
                    'title': parts[0] if len(parts) > 0 else '',
                    'company': parts[1] if len(parts) > 1 else '',
                    'dates': parts[2] if len(parts) > 2 else ''
                }
                achievements = []
            elif line.startswith('-') or line.startswith('•') or line.startswith('▸'):
                # Achievement bullet
                achievement = line.lstrip('-•▸ ').strip()
                if achievement:
                    achievements.append(achievement)
        
        # Add last role
        if current_role and achievements:
            html_parts.append(self._build_exp_item(current_role, achievements))
        
        return '\n'.join(html_parts)
    
    def _build_exp_item(self, role: Dict, achievements: list) -> str:
        """Build HTML for a single experience item"""
        bullets = ''.join([f'<li>{a}</li>' for a in achievements])
        return f'''
        <div class="experience-item">
            <div class="exp-header">
                <span class="exp-title">{role['title']}</span>
                <span class="exp-dates">{role['dates']}</span>
            </div>
            <div class="exp-company">{role['company']}</div>
            <ul class="exp-achievements">{bullets}</ul>
        </div>
        '''
    
    def _format_education(self, edu_text: str) -> str:
        """Format education section"""
        items = []
        for line in edu_text.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('['):
                items.append(f'<div class="cert-item">{line}</div>')
        return '\n'.join(items)
    
    def _format_certifications(self, cert_text: str) -> str:
        """Format certifications section"""
        items = []
        for line in cert_text.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('['):
                if '|' in line:
                    parts = line.split('|')
                    items.append(f'''
                    <div class="cert-item">
                        <span class="cert-name">{parts[0].strip()}</span>
                        <span class="cert-issuer">{parts[1].strip() if len(parts) > 1 else ""}</span>
                    </div>
                    ''')
                else:
                    items.append(f'<div class="cert-item"><span class="cert-name">{line}</span></div>')
        return '\n'.join(items)
    
    def _format_skills(self, skills_text: str) -> str:
        """Format skills section"""
        items = []
        for line in skills_text.strip().split('\n'):
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':', 1)
                items.append(f'''
                <div class="skill-category">
                    <span class="skill-label">{parts[0].strip()}:</span>
                    <span class="skill-items">{parts[1].strip()}</span>
                </div>
                ''')
        return '<div class="skills-grid">' + '\n'.join(items) + '</div>'
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize string for filename"""
        return re.sub(r'[^\w\-]', '_', name)[:30]


# Test function
if __name__ == "__main__":
    generator = PremiumCVGenerator()
    
    # Test with sample data
    test_resume = """Manoel Benicio
Technology Modernization & Digital Transformation leader with 20+ years experience.
Current: Head Strategic Business Development at Indra-Tech
Previous: Sr Cloud Operations Manager at Telefonica Tech
Certifications: AWS Solution Architect, Azure Solutions Architect, Google Cloud
"""
    
    test_job = {
        'company_name': 'Teradata',
        'job_title': 'Director, Product Management, AI Compute',
        'job_description': 'Lead AI compute product strategy. Experience with cloud platforms, data analytics, and enterprise software required.'
    }
    
    result = generator.generate_tailored_cv(test_resume, test_job)
    print(f"Generated: {result['pdf_path']}")
    print(f"Tokens used: {result['tokens_used']}")
