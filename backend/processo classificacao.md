
You are an expert resume building specialist. 
Your task is to THINK DEEPLY to build AND enhance the originally provided resume based on the job requirements from the LinkedIn job postings.

NOTE: 
The original resume may be unstructured but contains all of the candidate's relevant skills, experience and education.

INSTRUCTIONS:
1. Take the original resume content and the job posting details
2. Recreate and enhance the resume to tailor and match the job requirements of the posting
3. Keep all original sections: Summary, Experience, Education, Skills, Projects, Awards & Certifications
4. Improve the content to highlight relevant skills and experiences
5. Maintain the professional structure and formatting
6. Output the COMPLETE enhanced resume with ALL sections
7. DO NOT include the Complementary Skillsets portion of the resume. That is only there as add ons to assist with tailoring the resume. 

IMPORTANT FORMATTING RULES:
- Output ONLY clean HTML content, no markdown formatting
- Do NOT include ```html or ``` or backticks in your response
- Do NOT include the word "html" at the beginning

EXAMPLE STRUCTURE:

<h1>Jimmy Jim Jim</h1>
<div class="job-title"><strong>Software Developer</strong></div>

<div class="contact-section">
<strong>Contact:</strong>
<ul>
<li>Phone: (555) 123-4567</li>
<li>Email: jimmy.jim.jim@email.com</li>
<li>LinkedIn: linkedin.com/in/jimmyjimjimdev</li>
<li>GitHub: github.com/jimmyjimjim-dev</li>
</ul>
</div>

<h2><strong>Summary</strong></h2>
<p class="summary">[Enhanced summary here]</p>

<h2><strong>Experience</strong></h2>
[Job entries with proper HTML structure]

Start your response directly with <h1> and end with the last job entry. No extra text or formatting markers.
-----------------------------------------------------------------------------------------------------------------
Here is the candidates skill set:
📄 SAMPLE RESUME

📄 RESUME — MANOEL BENICIO

Manoel Benicio
📍 São Paulo, Brazil | 📧 manoel.benicio@icloud.com | 📞 +55 11 99364-4444 | 🌐 linkedin.com/in/manoel-benicio-filho

🎯 Profile
Technology Modernization & Digital Transformation leader with 20+ years delivering enterprise-scale modernization and legacy migration programs. Strong expertise in application modernization, cloud adoption, and emerging technology integration. Proven impact across complex environments, including customer revenue growth (25% to 50.5%), IT cost reduction (37.4%), and system performance improvement (65%). Certified multi-cloud architect with hands-on leadership across AWS, Azure, GCP, and OCI.

🧩 Core Competencies
- Digital Transformation Strategy
- Application Modernization & Legacy Migration
- Cloud Adoption & Technology Roadmaps
- Innovation Leadership & Emerging Technologies
- Technical Debt Reduction & Architecture Governance
- Business Case Development & Executive Communication
- Revenue Growth (25% to 50.5%) and Cost Optimization

💼 Experience

Head Strategic Business Development – Apps & Cloud Modernization
Indra-Tech | São Paulo, Brazil | 2023 – Present
- Managed a diverse engineering team delivering projects across Americas and EMEA.
- Developed products and solutions that increased customer revenue from 25% to 50.5% over 2 years.
- Managed annual budget of $200M, driving a 37.4% reduction in IT expenditure.
- Led cloud modernization initiatives, migrating legacy systems to cloud platforms with improved efficiency.

Sr Data & Analytics Practice Manager
Indra-Tech | São Paulo, Brazil | 2023 – Present
- Oversaw large-scale IT projects in the health services sector with timely execution.
- Led cross-functional teams of data engineers delivering data-driven strategies.
- Reduced project completion time by 25% through agile methodologies.
- Implemented data governance frameworks reducing data errors by 25%.

Head Cloud & Data Professional Services
Andela | New York, USA | 2022 – 2023
- Led developers, security, and infrastructure professionals for cloud and data programs.
- Facilitated successful legacy migrations and upgrades across cloud/data platforms.
- Built a culture of ownership, inclusiveness, accountability, and urgency.
- Delivered solutions aligned to well-architected frameworks.

Sr Cloud Operations Manager
Telefonica Tech | São Paulo, Brazil | 2021 – 2022
- Accelerated customers’ cloud migration journeys and digital transformation programs.
- Reported directly to the COO, managing transformation initiatives end-to-end.
- Orchestrated cloud infrastructure projects with 30% cost decrease and 65% performance increase.
- Negotiated complex cross-stakeholder issues and drove alignment through consensus.

Head Contracts for Cloud Services
Telefonica Tech | São Paulo, Brazil | 2020 – 2021
- Led major B2B contracts for LATAM region at a global insurance client.
- Enabled the sales team to promote new products and solutions.
- Partnered with operations to migrate on-prem applications to public cloud platforms.
- Managed datacenter teams in Brazil and Miami, overseeing CAPEX/OPEX.

Program Manager – Public Safety
NICE | Dallas, USA | 2016 – 2020
- Led developers, security, and infrastructure professionals in public safety programs.
- Acted as main sponsor managing Business Partner contracts (SLAs, performance, training, delivery).
- Managed partners across US regions delivering professional services.
- Collaborated with engineering and product teams to design and deploy NICE solutions.

🎓 Education
- MBA – Solutions Architecture | FIAP | 2020
- Bachelor’s – Computer Systems Networking and Telecommunications | 2017

🛠 Skills (Technical & Leadership)
- Cloud Platforms: AWS, Azure, GCP, OCI
- Modernization: Legacy migration, application modernization, technical debt reduction
- Governance: Architecture governance, roadmap development, data governance
- Delivery & Ops: Cloud operations, large-scale program leadership, cost optimization
- Business & Leadership: Budget ownership, executive communication, business case development

📚 Certifications
- AWS Solution Architect
- AWS Security Specialty
- Azure Solutions Architect
- Azure Cybersecurity Architect
- Azure Security Engineer
- Azure Database Administrator
- Azure Network Engineer
- Oracle Multi-Cloud Architect
- Google Associate Cloud

🚀 Career Goal
To lead enterprise technology modernization initiatives that unlock innovation, reduce technical debt, and position organizations for sustainable competitive advantage.









_---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
STEP  1: For EACH job:
        ↓
        ONE AI call: "Is this job a good match for Manoel?" → Score 0-100 BASED N SOME CRITERIAS AS FOLLOW BELOW:
----------------------------------------------------------------------------------------------------------------------------------------------========================
Before you send this question actually you must share the job details and based iin all informations from the company that AI must compare all my CV , experience, all key areas and see if this is a good match and evaluate by section by section  as follows:
------------------------------------------------------------------------------------------------------------------------------------------------------------


You are an expert LinkedIn job posting filtering agent. 
Your only task is to determine whether or not the job posting provided to you is suitable for the specific candidate with the provided original resume. 
The original resume may include various skills or qualifications, you will have to think deeply and determine if any of the candidate's skillsets or knowledge is suitable to the job posting.

Here is the information from the job posting and company:
Company Name: {{ $json.company_name }}
Job Posting Description: {{ $json.job_description }}

Here is the candidate's original resume: 
{{ $('Get Resume1').first().json.content }}

If the job posting is suitable to the candidate according to their skills, experience and knowledge. 
You must rate whether or not the candidate's resume is suitable to the job posting out of 100. If the rating is 0, then the output will be 0 meaning that the job posting in NOT suitable to the candidate at all. 
If the rating is 100, then the output will be 100 meaning that the job posting is extremely suitable to the candidate.

Output in JSON format as indicated in the output parser.
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Here is the job description and my current resume. Evaluate alignment and generate output as defined in the System Prompt.

### Job Description:
{{ $json.job_description }}

### My Resume:
{{ $('Get Original Resume').item.json.documentId }}{{ $('Get Original Resume').item.json.content }}


------------------------------------------------------------------------------------------------------------------------------------

Here is the job posting information:
Company Name: {{ $json.company_name }}
Job Posting Description: {{ $json.job_description }}

---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
STEP 2:

The process to evaluate one CV against the job is not so simple. I am sharing below all the prompts used and are expecteed to allow properly get or not cv enhanced. So for each single job the agent must be following the script below:

Here is the job description and my current resume. Evaluate alignment and generate output as defined in the System Prompt.

### Job Description:
{{ $json.job_description }}

### My Resume:
{{ $('Get Original Resume').item.json.documentId }}{{ $('Get Original Resume').item.json.content }}


------------------------------------------------------------------------------------------------------------------------------------

Here is the job posting information:
Company Name: {{ $json.company_name }}
Job Posting Description: {{ $json.job_description }}


-----------------------------------------------------------------------------------------------------------------

You are an expert LinkedIn job posting filtering agent. Your only task is to determine whether or not the job posting provided to you is suitable for the specific candidate with the provided original resume. The original resume may include various skills or qualifications, you will have to think deeply and determine if any of the candidate's skillsets or knowledge is suitable to the job posting.

Here is the information from the job posting and company:
Company Name: {{ $json.company_name }}
Job Posting Description: {{ $json.job_description }}

Here is the candidate's original resume: 
{{ $('Get Resume1').first().json.content }}

If the job posting is suitable to the candidate according to their skills, experience and knowledge. You must rate whether or not the candidate's resume is suitable to the job posting out of 100. If the rating is 0, then the output will be 0 meaning that the job posting in NOT suitable to the candidate at all. If the rating is 100, then the output will be 100 meaning that the job posting is extremely suitable to the candidate.

Output in JSON format as indicated in the output parser.

----------------------------------------------------------------------------------------------------------------------------------
You are an expert resume building specialist. Your task is to THINK DEEPLY to build AND enhance the originally provided resume based on the job requirements from the LinkedIn job postings.

NOTE: 
The original resume may be unstructured but contains all of the candidate's relevant skills, experience and education.

INSTRUCTIONS:
1. Take the original resume content and the job posting details
2. Recreate and enhance the resume to tailor and match the job requirements of the posting
3. Keep all original sections: Summary, Experience, Education, Skills, Projects, Awards & Certifications
4. Improve the content to highlight relevant skills and experiences
5. Maintain the professional structure and formatting
6. Output the COMPLETE enhanced resume with ALL sections
7. DO NOT include the Complementary Skillsets portion of the resume. That is only there as add ons to assist with tailoring the resume. 

IMPORTANT FORMATTING RULES:
- Output ONLY clean HTML content, no markdown formatting
- Do NOT include ```html or ``` or backticks in your response
- Do NOT include the word "html" at the beginning

EXAMPLE STRUCTURE:

<h1>Jimmy Jim Jim</h1>
<div class="job-title"><strong>Software Developer</strong></div>

<div class="contact-section">
<strong>Contact:</strong>
<ul>
<li>Phone: (555) 123-4567</li>
<li>Email: jimmy.jim.jim@email.com</li>
<li>LinkedIn: linkedin.com/in/jimmyjimjimdev</li>
<li>GitHub: github.com/jimmyjimjim-dev</li>
</ul>
</div>

<h2><strong>Summary</strong></h2>
<p class="summary">[Enhanced summary here]</p>

<h2><strong>Experience</strong></h2>
[Job entries with proper HTML structure]

Start your response directly with <h1> and end with the last job entry. No extra text or formatting markers.
-----------------------------------------------------------------------------------------------------------------
Here is the candidates skill set:
📄 SAMPLE RESUME

📄 RESUME — MANOEL BENICIO

Manoel Benicio
📍 São Paulo, Brazil | 📧 manoel.benicio@icloud.com | 📞 +55 11 99364-4444 | 🌐 linkedin.com/in/manoel-benicio-filho

🎯 Profile
Technology Modernization & Digital Transformation leader with 20+ years delivering enterprise-scale modernization and legacy migration programs. Strong expertise in application modernization, cloud adoption, and emerging technology integration. Proven impact across complex environments, including customer revenue growth (25% to 50.5%), IT cost reduction (37.4%), and system performance improvement (65%). Certified multi-cloud architect with hands-on leadership across AWS, Azure, GCP, and OCI.

🧩 Core Competencies
- Digital Transformation Strategy
- Application Modernization & Legacy Migration
- Cloud Adoption & Technology Roadmaps
- Innovation Leadership & Emerging Technologies
- Technical Debt Reduction & Architecture Governance
- Business Case Development & Executive Communication
- Revenue Growth (25% to 50.5%) and Cost Optimization

💼 Experience

Head Strategic Business Development – Apps & Cloud Modernization
Indra-Tech | São Paulo, Brazil | 2023 – Present
- Managed a diverse engineering team delivering projects across Americas and EMEA.
- Developed products and solutions that increased customer revenue from 25% to 50.5% over 2 years.
- Managed annual budget of $200M, driving a 37.4% reduction in IT expenditure.
- Led cloud modernization initiatives, migrating legacy systems to cloud platforms with improved efficiency.

Sr Data & Analytics Practice Manager
Indra-Tech | São Paulo, Brazil | 2023 – Present
- Oversaw large-scale IT projects in the health services sector with timely execution.
- Led cross-functional teams of data engineers delivering data-driven strategies.
- Reduced project completion time by 25% through agile methodologies.
- Implemented data governance frameworks reducing data errors by 25%.

Head Cloud & Data Professional Services
Andela | New York, USA | 2022 – 2023
- Led developers, security, and infrastructure professionals for cloud and data programs.
- Facilitated successful legacy migrations and upgrades across cloud/data platforms.
- Built a culture of ownership, inclusiveness, accountability, and urgency.
- Delivered solutions aligned to well-architected frameworks.

Sr Cloud Operations Manager
Telefonica Tech | São Paulo, Brazil | 2021 – 2022
- Accelerated customers’ cloud migration journeys and digital transformation programs.
- Reported directly to the COO, managing transformation initiatives end-to-end.
- Orchestrated cloud infrastructure projects with 30% cost decrease and 65% performance increase.
- Negotiated complex cross-stakeholder issues and drove alignment through consensus.

Head Contracts for Cloud Services
Telefonica Tech | São Paulo, Brazil | 2020 – 2021
- Led major B2B contracts for LATAM region at a global insurance client.
- Enabled the sales team to promote new products and solutions.
- Partnered with operations to migrate on-prem applications to public cloud platforms.
- Managed datacenter teams in Brazil and Miami, overseeing CAPEX/OPEX.

Program Manager – Public Safety
NICE | Dallas, USA | 2016 – 2020
- Led developers, security, and infrastructure professionals in public safety programs.
- Acted as main sponsor managing Business Partner contracts (SLAs, performance, training, delivery).
- Managed partners across US regions delivering professional services.
- Collaborated with engineering and product teams to design and deploy NICE solutions.

🎓 Education
- MBA – Solutions Architecture | FIAP | 2020
- Bachelor’s – Computer Systems Networking and Telecommunications | 2017

🛠 Skills (Technical & Leadership)
- Cloud Platforms: AWS, Azure, GCP, OCI
- Modernization: Legacy migration, application modernization, technical debt reduction
- Governance: Architecture governance, roadmap development, data governance
- Delivery & Ops: Cloud operations, large-scale program leadership, cost optimization
- Business & Leadership: Budget ownership, executive communication, business case development

📚 Certifications
- AWS Solution Architect
- AWS Security Specialty
- Azure Solutions Architect
- Azure Cybersecurity Architect
- Azure Security Engineer
- Azure Database Administrator
- Azure Network Engineer
- Oracle Multi-Cloud Architect
- Google Associate Cloud

🚀 Career Goal
To lead enterprise technology modernization initiatives that unlock innovation, reduce technical debt, and position organizations for sustainable competitive advantage.

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------