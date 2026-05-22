import requests
from django.conf import settings

# ────────────────────────────────────────────
# ① 한국관광공사 TourAPI (KorService2)
# ────────────────────────────────────────────
TOUR_BASE_URL = "https://apis.data.go.kr/B551011/KorService2/areaBasedList2"


def fetch_heritage_list(page=1, size=100, area_code=1, content_type_id=14):
    """
    한국관광공사 지역기반 관광정보 한 페이지 조회.
    반환: (item 리스트, totalCount)  — 오류 시 (None, 0)
    area_code      : 1=서울, 31=경기
    content_type_id: 12=관광지, 14=문화시설
    """
    params = {
        "serviceKey":    settings.PUBLIC_DATA_API_KEY,
        "pageNo":        page,
        "numOfRows":     size,
        "MobileOS":      "ETC",
        "MobileApp":     "CultureRoute",
        "areaCode":      area_code,
        "contentTypeId": content_type_id,
        "arrange":       "Q",
        "_type":         "json",
    }
    try:
        resp = requests.get(TOUR_BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        body = resp.json()["response"]["body"]
        total = int(body.get("totalCount", 0))
        raw = body.get("items") or {}
        item_list = raw.get("item", []) if isinstance(raw, dict) else []
        if isinstance(item_list, dict):   # 결과가 1건이면 dict로 옴
            item_list = [item_list]
        return item_list, total
    except Exception as e:
        print(f"[TourAPI 오류] page={page} area={area_code} ct={content_type_id}: {e}")
        return None, 0


def fetch_all_heritage(area_code=1, content_type_id=14, page_size=100):
    """
    전체 페이지를 순회하여 모든 항목 반환.
    반환: 전체 item 리스트  — 첫 페이지부터 오류 시 None
    """
    all_items = []
    page = 1
    while True:
        items, total = fetch_heritage_list(
            page=page, size=page_size,
            area_code=area_code, content_type_id=content_type_id,
        )
        if items is None:
            return None if page == 1 else all_items
        if not items:
            break
        all_items.extend(items)
        if len(all_items) >= total:
            break
        page += 1
    return all_items



# culture/api_clients.py 에 이미 있어야 함

WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

def fetch_weather(city="Seoul"):
    params = {
        "q":     city,
        "appid": settings.OPENWEATHER_API_KEY,
        "units": "metric",
        "lang":  "kr",
    }
    try:
        response = requests.get(WEATHER_BASE_URL, params=params, timeout=5)
        response.raise_for_status()
        data        = response.json()
        weather_id  = data['weather'][0]['id']
        description = data['weather'][0]['description']
        temp        = data['main']['temp']

        is_indoor = weather_id < 800  # 비·눈 → 실내 추천
        is_active = temp >= 10        # 10도 이상 → 동적 장소 추천

        return {
            'is_indoor':   is_indoor,
            'is_active':   is_active,
            'description': description,
            'temp':        temp,
        }
    except Exception as e:
        print(f"[날씨 API 오류] {e}")
        return None
    

# 기존 fetch_route_distance 함수 전체를 아래로 교체

KAKAO_LOCAL_URL = "https://dapi.kakao.com/v2/local/geo/transcoord.json"

def fetch_route_distance(origin, destination):
    """
    두 좌표 간 직선 거리 계산 (Kakao Mobility 대신 임시 사용)
    origin, destination: (위도, 경도) 튜플
    """
    import math

    lat1, lng1 = origin
    lat2, lng2 = destination

    # 하버사인 공식으로 직선거리 계산
    R = 6371000  # 지구 반지름 (미터)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng/2)**2
    distance = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    # 도보 속도 4km/h 기준 소요시간 계산
    duration = int((distance / 4000) * 3600)

    return {
        'distance': int(distance),  # 미터(m)
        'duration': duration,       # 초(s)
    }