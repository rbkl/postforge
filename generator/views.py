"""
Views for the LinkedIn Post Generator API.
"""
import json
import os
import re
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import UserProfile, SamplePost, UploadedPDF, ExtractedImage, GeneratedPost
from .serializers import (
    UserProfileSerializer, UserProfileCreateSerializer,
    SamplePostSerializer, UploadedPDFSerializer, 
    ExtractedImageSerializer, GeneratedPostSerializer,
    GeneratePostRequestSerializer
)
from .utils.pdf_processor import PDFProcessor
from .utils.ai_generator import AIGenerator
from .utils.url_scraper import URLScraper
from django.conf import settings


class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user profiles."""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Only return profiles for the current user."""
        if self.request.user.is_authenticated:
            # Try to get profile linked to user, or create one
            profile, created = UserProfile.objects.get_or_create(
                user=self.request.user,
                defaults={'name': self.request.user.get_full_name() or self.request.user.username}
            )
            return UserProfile.objects.filter(user=self.request.user)
        return UserProfile.objects.none()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserProfileCreateSerializer
        return UserProfileSerializer
    
    def perform_create(self, serializer):
        """Link profile to current user."""
        profile = serializer.save(user=self.request.user)
        return profile
    
    @action(detail=True, methods=['post'])
    def add_sample_post(self, request, pk=None):
        """Add a sample post to a profile."""
        profile = self.get_object()
        serializer = SamplePostSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(profile=profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'], url_path='sample-posts/(?P<post_id>[^/.]+)')
    def delete_sample_post(self, request, pk=None, post_id=None):
        """Delete a sample post from a profile."""
        profile = self.get_object()
        sample_post = get_object_or_404(SamplePost, id=post_id, profile=profile)
        sample_post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UploadedPDFViewSet(viewsets.ModelViewSet):
    """ViewSet for managing uploaded PDFs."""
    permission_classes = [IsAuthenticated]
    serializer_class = UploadedPDFSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        """Only return PDFs for the current user."""
        if self.request.user.is_authenticated:
            # Get user's profile
            try:
                profile = UserProfile.objects.get(user=self.request.user)
                return UploadedPDF.objects.filter(profile=profile)
            except UserProfile.DoesNotExist:
                return UploadedPDF.objects.none()
        return UploadedPDF.objects.none()
    
    def perform_create(self, serializer):
        """Link PDF to current user's profile."""
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'name': self.request.user.get_full_name() or self.request.user.username}
        )
        serializer.save(profile=profile)
    
    def create(self, request, *args, **kwargs):
        """Upload and process a PDF file."""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        pdf_file = request.FILES['file']
        
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'name': request.user.get_full_name() or request.user.username}
        )
        
        # Create the PDF record
        pdf_obj = UploadedPDF.objects.create(
            file=pdf_file,
            original_filename=pdf_file.name,
            profile=user_profile
        )
        
        # Process the PDF
        try:
            processor = PDFProcessor(pdf_obj.file.path)
            result = processor.extract_all()
            
            # Update PDF record with extracted data
            pdf_obj.extracted_text = result['text']
            pdf_obj.title = result['metadata'].get('title', '')
            pdf_obj.authors = result['metadata'].get('author', '')
            pdf_obj.abstract = result['metadata'].get('abstract', '')
            pdf_obj.processed = True
            pdf_obj.save()
            
            # Save extracted images - prioritize page_render figures over embedded
            # Sort by source (page_render first) and quality
            sorted_images = sorted(
                result['images'],
                key=lambda x: (
                    0 if x.get('source') == 'page_render' else 1,
                    -x.get('width', 0) * x.get('height', 0)
                )
            )
            
            for i, img_data in enumerate(sorted_images[:12]):  # Limit to 12 images
                try:
                    # Generate descriptive filename
                    source_type = img_data.get('source', 'embedded')
                    image_file = PDFProcessor.save_image_to_file(
                        img_data['image'],
                        f"pdf_{pdf_obj.id}_page{img_data['page']}_{source_type}_{i}.png"
                    )
                    
                    # Higher relevance for page-rendered figures with captions
                    if source_type == 'page_render' and img_data.get('caption'):
                        relevance = 0.8
                    elif img_data.get('is_figure'):
                        relevance = 0.6
                    else:
                        relevance = 0.3
                    
                    ExtractedImage.objects.create(
                        pdf=pdf_obj,
                        image=image_file,
                        page_number=img_data['page'],
                        is_figure=img_data.get('is_figure', False),
                        caption=img_data.get('caption', ''),
                        relevance_score=relevance
                    )
                except Exception as e:
                    print(f"Error saving image: {e}")
                    continue
            
            serializer = self.get_serializer(pdf_obj)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            pdf_obj.delete()
            return Response(
                {'error': f'Error processing PDF: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def images(self, request, pk=None):
        """Get all extracted images for a PDF."""
        pdf = self.get_object()
        images = pdf.extracted_images.all()
        serializer = ExtractedImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_url(request):
    """Submit a URL for content extraction."""
    url = request.data.get('url', '').strip()
    
    if not url:
        return Response(
            {'error': 'URL is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        # Scrape the URL
        scraper = URLScraper(url)
        result = scraper.extract_all()
        
        if not result['success']:
            return Response(
                {'error': result.get('error', 'Failed to fetch URL')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'name': request.user.get_full_name() or request.user.username}
        )
        
        # Create the content record
        # Handle featured_image_url - use None if empty string or missing
        image_url = result.get('image_url') or None
        if image_url == '':
            image_url = None
        
        content_obj = UploadedPDF.objects.create(
            source_type='url',
            source_url=url,
            domain=result.get('domain', ''),
            title=result.get('title', 'Untitled'),
            authors=result.get('author', ''),
            abstract=result.get('description', ''),
            extracted_text=result.get('content', ''),
            featured_image_url=image_url,
            processed=True,
            profile=user_profile
        )
        
        serializer = UploadedPDFSerializer(content_obj, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Error processing URL: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


class GeneratedPostViewSet(viewsets.ModelViewSet):
    """ViewSet for managing generated posts."""
    permission_classes = [IsAuthenticated]
    serializer_class = GeneratedPostSerializer
    
    def get_queryset(self):
        """Only return posts for the current user."""
        if self.request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=self.request.user)
                return GeneratedPost.objects.filter(profile=profile)
            except UserProfile.DoesNotExist:
                return GeneratedPost.objects.none()
        return GeneratedPost.objects.none()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_content(request):
    """Analyze a document and return structured insights.
    
    This is an intermediate step before post generation that helps users
    understand the content and choose what to focus on.
    """
    pdf_id = request.data.get('pdf_id')
    custom_instructions = request.data.get('custom_instructions', '')
    
    if not pdf_id:
        return Response(
            {'error': 'pdf_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    pdf = get_object_or_404(UploadedPDF, id=pdf_id)
    
    if not pdf.processed:
        return Response(
            {'error': 'Content has not been processed yet'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    ai = AIGenerator()
    
    # Get sections from content
    if pdf.source_type == 'pdf':
        processor = PDFProcessor(pdf.file.path)
        processor.text = pdf.extracted_text
        processor.metadata = {
            'title': pdf.title,
            'author': pdf.authors,
            'abstract': pdf.abstract
        }
        sections = processor.get_key_sections()
    else:
        # For URLs, create basic sections
        sections = {
            'abstract': pdf.abstract,
            'introduction': pdf.extracted_text[:2000] if pdf.extracted_text else '',
            'conclusion': ''
        }
    
    metadata = {
        'title': pdf.title,
        'author': pdf.authors,
        'abstract': pdf.abstract
    }
    
    try:
        # Generate the analysis
        analysis_json = ai.summarize_content(
            pdf.extracted_text,
            metadata,
            sections,
            custom_instructions=custom_instructions
        )
        
        # Try to parse as JSON, fall back to raw string
        try:
            import json
            # Clean up potential markdown code blocks
            cleaned = analysis_json.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            analysis = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            analysis = {'raw_analysis': analysis_json}
        
        return Response({
            'pdf_id': str(pdf.id),
            'title': pdf.title,
            'authors': pdf.authors,
            'source_type': pdf.source_type,
            'analysis': analysis,
            'content_preview': pdf.extracted_text[:1000] + '...' if len(pdf.extracted_text) > 1000 else pdf.extracted_text
        })
        
    except Exception as e:
        return Response(
            {'error': f'Analysis failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_post(request):
    """Generate a LinkedIn post from a PDF."""
    serializer = GeneratePostRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Get the PDF - ensure it belongs to the current user
    user_profile = UserProfile.objects.get(user=request.user)
    pdf = get_object_or_404(UploadedPDF, id=data['pdf_id'], profile=user_profile)
    
    if not pdf.processed:
        return Response(
            {'error': 'PDF has not been processed yet'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get profile (use user's profile)
    profile = user_profile
    sample_posts = [p.content for p in profile.sample_posts.all()[:5]]
    profile_custom_instructions = profile.custom_instructions or ''
    
    # Use preferences from request (overrides profile)
    preferences = {
        'tone_preference': data.get('tone_preference', 'professional'),
        'include_emojis': data.get('include_emojis', True),
        'include_hashtags': data.get('include_hashtags', True),
        'post_length_preference': data.get('post_length_preference', 'medium')
    }
    
    # Get custom instructions (from request, or fall back to profile default)
    custom_instructions = data.get('custom_instructions', '')
    if not custom_instructions and profile_custom_instructions:
        custom_instructions = profile_custom_instructions
    
    # Initialize AI generator
    ai = AIGenerator()
    
    # Get metadata and sections based on source type
    metadata = {
        'title': pdf.title,
        'author': pdf.authors,
        'abstract': pdf.abstract
    }
    
    # OPTIMIZATION: Check if we can reuse existing analysis from a recent post
    # This avoids redundant API calls when generating multiple posts from the same content
    analysis = None
    from django.utils import timezone
    from datetime import timedelta
    
    # Try to reuse analysis if:
    # 1. Custom instructions are empty (analysis is content-agnostic)
    # 2. There's a recent post (within last hour) with the same PDF
    if not custom_instructions:
        existing_post = GeneratedPost.objects.filter(
            pdf=pdf,
            summary__isnull=False
        ).exclude(summary='').filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).order_by('-created_at').first()
        
        if existing_post and existing_post.summary:
            # Reuse the analysis - this saves a full API call (~5-10 seconds)
            analysis = existing_post.summary
    
    # Only generate new analysis if we don't have a reusable one
    if not analysis:
        # For URL content, we don't have a PDF file to process
        if pdf.source_type == 'url':
            # URL content already has extracted text, create simple sections
            sections = {
                'main_content': pdf.extracted_text[:5000] if pdf.extracted_text else '',
            }
        else:
            # PDF content - use processor to get sections
            processor = PDFProcessor(pdf.file.path)
            processor.text = pdf.extracted_text
            processor.metadata = metadata
            sections = processor.get_key_sections()
        
        # Generate deep analysis with custom instructions
        analysis = ai.summarize_content(
            pdf.extracted_text,
            metadata,
            sections,
            custom_instructions=custom_instructions
        )
    
    # Generate LinkedIn post - pass BOTH the analysis AND the full content
    post_content = ai.generate_linkedin_post(
        analysis,
        metadata,
        sample_posts,
        preferences,
        custom_instructions=custom_instructions,
        full_content=pdf.extracted_text  # Pass full content for context
    )
    
    # Append source link if requested
    if data.get('include_source_link', False):
        source_url = None
        link_text = None
        
        if pdf.source_type == 'url' and pdf.source_url:
            source_url = pdf.source_url
            link_text = "Link to article"
        elif pdf.source_type == 'pdf':
            # Try to extract ArXiv URL from metadata or text
            # Check if it's an ArXiv paper
            if 'arxiv' in pdf.title.lower() or (pdf.extracted_text and 'arxiv' in pdf.extracted_text.lower()[:1000]):
                # Try to find ArXiv ID in text
                arxiv_match = re.search(r'arxiv[:\s]*(\d{4}\.\d{4,5})', pdf.extracted_text[:2000], re.IGNORECASE)
                if arxiv_match:
                    arxiv_id = arxiv_match.group(1)
                    source_url = f"https://arxiv.org/abs/{arxiv_id}"
                    link_text = "Link to paper"
                # Also check source_url field in case it was set
                elif pdf.source_url:
                    source_url = pdf.source_url
                    link_text = "Link to paper"
            else:
                # Generic PDF - use source_url if available
                if pdf.source_url:
                    source_url = pdf.source_url
                    link_text = "Link to paper"
        
        if source_url:
            post_content += f"\n\n{link_text}: {source_url}"
    
    # Create the generated post record
    generated_post = GeneratedPost.objects.create(
        profile=profile,
        pdf=pdf,
        summary=analysis,
        post_content=post_content
    )
    
    # Handle image selection/generation
    if data.get('use_extracted_image', True):
        # Try to use best extracted image
        best_image = pdf.extracted_images.order_by('-relevance_score', '-is_figure').first()
        if best_image:
            generated_post.selected_image = best_image
            generated_post.save()
    
    # AI image generation removed - only use extracted images from PDF/website
    # if data.get('generate_image', False):
    #     # Generate an AI image
    #     image_url = ai.generate_image(analysis, metadata)
    #     if image_url:
    #         generated_post.generated_image_url = image_url
    #         generated_post.save()
    
    serializer = GeneratedPostSerializer(generated_post, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_post(request, post_id):
    """Regenerate a LinkedIn post with different options."""
    generated_post = get_object_or_404(GeneratedPost, id=post_id)
    
    profile = generated_post.profile
    sample_posts = []
    preferences = {
        'tone_preference': 'professional',
        'include_emojis': True,
        'include_hashtags': True,
        'post_length_preference': 'medium'
    }
    
    if profile:
        sample_posts = [p.content for p in profile.sample_posts.all()[:5]]
        preferences = {
            'tone_preference': profile.tone_preference,
            'include_emojis': profile.include_emojis,
            'include_hashtags': profile.include_hashtags,
            'post_length_preference': profile.post_length_preference
        }
    
    # Override with request data if provided
    for key in ['tone_preference', 'include_emojis', 'include_hashtags', 'post_length_preference']:
        if key in request.data:
            preferences[key] = request.data[key]
    
    ai = AIGenerator()
    
    # Regenerate post
    post_content = ai.generate_linkedin_post(
        generated_post.summary,
        {
            'title': generated_post.pdf.title,
            'author': generated_post.pdf.authors
        },
        sample_posts,
        preferences
    )
    
    generated_post.post_content = post_content
    generated_post.save()
    
    serializer = GeneratedPostSerializer(generated_post, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refine_post(request, post_id):
    """Refine an existing LinkedIn post based on user feedback.
    
    This keeps the full document context and allows iterative editing.
    """
    generated_post = get_object_or_404(GeneratedPost, id=post_id)
    
    refinement_prompt = request.data.get('refinement_prompt', '').strip()
    if not refinement_prompt:
        return Response(
            {'error': 'Refinement prompt is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    ai = AIGenerator()
    
    # Get metadata for context
    metadata = {
        'title': generated_post.pdf.title,
        'author': generated_post.pdf.authors
    }
    
    try:
        # Refine the post with FULL document context
        refined_content = ai.refine_post(
            current_post=generated_post.post_content,
            refinement_prompt=refinement_prompt,
            content_analysis=generated_post.summary,
            metadata=metadata,
            full_content=generated_post.pdf.extracted_text  # Pass full document!
        )
        
        generated_post.post_content = refined_content
        generated_post.save()
        
        serializer = GeneratedPostSerializer(generated_post, context={'request': request})
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_prompts(request):
    """Return all prompts used by the tool for transparency."""
    
    # Get current provider info
    provider = getattr(settings, 'LLM_PROVIDER', 'deepseek')
    ai = AIGenerator()
    
    prompts = {
        'provider': provider,
        'model': ai.chat_model,
        'prompts': [
            {
                'id': 'analyze',
                'name': 'Content Analysis (Executive Briefing)',
                'description': 'Extracts CONCRETE, DATA-DRIVEN findings from documents for C-suite executives. Every claim must be backed by specific numbers, sample sizes, or direct quotes. No fluffy language or vague predictions.',
                'system_prompt': 'You are a senior research analyst preparing executive briefings. Your job is to extract ONLY concrete, data-backed findings. Never use vague language like "transformative", "revolutionary", or "game-changing". Every claim must cite specific numbers, sample sizes, or direct quotes from the source material. If data isn\'t available for a point, explicitly state "Data not provided in source." You always respond with valid JSON.',
                'user_prompt_template': '''You are a senior research analyst preparing a briefing for C-suite executives. Extract CONCRETE, DATA-DRIVEN insights from this content.

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
   
   Tailor section names to the document type (e.g., news articles: Context, Main Story, Expert Opinions)

3. KEY DATA POINTS (5-7 items):
   Extract the most important quantitative findings. For each:
   - State the specific metric/finding with exact numbers
   - Include methodology context (sample size, time period, comparison baseline)
   - Note any limitations or caveats mentioned
   
   BAD: "Significant cost savings were achieved"
   GOOD: "Operating costs decreased 23% ($4.2M annually) over 18 months, measured across 47 facilities vs. control group"

4. EXECUTIVE IMPLICATIONS:
   What should a CEO/CFO/CTO actually DO with this information? Be specific:
   - Financial impact: What's the potential ROI, cost, or revenue implication?
   - Operational impact: What processes or resources would need to change?
   - Timeline: When would results be expected based on the data?
   - Risk factors: What could go wrong? What are the documented failure cases?

5. METHODOLOGY & CREDIBILITY:
   - How was this research conducted?
   - Who conducted it? (Institution, potential conflicts of interest)
   - What are the stated limitations?

6. QUOTABLE FACTS (3 items):
   The 3 most striking, specific facts directly from the document.

Format as JSON with keys: core_finding, document_sections (array), key_data_points (array), executive_implications (object), methodology (object), quotable_facts (array)''',
                'variables': ['context (title, source, full content)', 'custom_angle (user\'s specific focus/perspective)']
            },
            {
                'id': 'generate',
                'name': 'LinkedIn Post Generation',
                'description': 'Creates high-engagement LinkedIn posts styled like top tech thought leaders. Has access to BOTH the AI analysis AND the full document text to pull specific quotes, numbers, and details.',
                'system_prompt': '''You are a top LinkedIn content creator known for posts that get massive engagement. Your style:
- You find the non-obvious angle that makes people stop scrolling
- You teach specific, actionable insights (not generic advice)
- You write with authority but stay accessible
- You use concrete numbers, examples, and details
- You challenge conventional thinking when the evidence supports it
- Your hooks are irresistible - they create genuine curiosity

CRITICAL: LinkedIn does NOT support markdown. Output plain text only. No **, no *, no # headers. Use line breaks, numbers, and emojis for formatting.''',
                'user_prompt_template': '''Create a high-engagement LinkedIn post about this content.

SOURCE: {title}
BY: {source}

AI ANALYSIS & KEY INSIGHTS:
{analysis}

FULL DOCUMENT CONTENT (use this to pull specific quotes, numbers, and details):
{full_content} [up to 8000 chars of the actual document]

STYLE REQUIREMENTS:
{preferences}
{style_examples}
{custom_angle}

WRITE LIKE TOP LINKEDIN CREATORS:

1. HOOK (First 2 lines - make them STOP scrolling):
   - Start with a surprising fact, counterintuitive claim, or bold statement
   - Use patterns like: "Everyone thinks X. They're wrong."

2. BODY (Deliver REAL value - not generic fluff):
   - Use numbered points or clear line breaks for scannability
   - Each point should teach something SPECIFIC
   - Pull specific quotes, numbers, or examples from the document
   - Include at least one "most people don't realize" insight

3. CLOSE (Drive engagement):
   - End with a thought-provoking question or clear takeaway

FORMATTING (No markdown - LinkedIn doesn't support it):
• Plain text ONLY
• Use line breaks generously
• Numbers (1. 2. 3.) and arrows (→) for lists
• Emojis for visual breaks

Output ONLY the post content.''',
                'variables': ['title', 'source', 'analysis (deep insights from step 1)', 'full_content (up to 8000 chars of actual document)', 'preferences', 'style_examples', 'custom_angle']
            },
            {
                'id': 'refine',
                'name': 'Post Refinement',
                'description': 'Iteratively refines posts based on user feedback. Has access to the FULL document to pull additional quotes, numbers, or details during refinement.',
                'system_prompt': 'You are an expert LinkedIn content editor who makes posts more engaging while keeping them specific and valuable. You have access to the full document to pull specific quotes, numbers, and details. You never water down insights into generic advice. LinkedIn does NOT support markdown - output plain text only.',
                'user_prompt_template': '''You are a top LinkedIn content editor helping refine a post for maximum engagement.

ORIGINAL CONTENT CONTEXT:
Title: {title}
Source: {source}

AI Analysis:
{analysis}

FULL DOCUMENT (reference for specific quotes/details):
{full_content} [up to 6000 chars of actual document]

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

Output ONLY the refined post. No explanations.''',
                'variables': ['title', 'source', 'analysis', 'full_content (up to 6000 chars)', 'current_post', 'refinement_prompt']
            }
        ]
    }
    
    return Response(prompts)

