import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import Place, Theme, Review, Route, Bookmark
from .serializers import (
    PlaceListSerializer, PlaceDetailSerializer,
    ThemeSerializer,
    ReviewSerializer,
    RouteListSerializer, RouteDetailSerializer, RouteCreateSerializer,
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
    """
    places = Place.objects.select_related('theme').all()
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

    era      = request.query_params.get('era')
    category = request.query_params.get('category')
    region   = request.query_params.get('region')
    is_indoor = request.query_params.get('is_indoor')

    if era:
        places = places.filter(theme__era=era)
    if category:
        places = places.filter(category=category)
    if region:
        places = places.filter(region=region)
    if is_indoor is not None:
        places = places.filter(is_indoor=is_indoor.lower() == 'true')

    serializer = PlaceListSerializer(places, many=True)
    return Response(serializer.data)


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
        routes = Route.objects.filter(is_shared=True).prefetch_related('places')
        serializer = RouteListSerializer(routes, many=True)
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
# F819 - 커뮤니티 코스 좋아요
# -----------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def route_like(request, route_pk):
    """
    POST /api/routes/<route_pk>/like/
    공유된 코스에 좋아요 추가
    """
    route = get_object_or_404(Route, pk=route_pk, is_shared=True)
    route.like_count += 1
    route.save(update_fields=['like_count'])
    return Response({'like_count': route.like_count}, status=status.HTTP_200_OK)
