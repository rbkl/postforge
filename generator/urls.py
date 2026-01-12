"""
API URL configuration for the generator app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profiles', views.UserProfileViewSet, basename='profile')
router.register(r'pdfs', views.UploadedPDFViewSet, basename='pdf')
router.register(r'posts', views.GeneratedPostViewSet, basename='post')

from . import auth_views

urlpatterns = [
    path('', include(router.urls)),
    # Authentication endpoints
    path('auth/register/', auth_views.register, name='register'),
    path('auth/login/', auth_views.login_view, name='login'),
    path('auth/logout/', auth_views.logout_view, name='logout'),
    path('auth/current-user/', auth_views.current_user, name='current-user'),
    path('auth/check/', auth_views.check_auth, name='check-auth'),
    # API endpoints
    path('analyze/', views.analyze_content, name='analyze-content'),
    path('generate/', views.generate_post, name='generate-post'),
    path('regenerate/<uuid:post_id>/', views.regenerate_post, name='regenerate-post'),
    path('refine/<uuid:post_id>/', views.refine_post, name='refine-post'),
    path('prompts/', views.get_prompts, name='get-prompts'),
    path('submit-url/', views.submit_url, name='submit-url'),
]

