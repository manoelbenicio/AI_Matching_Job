"""
LinkedIn Job Fetcher - Extract job details from LinkedIn URLs
Uses requests with proper headers to fetch public job data
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import json
from typing import Optional, Dict, Any


class LinkedInJobFetcher:
    """Fetch job details from LinkedIn job posting URLs"""
    
    def __init__(self):
        self.session = requests.Session()
        # Use headers that mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def extract_job_id(self, url: str) -> Optional[str]:
        """
        Extract job ID from various LinkedIn URL formats:
        - https://www.linkedin.com/jobs/view/1234567890
        - https://www.linkedin.com/jobs/search/?currentJobId=1234567890&...
        - https://www.linkedin.com/jobs/collections/recommended/?currentJobId=1234567890
        """
        if not url:
            return None
            
        # Pattern 1: /jobs/view/JOB_ID
        match = re.search(r'/jobs/view/(\d+)', url)
        if match:
            return match.group(1)
        
        # Pattern 2: currentJobId=JOB_ID in query string
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if 'currentJobId' in params:
            return params['currentJobId'][0]
        
        return None
    
    def fetch_job_details(self, url: str) -> Dict[str, Any]:
        """
        Fetch job details from a LinkedIn URL.
        Returns dict with: company_name, job_title, location, job_description, job_url
        """
        result = {
            'success': False,
            'company_name': '',
            'job_title': '',
            'location': '',
            'job_description': '',
            'job_url': url,
            'error': None
        }
        
        job_id = self.extract_job_id(url)
        if not job_id:
            result['error'] = 'Could not extract job ID from URL'
            return result
        
        # Construct direct job view URL
        direct_url = f'https://www.linkedin.com/jobs/view/{job_id}'
        result['job_url'] = direct_url
        
        try:
            # First try the public guest view URL (no login required)
            guest_url = f'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}'
            response = self.session.get(guest_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                result = self._parse_guest_job_page(soup, result)
            else:
                # Fallback: try the regular job view page
                response = self.session.get(direct_url, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    result = self._parse_job_page(soup, result)
                else:
                    result['error'] = f'LinkedIn returned status {response.status_code}'
                    
        except requests.exceptions.Timeout:
            result['error'] = 'Request timed out - LinkedIn may be blocking requests'
        except requests.exceptions.RequestException as e:
            result['error'] = f'Network error: {str(e)}'
        except Exception as e:
            result['error'] = f'Parsing error: {str(e)}'
        
        return result
    
    def _parse_guest_job_page(self, soup: BeautifulSoup, result: Dict) -> Dict:
        """Parse the LinkedIn guest/public job API response"""
        try:
            # Job title
            title_elem = soup.find('h2', class_='top-card-layout__title')
            if title_elem:
                result['job_title'] = title_elem.get_text(strip=True)
            
            # Company name  
            company_elem = soup.find('a', class_='topcard__org-name-link')
            if not company_elem:
                company_elem = soup.find('span', class_='topcard__flavor')
            if company_elem:
                result['company_name'] = company_elem.get_text(strip=True)
            
            # Location
            location_elem = soup.find('span', class_='topcard__flavor--bullet')
            if location_elem:
                result['location'] = location_elem.get_text(strip=True)
            
            # Job description
            desc_elem = soup.find('div', class_='description__text')
            if not desc_elem:
                desc_elem = soup.find('div', class_='show-more-less-html__markup')
            if desc_elem:
                # Get text with basic formatting preserved
                result['job_description'] = desc_elem.get_text(separator='\n', strip=True)
            
            if result['job_title'] and result['company_name']:
                result['success'] = True
            else:
                result['error'] = 'Could not find all required fields'
                
        except Exception as e:
            result['error'] = f'Parsing error: {str(e)}'
        
        return result
    
    def _parse_job_page(self, soup: BeautifulSoup, result: Dict) -> Dict:
        """Parse the regular LinkedIn job view page"""
        try:
            # Try to find job title from various selectors
            title_selectors = [
                'h1.top-card-layout__title',
                'h1.topcard__title', 
                'h1[class*="job-title"]',
                '.job-details-jobs-unified-top-card__job-title'
            ]
            for selector in title_selectors:
                elem = soup.select_one(selector)
                if elem:
                    result['job_title'] = elem.get_text(strip=True)
                    break
            
            # Company name
            company_selectors = [
                'a.topcard__org-name-link',
                '.topcard__flavor a',
                '.job-details-jobs-unified-top-card__company-name',
                'span.topcard__org-name'
            ]
            for selector in company_selectors:
                elem = soup.select_one(selector)
                if elem:
                    result['company_name'] = elem.get_text(strip=True)
                    break
            
            # Location
            location_selectors = [
                'span.topcard__flavor--bullet',
                '.job-details-jobs-unified-top-card__primary-description-container span:nth-child(1)',
                '.topcard__flavor:not(:has(a))'
            ]
            for selector in location_selectors:
                elem = soup.select_one(selector)
                if elem:
                    loc_text = elem.get_text(strip=True)
                    if loc_text and 'ago' not in loc_text.lower():
                        result['location'] = loc_text
                        break
            
            # Job description
            desc_selectors = [
                '.description__text',
                '.show-more-less-html__markup',
                '.jobs-description__content',
                'div[class*="job-description"]'
            ]
            for selector in desc_selectors:
                elem = soup.select_one(selector)
                if elem:
                    result['job_description'] = elem.get_text(separator='\n', strip=True)
                    break
            
            # Check if we got enough data
            if result['job_title'] or result['company_name'] or result['job_description']:
                result['success'] = True
            else:
                result['error'] = 'Page loaded but could not extract job details - may need login'
                
        except Exception as e:
            result['error'] = f'Parsing error: {str(e)}'
        
        return result
    
    def is_linkedin_url(self, url: str) -> bool:
        """Check if URL is a LinkedIn job URL"""
        if not url:
            return False
        return 'linkedin.com/jobs' in url.lower()


def fetch_linkedin_job(url: str) -> Dict[str, Any]:
    """Convenience function to fetch job details from LinkedIn URL"""
    fetcher = LinkedInJobFetcher()
    return fetcher.fetch_job_details(url)


if __name__ == '__main__':
    # Test with example URL
    test_url = "https://www.linkedin.com/jobs/view/4357596542"
    print(f"Testing with URL: {test_url}")
    result = fetch_linkedin_job(test_url)
    print(f"Success: {result['success']}")
    print(f"Title: {result['job_title']}")
    print(f"Company: {result['company_name']}")
    print(f"Location: {result['location']}")
    print(f"Description length: {len(result['job_description'])} chars")
    if result['error']:
        print(f"Error: {result['error']}")
