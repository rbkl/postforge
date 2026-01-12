"""
Serializers for the LinkedIn Post Generator API.
"""
from rest_framework import serializers
from .models import UserProfile, SamplePost, UploadedPDF, ExtractedImage, GeneratedPost


class SamplePostSerializer(serializers.ModelSerializer):
    class Meta:
        model = SamplePost
        fields = ['id', 'content', 'engagement_notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    sample_posts = SamplePostSerializer(many=True, read_only=True)
    sample_posts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'name', 'headline', 'industry', 
            'tone_preference', 'include_emojis', 'include_hashtags',
            'post_length_preference', 'custom_instructions',
            'sample_posts', 'sample_posts_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_sample_posts_count(self, obj):
        return obj.sample_posts.count()


class UserProfileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'name', 'headline', 'industry', 
            'tone_preference', 'include_emojis', 'include_hashtags',
            'post_length_preference', 'custom_instructions'
        ]


class ExtractedImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ExtractedImage
        fields = ['id', 'page_number', 'is_figure', 'caption', 'relevance_score', 'image_url']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class UploadedPDFSerializer(serializers.ModelSerializer):
    extracted_images = ExtractedImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = UploadedPDF
        fields = [
            'id', 'source_type', 'original_filename', 'source_url', 'domain',
            'title', 'authors', 'abstract', 'featured_image_url',
            'uploaded_at', 'processed', 'extracted_images'
        ]
        read_only_fields = ['id', 'title', 'authors', 'abstract', 'uploaded_at', 'processed']


class GeneratedPostSerializer(serializers.ModelSerializer):
    pdf_title = serializers.CharField(source='pdf.title', read_only=True)
    selected_image_data = ExtractedImageSerializer(source='selected_image', read_only=True)
    
    class Meta:
        model = GeneratedPost
        fields = [
            'id', 'pdf', 'pdf_title', 'summary', 'post_content',
            'selected_image', 'selected_image_data', 
            'generated_image_url', 'generated_image',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class GeneratePostRequestSerializer(serializers.Serializer):
    """Serializer for post generation request."""
    pdf_id = serializers.UUIDField()
    profile_id = serializers.UUIDField(required=False, allow_null=True)
    generate_image = serializers.BooleanField(default=False)
    use_extracted_image = serializers.BooleanField(default=True)
    
    # Custom instructions for summarization angle
    custom_instructions = serializers.CharField(required=False, allow_blank=True, default='')
    
    # Generation options (override profile settings)
    tone_preference = serializers.ChoiceField(
        choices=['professional', 'casual', 'thought_leader', 'educational', 'storytelling'],
        default='professional',
        required=False
    )
    post_length_preference = serializers.ChoiceField(
        choices=['short', 'medium', 'long'],
        default='medium',
        required=False
    )
    include_emojis = serializers.BooleanField(default=True, required=False)
    include_hashtags = serializers.BooleanField(default=True, required=False)
    include_source_link = serializers.BooleanField(default=False, required=False)

