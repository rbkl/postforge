from django.contrib import admin
from .models import UserProfile, SamplePost, UploadedPDF, ExtractedImage, GeneratedPost


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'headline', 'tone_preference', 'created_at']
    search_fields = ['name', 'headline']


@admin.register(SamplePost)
class SamplePostAdmin(admin.ModelAdmin):
    list_display = ['profile', 'content_preview', 'created_at']
    list_filter = ['profile']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content


@admin.register(UploadedPDF)
class UploadedPDFAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'title', 'processed', 'uploaded_at']
    list_filter = ['processed']


@admin.register(ExtractedImage)
class ExtractedImageAdmin(admin.ModelAdmin):
    list_display = ['pdf', 'page_number', 'is_figure', 'relevance_score']
    list_filter = ['is_figure']


@admin.register(GeneratedPost)
class GeneratedPostAdmin(admin.ModelAdmin):
    list_display = ['pdf', 'profile', 'created_at']
    list_filter = ['profile']




