import re

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import UserFollow
from culture.models import Place, Route, RoutePlace


# ── 칭호(badge) 시스템 ──────────────────────────────────
# 발자취(완료한 여행)에 포함된 장소를 집계해 칭호 달성 여부를 계산한다.

def _is_temple(name):
    clean = re.sub(r'[\(\[（【][^\)\]）】]*[\)\]）】]', '', name).strip()
    return (
        clean.endswith('사') or clean.endswith('암') or clean.endswith('절') or
        '선원' in name or '사찰' in name or clean.endswith('정사') or clean.endswith('도량')
    )


_WAR_KEYWORDS = ['전쟁', '전투', '순국', '전적비', '산성', '격전']


def _is_war_related(place):
    return (
        any(k in place.name for k in _WAR_KEYWORDS) or
        any(k in (place.description or '') for k in _WAR_KEYWORDS)
    )


BADGE_DEFS = [
    {'id': 'first_step',          'name': '첫 발걸음',              'flavor': '여행의 첫 페이지를 펼쳤어요.',                       'tier': '아주 쉬움', 'key': 'total',              'threshold': 1},
    {'id': 'goryeo_loyalist',     'name': '고려 충신',              'flavor': '고려 유적 찾아 삼만리.',                            'tier': '아주 쉬움', 'key': 'era_goryeo',         'threshold': 2},
    {'id': 'samguk_fan',          'name': '삼국시대 덕후',           'flavor': '백제·신라·고구려, 다 가봤음.',                        'tier': '쉬움',      'key': 'era_three_kingdoms', 'threshold': 4},
    {'id': 'neighborhood_walker', 'name': '동네 산책러',             'flavor': '우리 동네 문화 마실, 이제 시작이죠.',                  'tier': '쉬움',      'key': 'total',              'threshold': 5},
    {'id': 'war_maniac',          'name': '전쟁광',                 'flavor': '전쟁 유적만 보면 발걸음이 빨라진다.',                  'tier': '쉬움',      'key': 'war',                'threshold': 4},
    {'id': 'modern_hunter',       'name': '모던 컬처 헌터',           'flavor': '요즘 감성도 놓치지 않는 센스.',                       'tier': '쉬움',      'key': 'era_modern',         'threshold': 6},
    {'id': 'indoor_culture',      'name': '실내파 문화인',           'flavor': '냉방 빵빵한 곳만 골라다니는 센스.',                    'tier': '보통',      'key': 'indoor',             'threshold': 12},
    {'id': 'outdoor_vitamin',     'name': '햇빛 마니아',             'flavor': '비타민D는 이미 충분합니다.',                          'tier': '보통',      'key': 'outdoor',            'threshold': 15},
    {'id': 'museum_alive',        'name': '박물관은 살아있을지도?',    'flavor': '유물들이 밤마다 움직일 것 같은 단골손님.',              'tier': '보통',      'key': 'museum',             'threshold': 10},
    {'id': 'modern_history',      'name': '근현대사 워커',           'flavor': '아픈 역사도 잊지 않는 발걸음.',                       'tier': '보통',      'key': 'era_japanese',       'threshold': 8},
    {'id': 'history_writer',      'name': '발로 쓰는 역사책',         'flavor': '발걸음마다 역사 한 페이지.',                          'tier': '보통',      'key': 'historic',           'threshold': 20},
    {'id': 'seoul_local',         'name': '서울 토박이',             'flavor': '서울 골목골목이 내 집 앞마당.',                       'tier': '어려움',    'key': 'seoul',              'threshold': 15},
    {'id': 'gyeonggi_wanderer',   'name': '경기 유랑자',             'flavor': '경기도 한 바퀴는 기본 코스.',                         'tier': '어려움',    'key': 'gyeonggi',           'threshold': 15},
    {'id': 'little_buddha',       'name': '내 안의 작은 부처',        'flavor': '어느새 합장이 자연스러워졌다.',                       'tier': '어려움',    'key': 'temple',             'threshold': 15},
    {'id': 'royal_blood',         'name': '전생에 왕족이었나?',       'flavor': '궁궐 마루가 내 집처럼 익숙하다.',                     'tier': '어려움',    'key': 'palace',             'threshold': 6},
    {'id': 'metro_conqueror',     'name': '수도권 정복자',           'flavor': '서울도 경기도 다 내 구역.',                          'tier': '어려움',    'key': 'metro_min',          'threshold': 10},
    {'id': 'culture_nomad',       'name': '문화 노마드',             'flavor': '어디든 떠나는 게 일상이 된 사람.',                     'tier': '어려움',    'key': 'total',              'threshold': 15},
    {'id': 'joseon_witness',      'name': '조선왕조 500년 산증인',    'flavor': '조선시대 유적은 발도장 다 찍었다.',                    'tier': '매우 어려움', 'key': 'era_joseon',       'threshold': 35},
    {'id': 'history_geek',        'name': '역사 덕후',               'flavor': '주말마다 박물관·유적 투어는 국룰.',                    'tier': '매우 어려움', 'key': 'total',            'threshold': 30},
    {'id': 'heritage_conqueror',  'name': '문화유산 정복자',          'flavor': '이 나라 문화유산은 이제 내 손바닥 안.',                 'tier': '매우 어려움', 'key': 'total',            'threshold': 50},
]


def _compute_badge_stats(target):
    place_ids = RoutePlace.objects.filter(
        route__user=target, route__is_footprint=True
    ).values_list('place_id', flat=True).distinct()
    places = list(Place.objects.filter(id__in=place_ids).select_related('theme'))

    palace_cat = [p for p in places if p.category == 'palace']
    temple = sum(1 for p in palace_cat if _is_temple(p.name))
    palace = len(palace_cat) - temple
    indoor = sum(1 for p in places if p.is_indoor)
    seoul = sum(1 for p in places if p.region == 'seoul')
    gyeonggi = sum(1 for p in places if p.region == 'gyeonggi')

    era_counts = {}
    for p in places:
        if p.theme_id:
            era_counts[p.theme.era] = era_counts.get(p.theme.era, 0) + 1

    return {
        'total':              len(places),
        'historic':           sum(1 for p in places if p.category == 'historic'),
        'museum':              sum(1 for p in places if p.category == 'museum'),
        'temple':              temple,
        'palace':              palace,
        'seoul':               seoul,
        'gyeonggi':            gyeonggi,
        'indoor':              indoor,
        'outdoor':             len(places) - indoor,
        'war':                 sum(1 for p in places if _is_war_related(p)),
        'metro_min':           min(seoul, gyeonggi),
        'era_three_kingdoms':  era_counts.get('three_kingdoms', 0),
        'era_goryeo':          era_counts.get('goryeo', 0),
        'era_joseon':          era_counts.get('joseon', 0),
        'era_japanese':        era_counts.get('japanese', 0),
        'era_modern':          era_counts.get('modern', 0),
    }


def _compute_badges(target):
    stats = _compute_badge_stats(target)
    badges = []
    for b in BADGE_DEFS:
        progress = stats.get(b['key'], 0)
        threshold = b['threshold']
        badges.append({
            'id': b['id'],
            'name': b['name'],
            'flavor': b['flavor'],
            'tier': b['tier'],
            'earned': progress >= threshold,
            'progress': min(progress, threshold),
            'threshold': threshold,
        })
    return badges


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
        return Response({'username': request.user.username, 'id': request.user.id})
    return Response({'detail': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)


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
    badges_data = _compute_badges(target) if is_self else []

    return Response({
        'username': target.username,
        'email': target.email if is_self else '',
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
