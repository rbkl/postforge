"""
Models for the LinkedIn Post Generator.
"""
from django.db import models
import uuid


class UserProfile(models.Model):
    """User profile for storing LinkedIn posting preferences."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='user_profile',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255)
    headline = models.CharField(max_length=500, blank=True, help_text="Your LinkedIn headline")
    industry = models.CharField(max_length=255, blank=True, help_text="Your industry/field")
    tone_preference = models.CharField(
        max_length=100,
        choices=[
            ('professional', 'Professional'),
            ('casual', 'Casual & Conversational'),
            ('thought_leader', 'Thought Leadership'),
            ('educational', 'Educational'),
            ('storytelling', 'Storytelling'),
        ],
        default='professional'
    )
    include_emojis = models.BooleanField(default=True)
    include_hashtags = models.BooleanField(default=True)
    post_length_preference = models.CharField(
        max_length=50,
        choices=[
            ('short', 'Short (< 500 chars)'),
            ('medium', 'Medium (500-1500 chars)'),
            ('long', 'Long (1500+ chars)'),
        ],
        default='medium'
    )
    custom_instructions = models.TextField(
        blank=True,
        help_text="Default custom instructions/angle for post generation (e.g., 'Focus on practical applications for startups')"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']


class SamplePost(models.Model):
    """Sample LinkedIn posts to learn user's writing style."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='sample_posts'
    )
    content = models.TextField(help_text="The full text of your LinkedIn post")
    engagement_notes = models.TextField(
        blank=True,
        help_text="Optional: Notes about engagement (likes, comments) to help prioritize style"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.profile.name}'s post: {self.content[:50]}..."
    
    class Meta:
        ordering = ['-created_at']


class UploadedPDF(models.Model):
    """Uploaded PDF files or URL content for processing."""
    
    SOURCE_TYPE_CHOICES = [
        ('pdf', 'PDF File'),
        ('url', 'Web URL'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='uploaded_pdfs',
        null=True,
        blank=True
    )
    # Source type
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES, default='pdf')
    
    # PDF-specific fields
    file = models.FileField(upload_to='pdfs/', blank=True, null=True)
    original_filename = models.CharField(max_length=500, blank=True)
    
    # URL-specific fields
    source_url = models.URLField(max_length=2000, blank=True)
    domain = models.CharField(max_length=255, blank=True)
    featured_image_url = models.URLField(max_length=2000, blank=True, null=True)
    
    # Common fields
    title = models.CharField(max_length=500, blank=True)
    authors = models.TextField(blank=True)
    abstract = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    
    def __str__(self):
        if self.source_type == 'url':
            return self.title or self.source_url
        return self.original_filename or str(self.id)
    
    class Meta:
        ordering = ['-uploaded_at']


class ExtractedImage(models.Model):
    """Images extracted from PDFs."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pdf = models.ForeignKey(
        UploadedPDF,
        on_delete=models.CASCADE,
        related_name='extracted_images'
    )
    image = models.ImageField(upload_to='extracted_images/')
    page_number = models.IntegerField()
    is_figure = models.BooleanField(default=False, help_text="Is this a figure/chart?")
    caption = models.TextField(blank=True)
    relevance_score = models.FloatField(default=0.0, help_text="AI-determined relevance for LinkedIn")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image from page {self.page_number} of {self.pdf.original_filename}"
    
    class Meta:
        ordering = ['-relevance_score', 'page_number']


class GeneratedPost(models.Model):
    """Generated LinkedIn posts."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='generated_posts',
        null=True,
        blank=True
    )
    pdf = models.ForeignKey(
        UploadedPDF,
        on_delete=models.CASCADE,
        related_name='generated_posts'
    )
    summary = models.TextField(help_text="AI-generated summary of the paper")
    post_content = models.TextField(help_text="Generated LinkedIn post content")
    selected_image = models.ForeignKey(
        ExtractedImage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_in_posts'
    )
    generated_image_url = models.URLField(blank=True, help_text="URL of AI-generated image")
    generated_image = models.ImageField(upload_to='generated_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Post for {self.pdf.original_filename}"
    
    class Meta:
        ordering = ['-created_at']

