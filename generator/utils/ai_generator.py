"""
AI integration for generating LinkedIn posts and images.
Supports multiple LLM providers: OpenAI, DeepSeek.
"""
import os
import re
import json
import requests
from typing import Dict, List, Optional
from django.conf import settings


class AIGenerator:
    """Generate LinkedIn posts and images using LLM APIs (OpenAI or DeepSeek)."""
    
    # Provider configurations
    PROVIDERS = {
        'openai': {
            'base_url': 'https://api.openai.com/v1',
            'chat_model': 'gpt-4o',
            'supports_images': True
        },
        'deepseek': {
            'base_url': 'https://api.deepseek.com',
            'chat_model': 'deepseek-chat',
            'supports_images': False  # DeepSeek doesn't have image generation
        }
    }
    
    # Class-level session for connection pooling
    _session = None
    
    @classmethod
    def _get_session(cls):
        """Get or create a requests session for connection pooling."""
        if cls._session is None:
            cls._session = requests.Session()
            # Configure session for better performance
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=20,
                max_retries=2
            )
            cls._session.mount('http://', adapter)
            cls._session.mount('https://', adapter)
        return cls._session
    
    def __init__(self, provider: str = None):
        """Initialize the AI generator with specified provider.
        
        Args:
            provider: LLM provider ('openai' or 'deepseek'). Defaults to settings.LLM_PROVIDER.
        """
        self.provider = provider or getattr(settings, 'LLM_PROVIDER', 'deepseek')
        
        if self.provider not in self.PROVIDERS:
            raise ValueError(f"Unsupported provider: {self.provider}. Choose from: {list(self.PROVIDERS.keys())}")
        
        self.config = self.PROVIDERS[self.provider]
        self.base_url = self.config['base_url']
        self.chat_model = self.config['chat_model']
        
        # Set API key based on provider
        if self.provider == 'deepseek':
            self.api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
        else:
            self.api_key = getattr(settings, 'OPENAI_API_KEY', '')
        
    def _make_request(self, endpoint: str, payload: Dict) -> Dict:
        """Make a request to the LLM API with connection pooling."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        session = self._get_session()
        response = session.post(
            f"{self.base_url}/{endpoint}",
            headers=headers,
            json=payload,
            timeout=120
        )
        
        if response.status_code != 200:
            raise Exception(f"{self.provider.title()} API error: {response.text}")
        
        return response.json()
    
    def summarize_content(self, text: str, metadata: Dict, sections: Dict, custom_instructions: str = '') -> str:
        """Generate a deep analysis of any document (paper, article, news story, etc.).
        
        Args:
            text: Full text of the document
            metadata: Document metadata (title, authors/source, etc.)
            sections: Extracted sections (abstract, intro, conclusion if available)
            custom_instructions: User's custom angle/perspective for the analysis
        """
        
        # Prepare context
        context_parts = []
        
        if metadata.get('title'):
            context_parts.append(f"Title: {metadata['title']}")
        
        if metadata.get('author'):
            context_parts.append(f"Source/Author: {metadata['author']}")
        
        if sections.get('abstract'):
            context_parts.append(f"Summary/Abstract: {sections['abstract'][:2000]}")
        
        if sections.get('introduction'):
            context_parts.append(f"Opening section: {sections['introduction'][:2000]}")
        
        if sections.get('conclusion'):
            context_parts.append(f"Conclusion/Key points: {sections['conclusion'][:2000]}")
        
        # Add main text - optimized to reduce token usage while maintaining quality
        # Reduced from 15000 to 12000 chars to speed up API calls
        if len('\n'.join(context_parts)) < 8000:
            remaining = 12000 - len('\n'.join(context_parts))
            context_parts.append(f"Full content: {text[:remaining]}")
        
        context = '\n\n'.join(context_parts)
        
        # Build the prompt with optional custom instructions
        custom_angle = ""
        if custom_instructions:
            custom_angle = f"""
USER'S SPECIFIC ANGLE/FOCUS:
{custom_instructions}

Tailor your analysis to emphasize this perspective while maintaining accuracy.
"""
        
        prompt = f"""You are a senior research analyst preparing a briefing for C-suite executives. Extract CONCRETE, DATA-DRIVEN insights from this content.

CONTENT TO ANALYZE:
{context}
{custom_angle}
CRITICAL RULES:
- NO fluffy language ("transformative", "paradigm shift", "revolutionize", "game-changing")
- NO vague predictions ("this will impact X, Y, Z")
- EVERY claim must be backed by specific data, numbers, or direct quotes from the document
- If the document doesn't provide data for a point, say "Data not provided" rather than speculating

Extract the following:

1. CORE FINDING (2-3 sentences):
   - What is the primary claim or discovery?
   - What specific evidence supports it? (Include exact numbers, sample sizes, percentages, dollar amounts)
   - Example format: "The study found that X increased by 47% (n=1,200, p<0.05) when Y was implemented."

2. DOCUMENT SECTIONS (provide a detailed breakdown of 4-8 key sections):
   For each major section or topic covered in the document:
   - section_title: A clear title for this section/topic
   - summary: 2-4 sentences explaining what this section covers and its key points
   - key_details: 2-3 bullet points with specific facts, data, or arguments from this section
   
   Example sections might include: Introduction/Background, Methodology, Results, Case Studies, Discussion, Conclusions, etc.
   Tailor to what's actually in the document - news articles might have: Context, Main Story, Expert Opinions, Implications, etc.

3. KEY DATA POINTS (5-7 items):
   Extract the most important quantitative findings. For each:
   - State the specific metric/finding with exact numbers
   - Include methodology context (sample size, time period, comparison baseline)
   - Note any limitations or caveats mentioned
   
   BAD: "Significant cost savings were achieved"
   GOOD: "Operating costs decreased 23% ($4.2M annually) over 18 months, measured across 47 facilities vs. control group of 12 facilities"

4. EXECUTIVE IMPLICATIONS:
   What should a CEO/CFO/CTO actually DO with this information? Be specific:
   - Financial impact: What's the potential ROI, cost, or revenue implication? Use numbers from the document.
   - Operational impact: What processes or resources would need to change?
   - Timeline: When would results be expected based on the data?
   - Risk factors: What could go wrong? What are the documented failure cases or limitations?

5. METHODOLOGY & CREDIBILITY:
   - How was this research conducted? (Sample size, duration, methodology)
   - Who conducted it? (Institution, potential conflicts of interest)
   - What are the stated limitations?
   - How does this compare to prior work? (If mentioned)

6. QUOTABLE FACTS (3 items):
   Pull the 3 most striking, specific facts that would make an executive pay attention.
   These must be DIRECTLY from the document - no paraphrasing into vague statements.
   
   BAD: "AI is becoming more important"
   GOOD: "Companies using AI-assisted decision making saw 34% faster time-to-market (median 6.2 vs 9.4 months, n=89 product launches)"

Format as JSON with keys: core_finding, document_sections (array of objects with "section_title", "summary", "key_details"), key_data_points (array of objects with "finding", "context", "limitations"), executive_implications (object with "financial", "operational", "timeline", "risks"), methodology (object with "approach", "credibility", "limitations", "prior_work"), quotable_facts (array)"""

        if not self.api_key:
            # Return a mock response for testing without API key
            return json.dumps({
                "core_finding": f"'{metadata.get('title', 'This content')}' presents findings based on [specific methodology]. The primary result shows [X metric] changed by [Y%] compared to baseline (n=[sample size], measured over [time period]).",
                "document_sections": [
                    {
                        "section_title": "Introduction & Background",
                        "summary": "Sets the context for the research by explaining the current state of the field and identifying the gap this work addresses. Establishes why this topic matters for practitioners and researchers.",
                        "key_details": ["Previous approaches achieved only 23% efficiency", "Market size estimated at $4.7B by 2025", "No prior study examined this specific combination"]
                    },
                    {
                        "section_title": "Methodology",
                        "summary": "Details the research design including participant selection, data collection methods, and analysis approach. Uses a randomized controlled trial with 1,200 participants across 47 facilities over 18 months.",
                        "key_details": ["Randomized controlled trial design", "1,200 participants, 47 facilities", "18-month observation period with monthly data collection"]
                    },
                    {
                        "section_title": "Key Results",
                        "summary": "Presents the primary findings showing significant improvements across all measured metrics. The intervention group outperformed control on efficiency, cost, and satisfaction measures.",
                        "key_details": ["47% improvement in primary metric (p<0.05)", "Cost reduction of $4.2M annually", "Customer satisfaction increased 12 NPS points"]
                    },
                    {
                        "section_title": "Case Studies",
                        "summary": "Three detailed examples of organizations that implemented the approach, showing real-world application and results. Includes both success stories and challenges encountered.",
                        "key_details": ["Company A: Full implementation in 6 months, 52% improvement", "Company B: Partial rollout, 31% improvement with legacy system constraints", "Company C: Failed implementation due to change management issues"]
                    },
                    {
                        "section_title": "Discussion & Implications",
                        "summary": "Interprets the results in the context of existing literature and practical applications. Addresses limitations and suggests areas for future research.",
                        "key_details": ["Results consistent with prior work but magnitude larger", "Implementation challenges primarily organizational not technical", "ROI timeline of 14 months for typical enterprise"]
                    },
                    {
                        "section_title": "Conclusions & Recommendations",
                        "summary": "Summarizes key takeaways and provides actionable recommendations for practitioners. Emphasizes the importance of change management alongside technical implementation.",
                        "key_details": ["Start with pilot program of 90 days", "Dedicated team of 3-5 FTEs required", "Executive sponsorship critical for success"]
                    }
                ],
                "key_data_points": [
                    {"finding": "Primary metric improved 47% vs control", "context": "n=1,200 participants over 18 months, randomized controlled trial", "limitations": "Self-reported data, single geographic region"},
                    {"finding": "Cost reduction of $4.2M annually", "context": "Measured across 47 facilities, compared to 12 control facilities", "limitations": "Does not account for implementation costs"},
                    {"finding": "Time-to-completion decreased from 9.4 to 6.2 months (34% faster)", "context": "89 product launches tracked, Fortune 500 companies only", "limitations": "Selection bias toward well-resourced teams"},
                    {"finding": "Customer satisfaction scores increased 12 points (NPS)", "context": "Survey of 5,400 customers pre/post implementation", "limitations": "6-month follow-up only"},
                    {"finding": "Error rate dropped from 8.3% to 2.1%", "context": "Automated tracking system, 100K+ transactions analyzed", "limitations": "Excludes edge cases requiring manual review"}
                ],
                "executive_implications": {
                    "financial": "Based on documented results, similar implementation could yield $2-5M annual savings for mid-size enterprise (extrapolated from per-facility figures). Break-even expected at 14 months.",
                    "operational": "Requires dedicated team of 3-5 FTEs for 6-month implementation. Existing systems need API integration (estimated 200 dev hours).",
                    "timeline": "Pilot results visible in 90 days. Full deployment 6-9 months. ROI measurable at 18 months based on study timeline.",
                    "risks": "23% of pilot participants reported integration challenges. 8% abandoned implementation due to legacy system incompatibility. Change management cited as primary barrier."
                },
                "methodology": {
                    "approach": "Randomized controlled trial with stratified sampling",
                    "credibility": "Published in peer-reviewed journal. Authors affiliated with [Institution]. No disclosed conflicts of interest.",
                    "limitations": "Single industry focus. Western market data only. Pre-2024 data may not reflect current conditions.",
                    "prior_work": "Builds on 2022 study by [Author] which found similar directional results (32% vs 47% improvement)."
                },
                "quotable_facts": [
                    "Organizations implementing this approach saw 47% improvement in primary metric (n=1,200, p<0.05)",
                    "Average cost savings of $4.2M annually across 47 facilities vs control group",
                    "34% reduction in time-to-market (6.2 vs 9.4 months median, 89 product launches tracked)"
                ]
            })
        
        try:
            response = self._make_request("chat/completions", {
                "model": self.chat_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior research analyst preparing executive briefings. Your job is to extract ONLY concrete, data-backed findings. Never use vague language like 'transformative', 'revolutionary', or 'game-changing'. Every claim must cite specific numbers, sample sizes, or direct quotes from the source material. If data isn't available for a point, explicitly state 'Data not provided in source.' You always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.5,
                "max_tokens": 2000  # Reduced from 2500 to speed up response
            })
            
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Error in summarize_content ({self.provider}): {e}")
            return json.dumps({
                "core_finding": f"Analysis failed for: {metadata.get('title', 'Unknown Title')}",
                "key_data_points": [{"finding": "Analysis could not be completed", "context": "Please try again", "limitations": "N/A"}],
                "executive_implications": {"financial": "N/A", "operational": "N/A", "timeline": "N/A", "risks": "N/A"},
                "methodology": {"approach": "N/A", "credibility": "N/A", "limitations": "N/A", "prior_work": "N/A"},
                "quotable_facts": ["Analysis unavailable - please retry"]
            })
    
    # Keep old method name for backwards compatibility
    def summarize_paper(self, text: str, metadata: Dict, sections: Dict, custom_instructions: str = '') -> str:
        """Backwards compatible wrapper for summarize_content."""
        return self.summarize_content(text, metadata, sections, custom_instructions)
    
    def generate_linkedin_post(
        self,
        analysis: str,
        metadata: Dict,
        sample_posts: List[str],
        preferences: Dict,
        custom_instructions: str = '',
        full_content: str = ''
    ) -> str:
        """Generate a LinkedIn post based on content analysis and user style.
        
        Args:
            analysis: AI-generated analysis/insights from the content
            metadata: Content metadata (title, source/authors, etc.)
            sample_posts: User's sample posts for style matching
            preferences: Generation preferences (tone, length, emojis, hashtags)
            custom_instructions: User's custom angle/perspective
            full_content: The complete extracted text from the document (for reference)
        """
        
        # Build style guidance from sample posts
        style_examples = ""
        if sample_posts:
            style_examples = "\n\nMATCH THIS WRITING STYLE (user's previous posts):\n"
            for i, post in enumerate(sample_posts[:5], 1):
                style_examples += f"\n--- Example {i} ---\n{post}\n"
        
        # Build preference instructions
        pref_instructions = []
        
        tone_map = {
            'professional': 'authoritative yet accessible - like a senior expert sharing insights',
            'casual': 'conversational and relatable - like texting a smart friend',
            'thought_leader': 'bold and visionary - challenge conventional thinking',
            'educational': 'teaching mode - break down complex ideas step by step',
            'storytelling': 'narrative-driven - use story structure and concrete examples'
        }
        
        pref_instructions.append(f"Tone: {tone_map.get(preferences.get('tone_preference', 'professional'), 'professional')}")
        
        if preferences.get('include_emojis', True):
            pref_instructions.append("Use emojis strategically for visual breaks and emphasis (not excessively)")
        else:
            pref_instructions.append("Do not use emojis")
        
        if preferences.get('include_hashtags', True):
            pref_instructions.append("End with 3-5 relevant hashtags")
        else:
            pref_instructions.append("Do not include hashtags")
        
        length_map = {
            'short': 'Concise and punchy - under 500 characters. Every word earns its place.',
            'medium': 'Substantial but scannable - 500-1500 characters with clear structure',
            'long': 'Deep dive - 1500+ characters with detailed breakdown and multiple insights'
        }
        pref_instructions.append(length_map.get(preferences.get('post_length_preference', 'medium'), 'Substantial but scannable'))
        
        # Add custom angle if provided
        custom_angle_section = ""
        if custom_instructions:
            custom_angle_section = f"""
USER'S SPECIFIC ANGLE/FOCUS:
{custom_instructions}

Frame the entire post around this perspective.
"""
        
        # Include truncated full content for reference (to pull specific quotes/details)
        # OPTIMIZATION: Reduced from 8000 to 6000 chars to speed up API calls
        full_content_section = ""
        if full_content:
            # Include up to 6000 chars of the full content for specific details
            truncated_content = full_content[:6000]
            if len(full_content) > 6000:
                truncated_content += "\n... [content truncated for length]"
            full_content_section = f"""

FULL DOCUMENT CONTENT (use this to pull specific quotes, numbers, and details):
{truncated_content}
"""
        
        prompt = f"""Create a high-engagement LinkedIn post about this content.

SOURCE: {metadata.get('title', 'Content')}
BY: {metadata.get('author', 'Unknown')}

EXECUTIVE ANALYSIS (use these concrete data points):
{analysis}
{full_content_section}

STYLE REQUIREMENTS:
{chr(10).join('• ' + p for p in pref_instructions)}
{style_examples}
{custom_angle_section}

YOUR POST MUST:
1. Lead with a SPECIFIC data point or finding (use exact numbers from the analysis)
2. Include at least 2-3 concrete statistics, percentages, or dollar figures
3. Explain what this means for executives/decision-makers (use the executive_implications from the analysis)
4. Cite methodology context where relevant (sample size, timeframe) to build credibility

STRUCTURE:

1. HOOK (First 2 lines):
   - Open with the most striking statistic or finding
   - Example: "47% improvement. 18 months. $4.2M saved. Here's the data nobody's talking about:"

2. BODY (The substance):
   - Present 3-5 key findings WITH their numbers
   - For each, briefly explain what it means practically
   - Use the quotable_facts and key_data_points from the analysis
   - Include context (sample size, methodology) to add credibility
   - Add executive implications: "For a mid-size company, this translates to..."

3. CLOSE:
   - One concrete takeaway or action
   - A specific question that invites discussion about the data

CRITICAL FORMATTING (LinkedIn has NO markdown support):
• Plain text ONLY - no **, no *, no # headers, no [links](url)
• Use line breaks generously for readability
• Use → or • for bullet points
• Numbers (1. 2. 3.) work great for lists
• Emojis sparingly for visual breaks

BAD EXAMPLE (fluffy, no data):
"This study is transformative! It's going to revolutionize how we think about AI. Companies need to pay attention. The implications are huge!"

GOOD EXAMPLE (specific, data-driven):
"47% improvement in primary metric.
$4.2M annual savings.
89 product launches analyzed.

I just went through the data from this study, and here's what executives need to know:

1. Time-to-market dropped 34% (from 9.4 to 6.2 months median)
→ For context: this was across Fortune 500 companies only

2. The cost reduction wasn't small - $4.2M annually measured across 47 facilities
→ Important caveat: doesn't include implementation costs (estimated 14-month break-even)

3. Error rates fell from 8.3% to 2.1% based on 100K+ transactions
→ Though edge cases requiring manual review were excluded

What's the catch? 23% of pilots reported integration challenges. Legacy systems remain the biggest barrier.

For CFOs: The data suggests 6-9 month deployment timeline with ROI measurable at 18 months.

Is your team's hesitation costing more than the implementation?"

Output ONLY the post content. No explanations."""

        if not self.api_key:
            # Return a mock response for testing without API key (plain text, no markdown)
            title = metadata.get('title', 'Interesting Content')
            return f"""Everyone is talking about this. Almost nobody understands why it actually matters.

I just went deep on "{title}" and here's what I found:

The surface-level take misses the real story.

Here's what's actually happening:

1→ The conventional wisdom is being challenged by new data
2→ This has second-order effects most people aren't seeing  
3→ Early movers will have a significant advantage

The hidden insight nobody is discussing:

Most coverage focuses on the obvious. But the methodology reveals something counterintuitive - our assumptions about this space may be fundamentally wrong.

What this means for you:
• If you're in this field, the playbook is changing
• The window to adapt is shorter than you think
• Action beats analysis right now

I'm curious - are you seeing this shift in your work?

Drop your take below 👇

#Innovation #Strategy #Insights #Leadership"""

        try:
            response = self._make_request("chat/completions", {
                "model": self.chat_model,
                "messages": [
                    {
                        "role": "system",
                        "content": """You are a top LinkedIn content creator known for posts that get massive engagement. Your style:
- You find the non-obvious angle that makes people stop scrolling
- You teach specific, actionable insights (not generic advice)
- You write with authority but stay accessible
- You use concrete numbers, examples, and details
- You challenge conventional thinking when the evidence supports it
- Your hooks are irresistible - they create genuine curiosity

CRITICAL: LinkedIn does NOT support markdown. Output plain text only. No **, no *, no # headers. Use line breaks, numbers, and emojis for formatting."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.85,
                "max_tokens": 1200  # Reduced from 1500 to speed up response
            })
            
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Error in generate_linkedin_post ({self.provider}): {e}")
            return f"📚 Interesting content: {metadata.get('title', 'Check this out')}\n\n[Post generation encountered an error. Please try again.]"
    
    # AI image generation removed - only extract images from PDFs/websites
    # def generate_image(self, summary: str, metadata: Dict) -> Optional[str]:
    #     """Generate an image for the LinkedIn post using DALL-E."""
    #     ... (removed - only use extracted images from PDF/website)
    
    def refine_post(
        self,
        current_post: str,
        refinement_prompt: str,
        content_analysis: str,
        metadata: Dict,
        full_content: str = ''
    ) -> str:
        """Refine an existing LinkedIn post based on user feedback.
        
        Args:
            current_post: The current version of the post
            refinement_prompt: User's instructions for how to refine the post
            content_analysis: The AI-generated analysis for context
            metadata: Content metadata (title, source, etc.)
            full_content: The complete extracted text from the document
        
        Returns:
            The refined post content
        """
        
        # Include truncated full content for specific details
        full_content_section = ""
        if full_content:
            truncated_content = full_content[:6000]
            if len(full_content) > 6000:
                truncated_content += "\n... [content truncated]"
            full_content_section = f"""

FULL DOCUMENT (reference for specific quotes/details):
{truncated_content}
"""
        
        prompt = f"""You are a top LinkedIn content editor helping refine a post for maximum engagement.

ORIGINAL CONTENT CONTEXT:
Title: {metadata.get('title', 'Content')}
Source: {metadata.get('author', 'Unknown')}

AI Analysis:
{content_analysis[:2500]}
{full_content_section}

CURRENT POST VERSION:
{current_post}

USER'S REFINEMENT REQUEST:
{refinement_prompt}

REFINEMENT GUIDELINES:
1. Apply the user's requested changes precisely
2. Maintain the specific insights and details - don't make it more generic
3. Keep the hook strong (or make it stronger if that's the request)
4. Ensure every point delivers real value, not fluff
5. Preserve accuracy to the source content
6. You can pull specific quotes, numbers, or details from the full document if helpful

FORMATTING (LinkedIn has NO markdown):
• Plain text only - no **, no *, no # headers
• Use line breaks for readability
• Numbers (1. 2. 3.) and arrows (→) work well
• Emojis are fine for visual breaks

Output ONLY the refined post. No explanations or meta-commentary."""

        if not self.api_key:
            # Return a mock refined response for testing
            return f"{current_post}\n\n[Refined based on: {refinement_prompt}]"
        
        try:
            response = self._make_request("chat/completions", {
                "model": self.chat_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert LinkedIn content editor who makes posts more engaging while keeping them specific and valuable. You have access to the full document to pull specific quotes, numbers, and details. You never water down insights into generic advice. LinkedIn does NOT support markdown - output plain text only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1500
            })
            
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Error in refine_post ({self.provider}): {e}")
            raise Exception(f"Failed to refine post: {str(e)}")
    
    def rank_images(self, images_info: List[Dict], paper_summary: str) -> List[Dict]:
        """Rank extracted images by relevance for LinkedIn post."""
        
        if not images_info:
            return []
        
        # Simple heuristic ranking if no API key
        if not self.api_key:
            ranked = []
            for i, img in enumerate(images_info):
                score = 0.5
                if img.get('is_figure'):
                    score += 0.3
                # Prefer images from first few pages (likely main figures)
                if img.get('page', 0) <= 3:
                    score += 0.2
                # Prefer larger images
                if img.get('width', 0) > 300 and img.get('height', 0) > 300:
                    score += 0.1
                
                ranked.append({**img, 'relevance_score': min(score, 1.0)})
            
            return sorted(ranked, key=lambda x: x['relevance_score'], reverse=True)
        
        # Use AI to rank if we have API key
        try:
            # For simplicity, use heuristics enhanced with basic checks
            ranked = []
            for img in images_info:
                score = 0.3
                if img.get('is_figure'):
                    score += 0.4
                if img.get('page', 0) <= 5:
                    score += 0.2
                if img.get('width', 0) > 400:
                    score += 0.1
                
                ranked.append({**img, 'relevance_score': min(score, 1.0)})
            
            return sorted(ranked, key=lambda x: x['relevance_score'], reverse=True)
        except Exception as e:
            print(f"Error ranking images: {e}")
            return images_info

