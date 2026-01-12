"""
URL Scraper for extracting content from web pages.
Supports news articles, blog posts, and general web content.
"""
import re
import requests
import random
from typing import Dict, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup


class URLScraper:
    """Extract content from web URLs for LinkedIn post generation."""
    
    # Common selectors for main content
    CONTENT_SELECTORS = [
        'article',
        '[role="main"]',
        '.post-content',
        '.article-content',
        '.entry-content',
        '.content-body',
        '.story-body',
        '.article-body',
        'main',
        '.main-content',
        # News site specific
        '.article-text',
        '.article-body-text',
        '.story-content',
        '.post-body',
        '.entry',
        '#content',
        '#main-content',
        '.content',
        '.text-content',
        # Insurance Journal specific
        '.article-detail',
        '.article-content-wrapper',
    ]
    
    # Selectors to remove (ads, navigation, etc.)
    REMOVE_SELECTORS = [
        'nav', 'header', 'footer', 'aside',
        '.advertisement', '.ad', '.ads', '.sidebar',
        '.comments', '.comment-section', '.social-share',
        '.related-posts', '.recommended', '.newsletter',
        'script', 'style', 'noscript', 'iframe',
        '.nav', '.menu', '.footer', '.header',
    ]
    
    # User agents to rotate for better success rate
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    def __init__(self, url: str):
        """Initialize with URL to scrape."""
        self.url = url
        self.soup = None
        self.html = None
        self.error_message = None
        
    def fetch(self) -> bool:
        """Fetch the URL content with anti-bot protection bypass."""
        # Try multiple user agents if needed
        for attempt in range(3):
            try:
                headers = {
                    'User-Agent': random.choice(self.USER_AGENTS),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                    'Sec-CH-UA': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    'Sec-CH-UA-Mobile': '?0',
                    'Sec-CH-UA-Platform': '"macOS"',
                }
                
                # Create a session for cookie handling
                session = requests.Session()
                response = session.get(self.url, headers=headers, timeout=30, allow_redirects=True)
                
                if response.status_code == 403:
                    # Some sites need a cookie from an initial request
                    print(f"Got 403, attempt {attempt + 1}/3, trying again...")
                    continue
                    
                response.raise_for_status()
                self.html = response.text
                self.soup = BeautifulSoup(self.html, 'html.parser')
                return True
                
            except requests.exceptions.HTTPError as e:
                self.error_message = f"HTTP {e.response.status_code}: The website blocked our request. Try a different URL."
                print(f"Error fetching URL (attempt {attempt + 1}): {e}")
            except requests.exceptions.ConnectionError as e:
                self.error_message = "Could not connect to the website. Please check the URL."
                print(f"Connection error: {e}")
            except requests.exceptions.Timeout:
                self.error_message = "The website took too long to respond. Please try again."
                print("Request timeout")
            except Exception as e:
                self.error_message = f"Error fetching URL: {str(e)}"
                print(f"Error fetching URL: {e}")
        
        return False
    
    def extract_title(self) -> str:
        """Extract the page title."""
        if not self.soup:
            return ""
        
        # Try Open Graph title first
        og_title = self.soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        # Try Twitter title
        twitter_title = self.soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            return twitter_title['content'].strip()
        
        # Try h1
        h1 = self.soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        # Fall back to title tag
        title = self.soup.find('title')
        if title:
            return title.get_text().strip()
        
        return "Untitled"
    
    def extract_author(self) -> str:
        """Extract the author name."""
        if not self.soup:
            return ""
        
        # Try various meta tags
        author_metas = [
            ('meta', {'name': 'author'}),
            ('meta', {'property': 'article:author'}),
            ('meta', {'name': 'twitter:creator'}),
        ]
        
        for tag, attrs in author_metas:
            meta = self.soup.find(tag, attrs)
            if meta and meta.get('content'):
                return meta['content'].strip()
        
        # Try common author selectors
        author_selectors = [
            '.author', '.byline', '.author-name', 
            '[rel="author"]', '.post-author',
            '[itemprop="author"]', '.article-author',
        ]
        
        for selector in author_selectors:
            author = self.soup.select_one(selector)
            if author:
                text = author.get_text().strip()
                # Clean up "By Author Name" patterns
                text = re.sub(r'^by\s+', '', text, flags=re.IGNORECASE)
                if text and len(text) < 100:  # Sanity check
                    return text
        
        return ""
    
    def extract_description(self) -> str:
        """Extract the meta description."""
        if not self.soup:
            return ""
        
        # Try Open Graph description
        og_desc = self.soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
        
        # Try meta description
        meta_desc = self.soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        return ""
    
    def extract_date(self) -> str:
        """Extract the publication date."""
        if not self.soup:
            return ""
        
        date_metas = [
            ('meta', {'property': 'article:published_time'}),
            ('meta', {'name': 'date'}),
            ('meta', {'name': 'publish-date'}),
            ('time', {'datetime': True}),
        ]
        
        for tag, attrs in date_metas:
            element = self.soup.find(tag, attrs)
            if element:
                if tag == 'time':
                    return element.get('datetime', element.get_text()).strip()
                elif element.get('content'):
                    return element['content'].strip()
        
        return ""
    
    def extract_main_content(self) -> str:
        """Extract the main text content."""
        if not self.soup:
            return ""
        
        # Create a copy to modify
        soup_copy = BeautifulSoup(str(self.soup), 'html.parser')
        
        # Remove unwanted elements
        for selector in self.REMOVE_SELECTORS:
            for element in soup_copy.select(selector):
                element.decompose()
        
        # Try to find main content area
        main_content = None
        for selector in self.CONTENT_SELECTORS:
            main_content = soup_copy.select_one(selector)
            if main_content:
                break
        
        # Fall back to body if no main content found
        if not main_content:
            main_content = soup_copy.find('body')
        
        if not main_content:
            return ""
        
        # Extract text from paragraphs and other content elements
        paragraphs = main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div'])
        
        text_parts = []
        seen_texts = set()  # Avoid duplicates
        
        for p in paragraphs:
            text = p.get_text().strip()
            # Filter out very short lines (likely navigation, etc.)
            # But be more lenient - reduce threshold from 30 to 20
            if len(text) > 20 and text not in seen_texts:
                # Skip if it looks like navigation/menu
                if any(skip in text.lower() for skip in ['home', 'about', 'contact', 'privacy', 'terms', 'cookie', 'subscribe', 'login', 'sign up']):
                    if len(text) < 50:  # Only skip short navigation-like text
                        continue
                text_parts.append(text)
                seen_texts.add(text)
        
        # If we didn't get much content, try getting all text from main_content
        if len('\n\n'.join(text_parts)) < 200:
            all_text = main_content.get_text(separator='\n\n', strip=True)
            # Clean up excessive whitespace
            all_text = re.sub(r'\n{3,}', '\n\n', all_text)
            if len(all_text) > 200:
                return all_text
        
        result = '\n\n'.join(text_parts)
        
        # Final check - if still too short, return what we have
        if len(result) < 100:
            # Last resort: get all text from body
            body_text = soup_copy.find('body')
            if body_text:
                result = body_text.get_text(separator='\n\n', strip=True)
                result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result
    
    def extract_image(self) -> Optional[str]:
        """Extract the main/featured image URL."""
        if not self.soup:
            return None
        
        # Try Open Graph image
        og_image = self.soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']
        
        # Try Twitter image
        twitter_image = self.soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            return twitter_image['content']
        
        return None
    
    def get_domain(self) -> str:
        """Get the domain name from the URL."""
        parsed = urlparse(self.url)
        return parsed.netloc.replace('www.', '')
    
    def extract_all(self) -> Dict:
        """Extract all content from the URL."""
        if not self.soup and not self.fetch():
            return {
                'success': False,
                'error': self.error_message or 'Failed to fetch URL',
                'url': self.url,
            }
        
        title = self.extract_title()
        author = self.extract_author()
        content = self.extract_main_content()
        description = self.extract_description()
        date = self.extract_date()
        image = self.extract_image()
        domain = self.get_domain()
        
        # Validate that we got meaningful content
        if not content or len(content.strip()) < 100:
            # Try one more time with a different approach
            if self.soup:
                # Get all text from body as fallback
                body = self.soup.find('body')
                if body:
                    content = body.get_text(separator='\n\n', strip=True)
                    content = re.sub(r'\n{3,}', '\n\n', content)
                    # Remove common non-content patterns
                    lines = content.split('\n\n')
                    filtered_lines = []
                    for line in lines:
                        line = line.strip()
                        if len(line) > 20 and not any(skip in line.lower() for skip in ['cookie', 'privacy policy', 'terms of service', 'subscribe to newsletter']):
                            filtered_lines.append(line)
                    content = '\n\n'.join(filtered_lines)
        
        # If still no content, return error
        if not content or len(content.strip()) < 100:
            return {
                'success': False,
                'error': 'Could not extract meaningful content from the page. The page may require JavaScript to load content, or the content structure is not recognized.',
                'url': self.url,
            }
        
        # If author not found, use domain as source
        if not author:
            author = domain
        
        return {
            'success': True,
            'url': self.url,
            'title': title,
            'author': author,
            'description': description,
            'content': content,
            'date': date,
            'image_url': image,
            'domain': domain,
            'metadata': {
                'title': title,
                'author': author,
                'abstract': description,
            }
        }



