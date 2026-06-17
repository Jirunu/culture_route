import json
import math
import re
import requests
from itertools import permutations
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import Place, Theme, Review, Route, Bookmark, RouteLike, RouteComment
from .serializers import (
    PlaceListSerializer, PlaceDetailSerializer,
    ThemeSerializer,
    ReviewSerializer,
    RouteListSerializer, RouteDetailSerializer, RouteCreateSerializer,
    RouteCommentSerializer,
    BookmarkSerializer,
)


# -----------------------------------------------
# F808 - place_list
# 전체 문화 장소 목록 조회
# -----------------------------------------------
@api_view(['GET'])
def place_list(request):
    """
    GET /api/places/
    전체 문화 장소 목록 반환
    - q: 이름 검색 (name__icontains)
    """
    places = Place.objects.select_related('theme').all()
    q = request.query_params.get('q')
    if q:
        places = places.filter(name__icontains=q)
    serializer = PlaceListSerializer(places, many=True)
    return Response(serializer.data)


# -----------------------------------------------
# F809 - place_detail
# 단일 문화 장소 상세 조회
# -----------------------------------------------
@api_view(['GET'])
def place_detail(request, place_pk):
    """
    GET /api/places/<place_pk>/
    단일 장소 상세 정보 반환 (리뷰 최신 5개 포함)
    """
    place = get_object_or_404(Place, pk=place_pk)
    serializer = PlaceDetailSerializer(place)
    return Response(serializer.data)


# -----------------------------------------------
# F810 - place_by_theme
# 시대·카테고리·지역 필터 장소 조회
# -----------------------------------------------
@api_view(['GET'])
def place_by_theme(request):
    """
    GET /api/places/filter/
    쿼리 파라미터로 필터링
    - era      : 시대 (three_kingdoms / goryeo / joseon / japanese / modern)
    - category : 카테고리 (historic / museum / park / palace / culture / etc)
    - region   : 지역 (seoul / gyeonggi)
    - is_indoor: 실내 여부 (true / false)
    """
    places = Place.objects.select_related('theme').all()

    era_list      = request.query_params.getlist('era')
    category_list = request.query_params.getlist('category')
    region        = request.query_params.get('region')
    is_indoor     = request.query_params.get('is_indoor')
    is_active     = request.query_params.get('is_active')
    q             = request.query_params.get('q')

    if era_list:
        places = places.filter(theme__era__in=era_list)
    if category_list:
        places = places.filter(category__in=category_list)
    if region:
        places = places.filter(region=region)
    if is_indoor is not None:
        places = places.filter(is_indoor=is_indoor.lower() == 'true')
    if is_active is not None:
        places = places.filter(is_active=is_active.lower() == 'true')
    if q:
        places = places.filter(name__icontains=q)

    serializer = PlaceListSerializer(places, many=True)
    return Response(serializer.data)


# -----------------------------------------------
# 비슷한 장소 추천
# -----------------------------------------------
@api_view(['GET'])
def place_similar(request, place_pk):
    """GET /api/places/<pk>/similar/ — 같은 카테고리·테마 장소 4개"""
    place = get_object_or_404(Place, pk=place_pk)
    qs = Place.objects.filter(
        Q(category=place.category) | Q(theme=place.theme)
    ).exclude(pk=place_pk).select_related('theme').order_by('?')[:4]
    return Response(PlaceListSerializer(qs, many=True).data)


# -----------------------------------------------
# F811 - review_list
# 특정 장소의 전체 리뷰 조회 + 리뷰 작성
# -----------------------------------------------
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def review_list(request, place_pk):
    """
    GET  /api/places/<place_pk>/reviews/  : 해당 장소 리뷰 목록 조회
    POST /api/places/<place_pk>/reviews/  : 리뷰 작성 (로그인 필요)
    """
    place = get_object_or_404(Place, pk=place_pk)

    if request.method == 'GET':
        reviews = place.reviews.all()
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    # POST
    serializer = ReviewSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user, place=place)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------------------------
# F812 - review_detail
# 단일 리뷰 조회·수정·삭제
# -----------------------------------------------
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticatedOrReadOnly])
def review_detail(request, place_pk, review_pk):
    """
    GET    /api/places/<place_pk>/reviews/<review_pk>/  : 단일 리뷰 조회
    PUT    /api/places/<place_pk>/reviews/<review_pk>/  : 리뷰 수정 (작성자만)
    DELETE /api/places/<place_pk>/reviews/<review_pk>/  : 리뷰 삭제 (작성자만)
    """
    place  = get_object_or_404(Place, pk=place_pk)
    review = get_object_or_404(Review, pk=review_pk, place=place)

    if request.method == 'GET':
        serializer = ReviewSerializer(review)
        return Response(serializer.data)

    # 작성자 본인만 수정·삭제 가능
    if review.user != request.user:
        return Response(
            {'detail': '본인이 작성한 리뷰만 수정·삭제할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == 'PUT':
        serializer = ReviewSerializer(review, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    review.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# -----------------------------------------------
# F813 - create_review
# 리뷰 작성 (단독 엔드포인트 - review_list POST와 동일 역할)
# -----------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review(request, place_pk):
    """
    POST /api/places/<place_pk>/reviews/create/
    리뷰 데이터를 전달받아 DB에 저장
    """
    place = get_object_or_404(Place, pk=place_pk)
    serializer = ReviewSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user, place=place)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------------------------
# F814 - route_recommend
# 동선 코스 자동 생성 및 목록 조회
# -----------------------------------------------
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def route_recommend(request):
    """
    GET  /api/routes/          : 공유된 커뮤니티 코스 목록 조회
    POST /api/routes/          : 새 코스 생성
         body: { title, mode, total_distance, total_time, is_shared, place_ids }
    """
    if request.method == 'GET':
        routes = Route.objects.filter(is_shared=True).select_related('user').prefetch_related(
            'routeplace_set__place', 'likes', 'comments'
        ).order_by('-created_at')
        serializer = RouteListSerializer(routes, many=True, context={'request': request})
        return Response(serializer.data)

    # POST
    serializer = RouteCreateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticatedOrReadOnly])
def route_detail(request, route_pk):
    """
    GET    /api/routes/<route_pk>/  : 코스 상세 조회
    PUT    /api/routes/<route_pk>/  : 코스 수정 (생성자만)
    DELETE /api/routes/<route_pk>/  : 코스 삭제 (생성자만)
    """
    route = get_object_or_404(Route, pk=route_pk)

    if request.method == 'GET':
        serializer = RouteDetailSerializer(route)
        return Response(serializer.data)

    if route.user != request.user:
        return Response(
            {'detail': '본인이 생성한 코스만 수정·삭제할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == 'PUT':
        serializer = RouteCreateSerializer(route, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    route.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# -----------------------------------------------
# F815 - bookmark_list / detail
# 북마크 목록 조회·추가·삭제
# -----------------------------------------------
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def bookmark_list(request):
    """
    GET  /api/bookmarks/  : 내 북마크 목록 조회
    POST /api/bookmarks/  : 북마크 추가
         body: { place: <id> } 또는 { route: <id> }
    """
    if request.method == 'GET':
        bookmarks = Bookmark.objects.filter(user=request.user).select_related('place', 'route')
        place_id = request.query_params.get('place')
        if place_id:
            bookmarks = bookmarks.filter(place_id=place_id)
        serializer = BookmarkSerializer(bookmarks, many=True)
        return Response(serializer.data)

    # POST
    serializer = BookmarkSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def bookmark_detail(request, bookmark_pk):
    """
    DELETE /api/bookmarks/<bookmark_pk>/  : 북마크 삭제 (본인만)
    """
    bookmark = get_object_or_404(Bookmark, pk=bookmark_pk, user=request.user)
    bookmark.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# -----------------------------------------------
# F816 - 날씨 기반 장소 추천
# -----------------------------------------------
@api_view(['GET'])
def weather_recommend(request):
    """
    GET /api/places/weather/
    쿼리 파라미터:
    - is_indoor : true / false  (날씨 API 연동 후 자동 판단 예정)
    - is_active : true / false  (동적/정적 장소 여부)

    현재는 파라미터 기반 필터링,
    추후 OpenWeatherMap API 연동으로 자동화 예정 (F818)
    """
    places = Place.objects.select_related('theme').all()

    is_indoor = request.query_params.get('is_indoor')
    is_active = request.query_params.get('is_active')

    if is_indoor is not None:
        places = places.filter(is_indoor=is_indoor.lower() == 'true')
    if is_active is not None:
        places = places.filter(is_active=is_active.lower() == 'true')

    serializer = PlaceListSerializer(places, many=True)
    return Response(serializer.data)


# -----------------------------------------------
# F818 - OpenWeatherMap 실시간 날씨 조회
# -----------------------------------------------
@api_view(['GET'])
def weather_current(request):
    """
    GET /api/places/weather-current/
    OpenWeatherMap API로 서울 현재 날씨를 조회하고
    실내/실외 추천 여부와 함께 반환한다.
    """
    api_key = getattr(settings, 'OPENWEATHER_API_KEY', '')
    if not api_key:
        return Response({'error': 'OPENWEATHER_API_KEY가 설정되지 않았습니다.'}, status=503)

    try:
        resp = requests.get(
            'https://api.openweathermap.org/data/2.5/weather',
            params={'q': 'Seoul,KR', 'appid': api_key, 'units': 'metric', 'lang': 'kr'},
            timeout=5,
        )
        resp.raise_for_status()
        w = resp.json()
    except requests.RequestException:
        return Response({'error': '날씨 정보를 가져올 수 없습니다. 잠시 후 다시 시도해 주세요.'}, status=503)

    weather_id   = w['weather'][0]['id']
    description  = w['weather'][0]['description']
    temp         = round(w['main']['temp'])
    humidity     = w['main']['humidity']
    icon_code    = w['weather'][0]['icon']
    city         = w['name']

    # 800: 맑음, 801-802: 구름 조금 → 실외 OK / 나머지 → 실내 권장
    is_indoor = not (weather_id == 800 or 801 <= weather_id <= 802)

    if weather_id == 800:
        emoji, msg = '☀️', '야외 활동하기 최적의 날씨입니다.\n실외 역사 유적지와 궁궐을 추천드립니다.'
        conds = ['실외 · 동적 장소 우선', '공원 · 궁궐 · 유적지 추천']
    elif 801 <= weather_id <= 802:
        emoji, msg = '⛅', '구름이 조금 있지만 야외 활동 가능합니다.\n궁궐이나 공원 방문을 추천드립니다.'
        conds = ['실외 장소 무난', '공원 · 산책로 추천']
    elif 803 <= weather_id <= 804:
        emoji, msg = '☁️', '흐린 날씨입니다.\n실내 박물관이나 미술관 방문을 추천드립니다.'
        conds = ['실내 시설 우선 추천', '박물관 · 미술관 · 문화 시설']
    elif 300 <= weather_id <= 321:
        emoji, msg = '🌦️', '이슬비가 내리고 있습니다.\n실내 문화 시설을 추천드립니다.'
        conds = ['실내 시설 추천', '박물관 · 미술관']
    elif 500 <= weather_id <= 531:
        emoji, msg = '🌧️', '비가 내리고 있습니다.\n따뜻한 실내 문화 시설을 추천드립니다.'
        conds = ['실내 관람 시설 우선', '박물관 · 역사관 추천']
    elif 600 <= weather_id <= 622:
        emoji, msg = '❄️', '눈이 내리고 있습니다.\n실내 박물관이나 미술관을 추천드립니다.'
        conds = ['실내 시설 강력 추천', '박물관 · 미술관 · 실내 문화']
    elif 200 <= weather_id <= 232:
        emoji, msg = '⛈️', '천둥번개가 치고 있습니다.\n안전을 위해 실내 시설을 이용하세요.'
        conds = ['실내 시설 이용 권장', '안전 우선 실내 관람']
    else:
        emoji, msg = '🌤️', '다양한 문화 명소를 즐겨보세요.'
        conds = ['날씨에 맞는 장소 추천', '문화 명소 탐방']

    return Response({
        'temp':           temp,
        'description':    description,
        'humidity':       humidity,
        'emoji':          emoji,
        'city':           city,
        'is_indoor':      is_indoor,
        'recommendation': msg,
        'conditions':     conds,
        'icon':           f'https://openweathermap.org/img/wn/{icon_code}@2x.png',
    })


# -----------------------------------------------
# F819 - 커뮤니티 코스 좋아요 토글
# -----------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def route_like(request, route_pk):
    """
    POST /api/routes/<route_pk>/like/
    좋아요 토글 — 처음 누르면 추가, 다시 누르면 취소
    """
    route = get_object_or_404(Route, pk=route_pk, is_shared=True)
    like, created = RouteLike.objects.get_or_create(user=request.user, route=route)
    if not created:
        like.delete()
        route.like_count = max(0, route.like_count - 1)
        liked = False
    else:
        route.like_count += 1
        liked = True
    route.save(update_fields=['like_count'])
    return Response({'liked': liked, 'like_count': route.like_count}, status=status.HTTP_200_OK)


# -----------------------------------------------
# 코스 댓글
# -----------------------------------------------
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def route_comments(request, route_pk):
    """
    GET  /api/routes/<route_pk>/comments/  : 댓글 목록 조회
    POST /api/routes/<route_pk>/comments/  : 댓글 작성 (로그인 필요)
    """
    route = get_object_or_404(Route, pk=route_pk)
    if request.method == 'GET':
        serializer = RouteCommentSerializer(route.comments.select_related('user').all(), many=True)
        return Response(serializer.data)
    serializer = RouteCommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user, route=route)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def route_comment_detail(request, route_pk, comment_pk):
    """
    DELETE /api/routes/<route_pk>/comments/<comment_pk>/  : 댓글 삭제 (작성자만)
    """
    comment = get_object_or_404(RouteComment, pk=comment_pk, route_id=route_pk)
    if comment.user != request.user:
        return Response({'detail': '본인이 작성한 댓글만 삭제할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)
    comment.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# -----------------------------------------------
# 온보딩 설문 뷰
# -----------------------------------------------
@login_required
def survey_view(request):
    """GET /survey/ — survey_done 세션 없으면 설문, 있으면 /app/ 리다이렉트"""
    if request.session.get('survey_done'):
        return redirect('/app/')
    return render(request, 'survey.html')


@login_required
def app_view(request):
    """GET /app/ — 설문 완료 후 메인 앱 (미완료 시 /survey/ 리다이렉트)"""
    if not request.session.get('survey_done'):
        return redirect('/survey/')
    survey_data = request.session.get('survey_data', {})
    return render(request, 'app.html', {'survey_data_json': json.dumps(survey_data, ensure_ascii=False)})


def index_view(request):
    """GET / — 랜딩 페이지 (survey_done 여부를 context로 전달)"""
    return render(request, 'landing.html', {
        'survey_done': request.session.get('survey_done', False),
    })


@require_http_methods(['POST'])
def survey_save(request):
    """POST /api/survey/save/ — 설문 응답을 세션에 저장"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': '잘못된 데이터입니다.'}, status=400)
    request.session['survey_done'] = True
    request.session['survey_data'] = data
    return JsonResponse({'status': 'ok', 'redirect': '/loading/'})


# -----------------------------------------------
# Haversine 거리 계산 (km)
# -----------------------------------------------
def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# 지역 중심 좌표 (새 설문 region 값 기준)
_REGION_CENTER = {
    'seoul_center':   (37.5704, 126.9868),
    'seoul_outer':    (37.5665, 126.9780),
    'gyeonggi_north': (37.7500, 127.0000),
    'gyeonggi_south': (37.2500, 127.0000),
    'any':            (37.5665, 126.9780),
}

# 새 설문 interest 값 → DB 필터 매핑
_ERA_MAP = {
    'joseon':        ['joseon'],
    'goryeo_samguk': ['goryeo', 'three_kingdoms'],
    'modern_history':['japanese', 'modern'],
}
_CAT_MAP = {
    'buddhism': 'palace',
    'royal':    'palace',
    'folk':     'historic',
    # 설문 2단계 직접 선택값
    'historic': 'historic',
    'museum':   'museum',
    'palace':   'palace',
}
_DURATION_MAP = {'short': 2, 'half': 4, 'full': 8}
_REGION_DB_MAP = {
    'seoul_center': 'seoul', 'seoul_outer': 'seoul',
    'gyeonggi_north': 'gyeonggi', 'gyeonggi_south': 'gyeonggi',
    'any': '',
    # 구 설문 형식 호환
    'seoul_north': 'seoul', 'seoul_south': 'seoul',
    'seoul_east':  'seoul', 'seoul_west':  'seoul',
    'gyeonggi_east': 'gyeonggi', 'gyeonggi_west': 'gyeonggi',
}


def _call_claude_recommend(survey, candidates):
    """Claude API로 후보 장소 중 최적 5개 추천. 실패 시 None 반환."""
    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        return None
    try:
        import anthropic as _ant
    except ImportError:
        return None

    ERA_KO = {
        'three_kingdoms': '삼국시대', 'goryeo': '고려시대', 'joseon': '조선시대',
        'japanese': '일제강점기', 'modern': '현대',
    }
    CAT_KO = {'historic': '역사 유적', 'museum': '박물관·미술관', 'palace': '궁궐·사찰'}
    COMPANIONS_KO = {'solo': '혼자', 'couple': '커플', 'group': '소그룹', 'family': '가족'}
    PURPOSE_KO = {'study': '역사 학습', 'culture': '문화 체험', 'healing': '힐링', 'photo': '사진 촬영'}
    DURATION_KO = {'short': '2~3시간', 'half': '반나절(4시간)', 'full': '하루(8시간)'}

    interests = [i for i in survey.get('interests', []) if i != 'any']
    interests_str = ', '.join(CAT_KO.get(i, i) for i in interests) or '무관'
    companions = COMPANIONS_KO.get(survey.get('companions', ''), '')
    purpose = PURPOSE_KO.get(survey.get('purpose', ''), '')
    duration = DURATION_KO.get(survey.get('duration_type', ''), '')

    places_data = [
        {
            'id': p.id,
            'name': p.name,
            'category': CAT_KO.get(p.category, p.category),
            'era': ERA_KO.get(p.theme.era if p.theme else '', ''),
            'indoor': '실내' if p.is_indoor else '실외',
            'fee': '무료' if p.entrance_fee == 0 else f'{p.entrance_fee:,}원',
        }
        for p in candidates
    ]

    prompt = (
        f'서울·경기 문화명소 여행 큐레이터입니다.\n\n'
        f'사용자 취향: 관심분야={interests_str}, 동행={companions}, 목적={purpose}, 소요시간={duration}\n\n'
        f'후보 장소 {len(places_data)}곳 중 이 사용자에게 최적인 5곳을 고르고, '
        f'취향에 맞춘 추천 이유를 한 문장씩 작성하세요.\n\n'
        f'후보:\n{json.dumps(places_data, ensure_ascii=False)}\n\n'
        f'JSON만 응답 (다른 텍스트 없이):\n'
        f'{{"ranked": [{{"id": <숫자>, "reason": "<이유>"}}, ...]}}'
    )

    try:
        client = _ant.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=600,
            messages=[{'role': 'user', 'content': prompt}],
        )
        text = msg.content[0].text.strip()
        if '```' in text:
            text = re.sub(r'```(?:json)?', '', text).strip()
        ranked = json.loads(text).get('ranked', [])[:5]
        id_to_place = {p.id: p for p in candidates}
        result = [
            (id_to_place[item['id']], item.get('reason', ''))
            for item in ranked
            if item.get('id') in id_to_place
        ]
        return result or None
    except Exception:
        return None


def _rank_candidates(candidates, eras, categories, duration_type, companions, purpose, interests):
    """설문 데이터 기반 규칙 점수 산정 → 상위 5개 반환."""
    ERA_LABEL = {
        'three_kingdoms': '삼국시대', 'goryeo': '고려시대', 'joseon': '조선시대',
        'japanese': '일제강점기', 'modern': '현대',
    }
    CAT_LABEL = {'historic': '역사 유적', 'museum': '박물관·미술관', 'palace': '궁궐·사찰'}

    scored = []
    for p in candidates:
        score = 0
        tags = []
        era = p.theme.era if p.theme else ''

        if eras and era in eras:
            score += 4
            tags.append(f'{ERA_LABEL.get(era, era)} 관련 장소')

        if categories and p.category in categories:
            score += 3
            tags.append(f'{CAT_LABEL.get(p.category, p.category)} 취향에 맞음')

        if duration_type == 'short' and p.is_indoor:
            score += 2
        elif duration_type == 'full' and not p.is_indoor:
            score += 1

        if purpose == 'study' and p.category in ('museum', 'historic'):
            score += 2
            tags.append('역사 학습에 적합')
        elif purpose == 'culture' and p.category == 'palace':
            score += 2
            tags.append('전통 문화 체험에 좋음')
        elif purpose in ('healing', 'photo') and not p.is_indoor:
            score += 1

        if companions == 'family' and p.entrance_fee == 0:
            score += 1
            tags.append('가족 방문에 알맞은 무료 장소')
        elif p.entrance_fee == 0:
            score += 1

        if not tags:
            if era:
                tags.append(f'{ERA_LABEL.get(era, era)} 테마의 장소')
            else:
                tags.append(f'{CAT_LABEL.get(p.category, "")} 취향 추천 장소')

        scored.append((score, p, ', '.join(tags)))

    scored.sort(key=lambda x: -x[0])
    return [(p, reason) for _, p, reason in scored[:5]]


# -----------------------------------------------
# AI 장소 추천 (Claude API + 규칙 기반 폴백)
# -----------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_recommend(request):
    """
    POST /api/places/ai-recommend/
    세션 설문 데이터 기반으로 GMS LLM이 장소 5개를 추천한다.
    body: { radius: <km, 기본 10> }
    비로그인도 허용 (설문 데이터는 세션에 저장).
    """
    survey = request.session.get('survey_data', {})
    radius = float(request.data.get('radius', 10))

    # ── 새 설문(v2) / 구 설문(v1) 공용 파싱 ─────
    is_new_survey = 'duration_type' in survey or 'companions' in survey

    if is_new_survey:
        interests     = survey.get('interests', [])
        duration_type = survey.get('duration_type', 'half')
        survey_region = survey.get('region', 'any')
        companions    = survey.get('companions', '')
        purpose       = survey.get('purpose', '')
        duration      = _DURATION_MAP.get(duration_type, 4)

        has_all = 'all' in interests or 'any' in interests
        eras, categories = [], []
        if not has_all:
            for interest in interests:
                if interest in _ERA_MAP:
                    for e in _ERA_MAP[interest]:
                        if e not in eras:
                            eras.append(e)
                elif interest in _CAT_MAP:
                    cat = _CAT_MAP[interest]
                    if cat not in categories:
                        categories.append(cat)
    else:
        # 구 설문 형식 호환
        interests     = survey.get('interests', [])
        duration      = survey.get('duration', 3)
        survey_region = survey.get('region', 'any')
        companions    = survey.get('visitors', '')
        purpose       = survey.get('activity', '')
        duration_type = 'half'
        eras          = [e for e in survey.get('eras', []) if e != 'any']
        categories    = [i for i in interests if i in ('historic', 'museum', 'palace')]

    region = _REGION_DB_MAP.get(survey_region, '')
    center = _REGION_CENTER.get(survey_region, (37.5665, 126.9780))

    # ── 후보 장소 조회 ────────────────────────────
    places_qs = Place.objects.select_related('theme').all()
    if region:
        places_qs = places_qs.filter(region=region)
    if eras:
        places_qs = places_qs.filter(theme__era__in=eras)
    if categories:
        places_qs = places_qs.filter(category__in=categories)

    candidates = list(places_qs[:50])

    # ── 범위 필터링 (Haversine) ───────────────────
    # radius는 동선 지름(km). 지역 중심에서 radius/2 이내 장소만 포함해
    # 어떤 두 장소도 최대 radius km 이내에 위치하도록 한다.
    filter_r = radius / 2
    if radius < 50:
        candidates = [
            p for p in candidates
            if _haversine(center[0], center[1], float(p.latitude), float(p.longitude)) <= filter_r
        ]

    # 범위 내 장소 없으면 지름 2배로 재시도
    if not candidates:
        fallback = list(places_qs[:50])
        candidates = [
            p for p in fallback
            if _haversine(center[0], center[1], float(p.latitude), float(p.longitude)) <= filter_r * 2
        ]

    if not candidates:
        return Response({'places': [], 'message': f'동선 범위 {radius:.0f}km 내 장소가 없습니다. 범위를 늘려 다시 시도해 주세요.'})

    selected_places = _call_claude_recommend(survey, candidates)
    if selected_places is None:
        selected_places = _rank_candidates(candidates, eras, categories, duration_type, companions, purpose, interests)

    result = [
        {
            'id':             p.id,
            'name':           p.name,
            'address':        p.address,
            'latitude':       float(p.latitude),
            'longitude':      float(p.longitude),
            'category':       p.category,
            'category_display': p.get_category_display(),
            'is_indoor':      p.is_indoor,
            'image_url':      p.image_url,
            'reason':         reason,
        }
        for p, reason in selected_places
    ]
    return Response({'places': result})


# -----------------------------------------------
# 동선 스토리텔링 (Claude API)
# -----------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def route_story(request):
    """
    POST /api/places/route-story/
    동선 장소들을 잇는 여행 스토리텔링 내러티브 생성
    body: { place_ids: [1, 2, 3, ...] }
    """
    place_ids = request.data.get('place_ids', [])
    if not place_ids:
        return Response({'error': '장소를 선택해 주세요.'}, status=400)

    places_qs = {p.id: p for p in Place.objects.filter(pk__in=place_ids).select_related('theme')}
    ordered = [places_qs[pid] for pid in place_ids if pid in places_qs]

    if not ordered:
        return Response({'error': '장소를 찾을 수 없습니다.'}, status=404)

    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        return Response({'error': 'AI 기능이 설정되지 않았습니다.'}, status=503)

    ERA_KO = {
        'three_kingdoms': '삼국시대', 'goryeo': '고려시대', 'joseon': '조선시대',
        'japanese': '일제강점기', 'modern': '현대',
    }
    CAT_KO = {'historic': '역사 유적', 'museum': '박물관·미술관', 'palace': '궁궐·사찰'}

    places_desc = '\n'.join(
        f'{i+1}. {p.name}'
        f' ({CAT_KO.get(p.category, p.category)}'
        f' | {ERA_KO.get(p.theme.era if p.theme else "", "시대 미상")})'
        f'{(" — " + p.description[:60]) if p.description else ""}'
        for i, p in enumerate(ordered)
    )

    prompt = (
        '당신은 한국 문화유산 전문 여행 작가입니다.\n\n'
        f'오늘의 동선:\n{places_desc}\n\n'
        '이 장소들을 방문 순서대로 자연스럽게 잇는 여행 스토리텔링 내러티브를 작성하세요.\n\n'
        '요구사항:\n'
        '- 4~5문장의 하나의 단락으로 작성\n'
        '- 역사적 사실과 감성적 묘사를 균형 있게 담을 것\n'
        '- 방문자가 시간 여행을 하는 듯한 몰입감을 줄 것\n'
        '- 장소명은 「」로 강조 (예: 「경복궁」)\n'
        '- 순수 텍스트만 출력 (JSON·마크다운 없이)'
    )

    try:
        import anthropic as _ant
        client = _ant.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=600,
            messages=[{'role': 'user', 'content': prompt}],
        )
        return Response({'story': msg.content[0].text.strip()})
    except Exception:
        return Response({'error': '스토리 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.'}, status=503)


@require_http_methods(['POST'])
def survey_reset(request):
    """POST /api/survey/reset/ — 설문 세션 초기화"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)
    request.session.pop('survey_done', None)
    request.session.pop('survey_data', None)
    return JsonResponse({'status': 'ok'})


# -----------------------------------------------
# 동선 최적화
# -----------------------------------------------
def _haversine_km(p1, p2):
    R = 6371
    lat1, lon1 = math.radians(float(p1.latitude)), math.radians(float(p1.longitude))
    lat2, lon2 = math.radians(float(p2.latitude)), math.radians(float(p2.longitude))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _shortest_route(places):
    """총 이동거리가 최소인 방문 순서 반환 (N≤8 브루트포스, N>8 최근접 휴리스틱)."""
    n = len(places)
    if n <= 1:
        return list(places)

    def total_dist(order):
        return sum(_haversine_km(order[i], order[i + 1]) for i in range(len(order) - 1))

    if n <= 8:
        best = min(permutations(places), key=total_dist)
        return list(best)

    # 최근접 이웃 — 모든 시작점 시도
    best_order, best_dist = None, float('inf')
    for start in range(n):
        unvisited = list(places)
        cur = unvisited.pop(start)
        order = [cur]
        while unvisited:
            nxt = min(unvisited, key=lambda p: _haversine_km(cur, p))
            unvisited.remove(nxt)
            order.append(nxt)
            cur = nxt
        d = total_dist(order)
        if d < best_dist:
            best_dist, best_order = d, order
    return best_order


@api_view(['POST'])
def route_optimize(request):
    """
    POST /api/places/route-optimize/
    좌표 기반 최단 동선 계산 + Claude로 팁·요약 생성
    body: { place_ids: [1, 2, 3, ...] }
    """
    place_ids = request.data.get('place_ids', [])
    if not place_ids:
        return Response({'error': '장소를 선택해 주세요.'}, status=400)

    places_qs = {p.id: p for p in Place.objects.filter(pk__in=place_ids).select_related('theme')}
    raw = [places_qs[pid] for pid in place_ids if pid in places_qs]

    # 좌표로 최단 동선 계산
    geo_ordered = _shortest_route(raw)
    optimal_ids = [p.id for p in geo_ordered]

    if not getattr(settings, 'ANTHROPIC_API_KEY', '') or len(geo_ordered) <= 1:
        return Response({'order': optimal_ids, 'tips': {}, 'summary': ''})

    CAT_KO = {'historic': '역사 유적', 'museum': '박물관·미술관', 'palace': '궁궐·사찰'}
    places_data = [
        {
            'id': p.id,
            'name': p.name,
            'category': CAT_KO.get(p.category, p.category),
            'address': p.address,
            'indoor': '실내' if p.is_indoor else '실외',
        }
        for p in geo_ordered
    ]

    prompt = (
        '서울·경기 문화 여행 안내사입니다.\n\n'
        '아래는 이미 이동거리 최소화 순서로 정렬된 장소 목록입니다. '
        '각 장소의 핵심 방문 포인트를 한 문장씩 설명하고, 전체 동선을 한 줄로 요약하세요.\n\n'
        f'장소(순서 고정):\n{json.dumps(places_data, ensure_ascii=False)}\n\n'
        'JSON만 응답 (다른 텍스트 없이):\n'
        '{"tips": {"<id문자열>": "<팁>", ...}, "summary": "<동선 한 줄 요약>"}'
    )

    try:
        import anthropic as _ant
        client = _ant.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=600,
            messages=[{'role': 'user', 'content': prompt}],
        )
        text = msg.content[0].text.strip()
        if '```' in text:
            text = re.sub(r'```(?:json)?', '', text).strip()
        result = json.loads(text)
        tips = {str(k): v for k, v in result.get('tips', {}).items()}
        return Response({'order': optimal_ids, 'tips': tips, 'summary': result.get('summary', '')})
    except Exception:
        return Response({'order': optimal_ids, 'tips': {}, 'summary': ''})
