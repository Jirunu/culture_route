import re
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import UserFollow, Profile
from .badges import BADGE_MAP, compute_badges, get_badge_info
from .utils import get_display_name, get_avatar_url

NICKNAME_RE = re.compile(r'^[가-힣a-zA-Z0-9]+$')


def _validate_nickname(nickname):
    """닉네임 규칙 검증. 통과하면 None, 위반하면 에러 메시지 반환."""
    if ' ' in nickname:
        return '닉네임에 공백을 포함할 수 없습니다.'
    if len(nickname) < 2:
        return '닉네임은 2자 이상이어야 합니다.'
    if len(nickname) > 10:
        return '닉네임은 10자 이하여야 합니다.'
    if not NICKNAME_RE.match(nickname):
        return '닉네임은 한글·영문·숫자만 사용할 수 있습니다.'
    return None


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    username  = request.data.get('username', '').strip()
    password  = request.data.get('password', '')
    password2 = request.data.get('password2', '')
    nickname  = (request.data.get('nickname') or '').strip()

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

    if nickname:
        err = _validate_nickname(nickname)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        if Profile.objects.filter(nickname__iexact=nickname).exists():
            return Response({'detail': '이미 사용 중인 닉네임입니다.'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password)
    if nickname:
        Profile.objects.create(user=user, nickname=nickname)
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
        try:
            nickname = request.user.profile.nickname
        except Profile.DoesNotExist:
            nickname = None
        return Response({
            'username': request.user.username,
            'id': request.user.id,
            'nickname': nickname,
            'display_name': get_display_name(request.user),
            'avatar_url': get_avatar_url(request.user),
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_nickname(request):
    """POST /api/accounts/me/nickname/ — 닉네임 설정/변경 (body: {nickname: str 또는 null/빈 문자열로 해제})"""
    raw = request.data.get('nickname')
    nickname = (raw or '').strip()

    if not nickname:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.nickname = None
        profile.save()
        return Response({'nickname': None, 'display_name': get_display_name(request.user)})

    err = _validate_nickname(nickname)
    if err:
        return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
    if Profile.objects.filter(nickname__iexact=nickname).exclude(user=request.user).exists():
        return Response({'detail': '이미 사용 중인 닉네임입니다.'}, status=status.HTTP_400_BAD_REQUEST)

    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.nickname = nickname
    profile.save()
    return Response({'nickname': nickname, 'display_name': get_display_name(request.user)})


@api_view(['GET'])
@permission_classes([AllowAny])
def check_nickname(request):
    """GET /api/accounts/check-nickname/?nickname=<값> — 닉네임 사용 가능 여부"""
    nickname = (request.query_params.get('nickname') or '').strip()
    err = _validate_nickname(nickname)
    if err:
        return Response({'available': False, 'detail': err})

    qs = Profile.objects.filter(nickname__iexact=nickname)
    if request.user.is_authenticated:
        qs = qs.exclude(user=request.user)
    if qs.exists():
        return Response({'available': False, 'detail': '이미 사용 중인 닉네임입니다.'})
    return Response({'available': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_profile_image(request):
    """POST /api/accounts/me/profile-image/ — multipart/form-data { image: <file> }"""
    image = request.FILES.get('image')
    if not image:
        return Response({'detail': '이미지 파일이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.profile_image = image
    profile.save()
    return Response({'avatar_url': get_avatar_url(request.user)})


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
    try:
        nickname = target.profile.nickname
    except Profile.DoesNotExist:
        nickname = None

    return Response({
        'username': target.username,
        'nickname': nickname,
        'display_name': get_display_name(target),
        'avatar_url': get_avatar_url(target),
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


# -----------------------------------------------
# 간편 로그인 (카카오 / 네이버 / 구글)
# -----------------------------------------------
SOCIAL_PROVIDERS = {
    'kakao': {
        'authorize_url': 'https://kauth.kakao.com/oauth/authorize',
        'token_url':     'https://kauth.kakao.com/oauth/token',
        'userinfo_url':  'https://kapi.kakao.com/v2/user/me',
        'client_id_setting':     'KAKAO_REST_KEY',
        'client_secret_setting': 'KAKAO_CLIENT_SECRET',
        'scope': 'account_email profile_nickname',
    },
    'naver': {
        'authorize_url': 'https://nid.naver.com/oauth2.0/authorize',
        'token_url':     'https://nid.naver.com/oauth2.0/token',
        'userinfo_url':  'https://openapi.naver.com/v1/nid/me',
        'client_id_setting':     'NAVER_CLIENT_ID',
        'client_secret_setting': 'NAVER_CLIENT_SECRET',
        'scope': '',
    },
    'google': {
        'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url':     'https://oauth2.googleapis.com/token',
        'userinfo_url':  'https://www.googleapis.com/oauth2/v3/userinfo',
        'client_id_setting':     'GOOGLE_CLIENT_ID',
        'client_secret_setting': 'GOOGLE_CLIENT_SECRET',
        'scope': 'openid email profile',
    },
}


def _social_redirect_uri(request, provider):
    return request.build_absolute_uri(reverse('social_callback', args=[provider]))


def social_login_start(request, provider):
    """GET /api/accounts/social/<provider>/ — 소셜 로그인 인가 페이지로 리다이렉트"""
    cfg = SOCIAL_PROVIDERS.get(provider)
    if not cfg:
        raise Http404

    client_id = getattr(settings, cfg['client_id_setting'], '')
    if not client_id:
        return redirect('/login/?social_error=' + provider)

    state = secrets.token_urlsafe(16)
    request.session[f'oauth_state_{provider}'] = state

    next_url = request.GET.get('next', '')
    if next_url.startswith('/'):
        request.session[f'oauth_next_{provider}'] = next_url

    params = {
        'client_id':     client_id,
        'redirect_uri':  _social_redirect_uri(request, provider),
        'response_type': 'code',
        'state':         state,
    }
    if cfg['scope']:
        params['scope'] = cfg['scope']
    return redirect(f"{cfg['authorize_url']}?{urlencode(params)}")


def _extract_social_profile(provider, info):
    """제공자별 응답에서 (uid, email, nickname) 추출"""
    if provider == 'kakao':
        account = info.get('kakao_account', {})
        uid = str(info['id'])
        email = account.get('email', '')
        nickname = account.get('profile', {}).get('nickname', '') or info.get('properties', {}).get('nickname', '')
        return uid, email, nickname
    if provider == 'naver':
        r = info.get('response', {})
        return str(r.get('id')), r.get('email', ''), r.get('nickname', '')
    if provider == 'google':
        return str(info.get('sub')), info.get('email', ''), info.get('name', '')
    raise ValueError(provider)


def _get_or_create_social_user(provider, uid, email, nickname):
    username = f'{provider}_{uid}'
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email or ''},
    )
    if created and nickname:
        profile, _ = Profile.objects.get_or_create(user=user)
        candidate = nickname.strip()[:30]
        if len(candidate) >= 2 and not Profile.objects.filter(nickname__iexact=candidate).exists():
            profile.nickname = candidate
            profile.save()
    return user


def social_login_callback(request, provider):
    """GET /api/accounts/social/<provider>/callback/ — 인가 코드 교환 → 로그인 처리"""
    cfg = SOCIAL_PROVIDERS.get(provider)
    if not cfg:
        raise Http404

    code = request.GET.get('code')
    state = request.GET.get('state')
    saved_state = request.session.pop(f'oauth_state_{provider}', None)
    if not code or not saved_state or state != saved_state:
        return redirect('/login/?social_error=' + provider)

    client_id = getattr(settings, cfg['client_id_setting'], '')
    client_secret = getattr(settings, cfg['client_secret_setting'], '')
    token_data = {
        'grant_type':   'authorization_code',
        'client_id':    client_id,
        'redirect_uri': _social_redirect_uri(request, provider),
        'code':         code,
    }
    if client_secret:
        token_data['client_secret'] = client_secret

    try:
        token_resp = requests.post(
            cfg['token_url'], data=token_data,
            headers={'Accept': 'application/json'}, timeout=8,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()['access_token']

        user_resp = requests.get(
            cfg['userinfo_url'],
            headers={'Authorization': f'Bearer {access_token}'}, timeout=8,
        )
        user_resp.raise_for_status()
        info = user_resp.json()
        uid, email, nickname = _extract_social_profile(provider, info)
    except (requests.RequestException, KeyError, ValueError):
        return redirect('/login/?social_error=' + provider)

    user = _get_or_create_social_user(provider, uid, email, nickname)
    login(request, user)
    next_url = request.session.pop(f'oauth_next_{provider}', None) or '/'
    return redirect(next_url)
