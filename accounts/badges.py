import re

from culture.models import Place, RoutePlace

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
    {'id': 'first_step',          'name': '첫 발걸음',              'flavor': '여행의 첫 페이지를 펼쳤어요.',                       'tier': '아주 쉬움',   'key': 'total',              'threshold': 1,  'condition': '장소 1곳 방문하기'},
    {'id': 'goryeo_loyalist',     'name': '고려 충신',              'flavor': '고려 유적 찾아 삼만리.',                            'tier': '아주 쉬움',   'key': 'era_goryeo',         'threshold': 2,  'condition': '고려시대 유적 2곳 방문하기'},
    {'id': 'samguk_fan',          'name': '삼국시대 덕후',           'flavor': '백제·신라·고구려, 다 가봤음.',                        'tier': '쉬움',        'key': 'era_three_kingdoms', 'threshold': 4,  'condition': '삼국시대 유적 4곳 방문하기'},
    {'id': 'neighborhood_walker', 'name': '동네 산책러',             'flavor': '우리 동네 문화 마실, 이제 시작이죠.',                  'tier': '쉬움',        'key': 'total',              'threshold': 5,  'condition': '장소 5곳 방문하기'},
    {'id': 'war_maniac',          'name': '전쟁광',                 'flavor': '전쟁 유적만 보면 발걸음이 빨라진다.',                  'tier': '쉬움',        'key': 'war',                'threshold': 4,  'condition': '전쟁 관련 장소 4곳 방문하기'},
    {'id': 'modern_hunter',       'name': '모던 컬처 헌터',           'flavor': '요즘 감성도 놓치지 않는 센스.',                       'tier': '쉬움',        'key': 'era_modern',         'threshold': 6,  'condition': '현대 문화·예술 장소 6곳 방문하기'},
    {'id': 'indoor_culture',      'name': '실내파 문화인',           'flavor': '냉방 빵빵한 곳만 골라다니는 센스.',                    'tier': '보통',        'key': 'indoor',             'threshold': 12, 'condition': '실내 장소 12곳 방문하기'},
    {'id': 'outdoor_vitamin',     'name': '햇빛 마니아',             'flavor': '비타민D는 이미 충분합니다.',                          'tier': '보통',        'key': 'outdoor',            'threshold': 15, 'condition': '실외 장소 15곳 방문하기'},
    {'id': 'museum_alive',        'name': '박물관은 살아있을지도?',    'flavor': '유물들이 밤마다 움직일 것 같은 단골손님.',              'tier': '보통',        'key': 'museum',             'threshold': 10, 'condition': '박물관·미술관 10곳 방문하기'},
    {'id': 'modern_history',      'name': '근현대사 워커',           'flavor': '아픈 역사도 잊지 않는 발걸음.',                       'tier': '보통',        'key': 'era_japanese',       'threshold': 8,  'condition': '일제강점기 유적 8곳 방문하기'},
    {'id': 'history_writer',      'name': '발로 쓰는 역사책',         'flavor': '발걸음마다 역사 한 페이지.',                          'tier': '보통',        'key': 'historic',           'threshold': 20, 'condition': '역사 유적 20곳 방문하기'},
    {'id': 'seoul_local',         'name': '서울 토박이',             'flavor': '서울 골목골목이 내 집 앞마당.',                       'tier': '어려움',      'key': 'seoul',              'threshold': 15, 'condition': '서울 소재 장소 15곳 방문하기'},
    {'id': 'gyeonggi_wanderer',   'name': '경기 유랑자',             'flavor': '경기도 한 바퀴는 기본 코스.',                         'tier': '어려움',      'key': 'gyeonggi',           'threshold': 15, 'condition': '경기 소재 장소 15곳 방문하기'},
    {'id': 'little_buddha',       'name': '내 안의 작은 부처',        'flavor': '어느새 합장이 자연스러워졌다.',                       'tier': '어려움',      'key': 'temple',             'threshold': 15, 'condition': '사찰 15곳 방문하기'},
    {'id': 'royal_blood',         'name': '전생에 왕족이었나?',       'flavor': '궁궐 마루가 내 집처럼 익숙하다.',                     'tier': '어려움',      'key': 'palace',             'threshold': 6,  'condition': '궁궐 6곳 방문하기'},
    {'id': 'metro_conqueror',     'name': '수도권 정복자',           'flavor': '서울도 경기도 다 내 구역.',                          'tier': '어려움',      'key': 'metro_min',          'threshold': 10, 'condition': '서울·경기 각각 10곳씩 방문하기'},
    {'id': 'culture_nomad',       'name': '문화 노마드',             'flavor': '어디든 떠나는 게 일상이 된 사람.',                     'tier': '어려움',      'key': 'total',              'threshold': 15, 'condition': '장소 15곳 방문하기'},
    {'id': 'joseon_witness',      'name': '조선왕조 500년 산증인',    'flavor': '조선시대 유적은 발도장 다 찍었다.',                    'tier': '매우 어려움', 'key': 'era_joseon',         'threshold': 35, 'condition': '조선시대 유적 35곳 방문하기'},
    {'id': 'history_geek',        'name': '역사 덕후',               'flavor': '주말마다 박물관·유적 투어는 국룰.',                    'tier': '매우 어려움', 'key': 'total',              'threshold': 30, 'condition': '장소 30곳 방문하기'},
    {'id': 'heritage_conqueror',  'name': '문화유산 정복자',          'flavor': '이 나라 문화유산은 이제 내 손바닥 안.',                 'tier': '매우 어려움', 'key': 'total',              'threshold': 50, 'condition': '장소 50곳 방문하기'},
]

BADGE_MAP = {b['id']: b for b in BADGE_DEFS}


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


def compute_badges(target):
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
            'condition': b['condition'],
            'earned': progress >= threshold,
            'progress': min(progress, threshold),
            'threshold': threshold,
        })
    return badges


def get_badge_name(user):
    """유저가 선택한 대표 칭호 이름을 반환. 실제로 달성하지 못한 칭호면 표시하지 않는다."""
    try:
        bid = user.profile.selected_badge
    except Exception:
        return None
    if not bid or bid not in BADGE_MAP:
        return None
    earned_ids = {b['id'] for b in compute_badges(user) if b['earned']}
    if bid not in earned_ids:
        return None
    return BADGE_MAP[bid]['name']
