from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import UserFollow, Profile
from .badges import BADGE_MAP, compute_badges, get_badge_info


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    username  = request.data.get('username', '').strip()
    password  = request.data.get('password', '')
    password2 = request.data.get('password2', '')

    if not username:
        return Response({'detail': '아이디를 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(username) < 3:
        return Response({'detail': '아이디는 3자 이상이어야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(password) < 8:
        return Response({'detail': '비밀번호는 8자 이상이어야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    if password != password2:
        return Response({'detail': '비밀번호가 일치하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({'detail': '이미 사용 중인 아이디입니다.'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password)
    login(request, user)
    return Response({'username': user.username, 'id': user.id}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response({'detail': '아이디와 비밀번호를 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({'detail': '아이디 또는 비밀번호가 올바르지 않습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

    login(request, user)
    return Response({'username': user.username, 'id': user.id})


@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({'detail': '로그아웃 되었습니다.'})


# ensure_csrf_cookie: 모든 페이지 로드 시 이 엔드포인트를 호출해 CSRF 쿠키를 설정한다
@api_view(['GET'])
@ensure_csrf_cookie
def me(request):
    if request.user.is_authenticated:
        return Response({
            'username': request.user.username,
            'id': request.user.id,
            'badge': get_badge_info(request.user),
        })
    return Response({'detail': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_badge(request):
    """POST /api/accounts/me/badge/ — 대표 칭호 선택/해제 (body: {badge_id: id 또는 null})"""
    badge_id = request.data.get('badge_id') or ''
    if badge_id and badge_id not in BADGE_MAP:
        return Response({'detail': '존재하지 않는 칭호입니다.'}, status=status.HTTP_400_BAD_REQUEST)
    if badge_id:
        earned_ids = {b['id'] for b in compute_badges(request.user) if b['earned']}
        if badge_id not in earned_ids:
            return Response({'detail': '아직 달성하지 않은 칭호입니다.'}, status=status.HTTP_400_BAD_REQUEST)

    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.selected_badge = badge_id
    profile.save()
    return Response({'badge': get_badge_info(request.user)})


@api_view(['GET'])
def profile_detail(request, username):
    """GET /api/accounts/profile/<username>/ — 프로필 정보 조회"""
    target = get_object_or_404(User, username=username)

    reviews = target.reviews.select_related('place').order_by('-created_at')[:20]
    bookmarks = target.bookmarks.filter(place__isnull=False).select_related('place').order_by('-created_at')[:20]

    follower_count  = target.followers_set.count()
    following_count = target.following_set.count()

    is_following = False
    is_self = False
    if request.user.is_authenticated:
        is_self = request.user == target
        if not is_self:
            is_following = UserFollow.objects.filter(follower=request.user, following=target).exists()

    routes_qs = target.routes.filter(is_footprint=False).prefetch_related('routeplace_set__place').order_by('-created_at')
    if not is_self:
        routes_qs = routes_qs.filter(is_shared=True)

    footprints_qs = target.routes.filter(is_footprint=True).prefetch_related('routeplace_set__place').order_by('-created_at')
    if not is_self:
        footprints_qs = footprints_qs.filter(is_shared=True)

    reviews_data = [
        {
            'id': r.id,
            'place_id': r.place.id,
            'place_name': r.place.name,
            'rating': r.rating,
            'content': r.content,
            'created_at': r.created_at.strftime('%Y.%m.%d'),
        }
        for r in reviews
    ]
    bookmarks_data = [
        {
            'bookmark_id': b.id,
            'place_id': b.place.id,
            'place_name': b.place.name,
            'place_image': b.place.image_url,
            'category': b.place.get_category_display(),
        }
        for b in bookmarks
    ]
    routes_data = [
        {
            'id': r.id,
            'title': r.title,
            'mode': r.get_mode_display(),
            'is_shared': r.is_shared,
            'like_count': r.like_count,
            'total_distance': r.total_distance,
            'total_time': r.total_time,
            'created_at': r.created_at.strftime('%Y.%m.%d'),
            'place_names': [rp.place.name for rp in r.routeplace_set.all()[:6]],
        }
        for r in routes_qs[:20]
    ]
    footprints_data = [
        {
            'id': r.id,
            'title': r.title,
            'total_distance': r.total_distance,
            'total_time': r.total_time,
            'created_at': r.created_at.strftime('%Y.%m.%d'),
            'place_names': [rp.place.name for rp in r.routeplace_set.all()[:6]],
        }
        for r in footprints_qs[:30]
    ]
    badges_data = compute_badges(target)
    earned_ids = {b['id'] for b in badges_data if b['earned']}
    try:
        selected_badge_id = target.profile.selected_badge
    except Profile.DoesNotExist:
        selected_badge_id = ''
    if selected_badge_id not in earned_ids:
        selected_badge_id = ''

    return Response({
        'username': target.username,
        'email': target.email if is_self else '',
        'badge': get_badge_info(target),
        'selected_badge': selected_badge_id,
        'follower_count': follower_count,
        'following_count': following_count,
        'is_following': is_following,
        'is_self': is_self,
        'reviews': reviews_data,
        'bookmarks': bookmarks_data,
        'routes': routes_data,
        'footprints': footprints_data,
        'badges': badges_data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_toggle(request, username):
    """POST /api/accounts/profile/<username>/follow/ — 팔로우 토글"""
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return Response({'detail': '자신을 팔로우할 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
    follow, created = UserFollow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        follow.delete()
        following = False
    else:
        following = True
    return Response({
        'following': following,
        'follower_count': target.followers_set.count(),
    })
