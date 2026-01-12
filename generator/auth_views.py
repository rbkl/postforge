"""
Authentication views for user registration, login, and session management.
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import UserProfile


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user."""
    username = request.data.get('username', '').strip()
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')
    name = request.data.get('name', '').strip()
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if email and User.objects.filter(email=email).exists():
        return Response(
            {'error': 'Email already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )
    
    # Create user profile
    profile = UserProfile.objects.create(
        user=user,
        name=name or username
    )
    
    # Log the user in
    login(request, user)
    
    return Response({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        },
        'profile': {
            'id': str(profile.id),
            'name': profile.name,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login a user."""
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(request, username=username, password=password)
    
    if user is None:
        return Response(
            {'error': 'Invalid username or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    login(request, user)
    
    # Get or create profile
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={'name': user.get_full_name() or user.username}
    )
    
    return Response({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        },
        'profile': {
            'id': str(profile.id),
            'name': profile.name,
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout the current user."""
    logout(request)
    return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Get the current authenticated user."""
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.get_full_name() or request.user.username}
    )
    
    return Response({
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
        },
        'profile': {
            'id': str(profile.id),
            'name': profile.name,
        },
        'is_authenticated': True
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def check_auth(request):
    """Check if user is authenticated (for frontend)."""
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'name': request.user.get_full_name() or request.user.username}
        )
        return Response({
            'is_authenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
            },
            'profile': {
                'id': str(profile.id),
                'name': profile.name,
            }
        })
    return Response({'is_authenticated': False})

