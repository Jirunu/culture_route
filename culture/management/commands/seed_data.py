"""
python manage.py seed_data

예시 유저 100명 + 리뷰 ~600개 + 커뮤니티 코스 60개 + 댓글·좋아요 생성
"""
import math
import random
from itertools import permutations

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db import transaction
from django.test.utils import override_settings

from culture.models import Place, Review, Route, RoutePlace, RouteLike, RouteComment
from accounts.models import UserFollow


# ── 유저 이름 풀 ──────────────────────────────────────────────
PREFIXES = [
    "문화탐방", "역사사랑", "서울나들이", "경기여행", "유적덕후",
    "박물관러", "궁궐탐방", "조선덕후", "고려사랑", "삼국탐험",
    "여행좋아", "문화생활", "주말나들이", "역사공부", "문화재팬",
    "서울탐험", "경기산책", "전통문화", "역사기행", "유물수집가",
]
SUFFIXES = ["하는중", "좋아요", "매니아", "팬클럽", "여행러",
            "생활자", "탐방가", "덕후", "마니아", "사랑꾼"]

# ── 리뷰 텍스트 풀 ─────────────────────────────────────────────
REVIEWS_HISTORIC = [
    "유적지 분위기가 정말 압도적이었어요. 시간 여행을 온 것 같았습니다.",
    "역사 공부를 열심히 했는데도 실제로 보니 감동이 배로 느껴졌어요.",
    "관리가 잘 되어 있고 안내판 설명이 자세해서 이해하기 쉬웠습니다.",
    "아이와 함께 왔는데 살아 있는 역사 교육이 됐어요. 강추합니다!",
    "주변 경관과 어우러진 유적지 모습이 정말 아름다웠어요.",
    "사진 찍기에도 좋고 역사적 의미도 깊은 곳입니다. 꼭 한 번 오세요.",
    "생각보다 규모가 커서 놀랐어요. 천천히 둘러보는 데 두 시간은 필요해요.",
    "발굴 현장을 가까이서 볼 수 있어서 흥미로웠습니다.",
    "해설사 분이 설명을 너무 잘해주셔서 더 재미있게 관람했어요.",
    "조용히 역사를 느끼기 좋은 곳. 복잡한 도심에서 벗어나고 싶을 때 오세요.",
    "입장료가 저렴한데 볼거리는 많아요. 가성비 최고 명소입니다.",
    "유적 보존 상태가 훌륭해요. 이런 문화재를 잘 지켜주셔서 감사합니다.",
    "봄에 방문했는데 꽃과 유적의 조화가 환상적이었어요.",
    "역사에 관심 없어도 분위기만으로 충분히 즐길 수 있는 곳이에요.",
    "주차 공간이 넉넉해서 차 가져가기 편했어요. 가족 나들이 추천!",
]

REVIEWS_MUSEUM = [
    "전시 구성이 체계적으로 잘 되어 있어서 흐름을 따라가기 쉬웠어요.",
    "상설 전시 외에 특별 전시도 있어서 두 번 방문해도 새로운 경험이에요.",
    "디지털 인터랙티브 전시가 인상 깊었어요. 역사가 살아 숨 쉬는 느낌!",
    "어른도 아이도 즐길 수 있는 균형 잡힌 전시였습니다.",
    "유물 하나하나에 자세한 설명이 있어서 혼자 관람해도 충분했어요.",
    "카페와 뮤지엄샵도 잘 돼 있어서 나오기 아쉬울 정도였습니다.",
    "공기도 쾌적하고 전시 조명도 적절해서 눈이 편했어요.",
    "오디오 가이드가 정말 유익해요. 대여 꼭 추천드립니다.",
    "학교 수업 시간에 배운 것들을 직접 눈으로 확인하는 느낌이었어요.",
    "규모는 작지만 알찬 전시로 가득 찬 보석 같은 박물관이에요.",
    "무료 입장인데 이 정도 퀄리티면 정말 대단한 것 같아요.",
    "화장실도 깨끗하고 휴게 공간도 충분해서 편하게 관람했습니다.",
    "전문 큐레이터가 있어서 질문하면 친절하게 답변해줘요.",
    "기획 전시가 정말 볼만했어요. 다음 전시도 기대됩니다!",
    "어린 아이 있는 가족에게도 맞는 눈높이 전시가 많아서 좋았어요.",
]

REVIEWS_PALACE = [
    "궁궐 전체를 돌아보는 데 두 시간이 넘게 걸렸어요. 그만큼 볼거리가 많아요.",
    "수문장 교대 의식을 직접 보니 정말 웅장하고 감동적이었습니다.",
    "한복 입고 방문하면 입장료 무료! 사진도 예쁘게 찍혀요.",
    "야간 개장 때 방문했는데 조명이 어우러진 궁궐 풍경이 환상적이었어요.",
    "왕의 생활 공간을 상상하면서 걸으니 색다른 재미가 있었습니다.",
    "사찰 분위기가 고요하고 평화로워서 마음이 정화되는 느낌이었어요.",
    "단풍 시즌에 방문했는데 궁궐과 단풍의 조화가 정말 그림 같았어요.",
    "외국인 친구 데려왔는데 한국 전통 건축에 감탄을 연발했습니다.",
    "해설 투어 프로그램을 이용하니 훨씬 깊이 있게 이해할 수 있었어요.",
    "영어·일어·중어 안내판이 잘 갖춰져 있어 외국인과 오기에도 좋아요.",
    "아침 일찍 방문하면 한산해서 더 여유롭게 즐길 수 있어요.",
    "계절마다 다른 매력이 있어서 사계절 모두 방문하고 싶은 곳이에요.",
    "연못과 정자가 어우러진 후원 풍경이 특히 인상적이었습니다.",
    "사찰 스님께서 절 역사를 설명해 주셔서 더욱 감동적이었어요.",
    "건물 하나하나의 처마와 단청이 얼마나 정교한지 놀라울 따름이에요.",
]

ALL_REVIEWS = {
    'historic': REVIEWS_HISTORIC,
    'museum':   REVIEWS_MUSEUM,
    'palace':   REVIEWS_PALACE,
}

# ── 짧은 코스 제목 풀 (60분 이내) ────────────────────────────────
SHORT_ROUTE_TITLES = [
    "점심시간 짬짬이 역사 산책", "퇴근 후 30분 문화재 코스", "도심 속 숨은 유적 찾기",
    "지하철 한 정거장 역사 탐방", "걸어서 10분 문화 코스", "빠르게 훑는 궁궐 하이라이트",
    "직장인 반시간 역사 충전", "도보로 즐기는 근처 박물관", "출퇴근길 스쳐가는 유적",
    "집 근처 숨겨진 역사 명소", "자전거로 동네 문화재 투어", "가볍게 한 바퀴 역사 산책",
    "바쁜 일상 속 문화 힐링", "호기심 한 스푼, 역사 한 조각", "점심 산책 문화재 코스",
    "뚜벅이 30분 유적 투어", "짧지만 알찬 역사 코스", "근처 박물관 빠른 관람",
    "도심 소확행 역사 산책", "짧은 여행 긴 여운 문화 코스",
]

# ── 코스 제목 풀 ───────────────────────────────────────────────
ROUTE_TITLES = [
    "서울 도심 역사 한 바퀴", "경기 북부 유적 탐방", "조선 왕조의 흔적을 찾아서",
    "박물관 데이트 코스", "한양 도성 걷기 투어", "일제강점기 역사 기행",
    "고려 문화 유적 여행", "삼국시대 역사 탐방", "현대 문화 예술 코스",
    "경복궁에서 창덕궁까지", "서울 4대 궁궐 순례", "남한산성 역사 트레일",
    "인사동 문화 산책로", "수원 화성 완전 정복", "강화도 역사 기행",
    "북촌 한옥마을 & 박물관", "청계천 따라 역사 기행", "덕수궁 돌담길 코스",
    "경기 도자기 문화 여행", "서울 성곽길 따라 역사 탐방",
    "한강 변 문화재 산책", "조선 왕릉 순례 코스", "불교 사찰 명상 투어",
    "근현대 역사 탐방 루트", "주말 가족 문화 나들이", "어린이와 함께하는 역사 탐방",
    "혼자 떠나는 역사 여행", "커플 문화재 데이트", "경기 남부 유적지 투어",
    "서울 서북권 역사 기행", "광화문 광장 역사 투어", "국립 박물관 완전 공략",
    "경기 동부 문화 투어", "북한산 기슭 사찰 순례", "고양 파주 역사 여행",
    "인천·강화 문화 기행", "안성·용인 도자기 기행", "남양주 조선 왕릉 코스",
    "이천·여주 도자기 & 역사", "의정부·동두천 역사 탐방",
    "삼청동 박물관 거리", "창경궁 & 종묘 코스", "경희궁 & 덕수궁 반일 코스",
    "서촌 문화 산책", "정동길 근대 역사 기행", "낙산 성곽 & 혜화 문화",
    "이태원 & 용산 박물관", "마포 & 합정 문화 코스", "은평 역사 한옥마을",
    "노원 & 도봉 사찰 기행", "강동 & 송파 백제 문화", "관악 & 동작 현충원 참배",
    "양천 & 강서 역사 기행", "구로 & 금천 근대 산업 유산", "도봉 & 강북 사찰 투어",
    "성동 & 광진 역사 탐방", "중구 & 종로 도심 문화 투어", "용산 & 마포 박물관 데이",
]

# ── 코스 댓글 풀 ──────────────────────────────────────────────
COMMENT_TEXTS = [
    "와, 이 코스 정말 알차네요! 저도 꼭 따라가 볼게요.",
    "동선 구성이 너무 좋아요. 이동 거리도 적절하고 볼거리도 많네요.",
    "지난 주말에 이 코스 그대로 다녀왔는데 정말 좋았어요!",
    "사진 찍기 좋은 장소들이 잘 모여 있네요. 감사합니다!",
    "반일 코스로 딱 적당한 것 같아요. 저장해 뒀어요!",
    "아이랑 함께 가기 좋은 코스네요. 다음 주에 가려고 합니다.",
    "이 순서대로 가면 이동이 훨씬 효율적이겠네요. 좋은 정보 감사해요!",
    "전에 비슷하게 다녀왔는데 이렇게 정리하니 더 보기 좋네요.",
    "마지막 장소 정말 강추예요. 저도 최애 장소입니다!",
    "처음 방문하는 곳도 있는데 이번 기회에 가봐야겠어요.",
    "코스 만들어 주셔서 감사해요. 덕분에 여행 계획 세우기 편했어요.",
    "이 코스 자전거로도 도전해볼 수 있을 것 같아요!",
    "대중교통으로 이동하기 좋은 코스네요. 교통 정보도 공유해주세요!",
    "날씨 좋은 날 가기 딱 좋은 코스예요. 봄에 한 번 더 갈 예정이에요.",
    "역사 공부하면서 돌아볼 수 있어서 더 의미 있는 코스네요.",
    "가족 여행으로 계획하고 있었는데 딱 찾던 코스예요!",
    "혼자 가도 외롭지 않을 것 같은 풍성한 코스네요.",
    "점심 식사할 곳도 중간에 있나요? 그 부분이 궁금해요.",
    "주말마다 이런 코스 탐방하는 게 취미인데 이 코스 꼭 도전해볼게요.",
    "사진 찍기 좋은 포인트 알려주시면 더 좋을 것 같아요!",
    "저는 이 코스에 ○○도 추가해서 갔어요. 더 풍성해지더라고요.",
    "계절마다 느낌이 다를 것 같아요. 가을에 꼭 다시 가보고 싶네요.",
    "너무 잘 정리된 코스예요. 팔로우하고 갈게요!",
    "이 코스 덕분에 처음 가보는 장소를 알게 됐어요. 감사합니다!",
    "예상 소요 시간 알려주시면 계획 세우기 더 편할 것 같아요.",
]


def make_username(i):
    prefix = PREFIXES[i % len(PREFIXES)]
    suffix = SUFFIXES[(i // len(PREFIXES)) % len(SUFFIXES)]
    return f"{prefix}{suffix}{i + 1}"


class Command(BaseCommand):
    help = '예시 유저 100명 + 리뷰·코스·댓글·좋아요 시드 데이터 생성'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=100)
        parser.add_argument('--clear', action='store_true', help='기존 시드 데이터 삭제 후 재생성')

    def handle(self, *args, **options):
        if options['clear']:
            self._clear()

        user_count   = options['users']
        places       = list(Place.objects.all())
        if not places:
            self.stdout.write(self.style.ERROR('장소 데이터가 없습니다. 먼저 장소를 등록해주세요.'))
            return

        places_by_cat = {}
        for p in places:
            places_by_cat.setdefault(p.category, []).append(p)

        with transaction.atomic():
            users = self._create_users(user_count)
            self.stdout.write(f'  유저 {len(users)}명 생성 완료')

            review_count = self._create_reviews(users, places, places_by_cat)
            self.stdout.write(f'  리뷰 {review_count}개 생성 완료')

            route_count, like_count, comment_count = self._create_routes(users, places)
            self.stdout.write(f'  코스 {route_count}개 / 좋아요 {like_count}개 / 댓글 {comment_count}개 생성 완료')

            follow_count = self._create_follows(users)
            self.stdout.write(f'  팔로우 {follow_count}개 생성 완료')

        self.stdout.write(self.style.SUCCESS('시드 데이터 생성 완료!'))

    # ── 유저 생성 ─────────────────────────────────────────────
    def _create_users(self, count):
        # MD5로 한 번만 해싱 — 시드 데이터용이므로 보안 불필요, 속도 우선
        fast_hashers = ['django.contrib.auth.hashers.MD5PasswordHasher']
        with override_settings(PASSWORD_HASHERS=fast_hashers):
            hashed_pw = make_password('culture1234!')
        all_names = [make_username(i) for i in range(count)]
        existing = {u.username for u in User.objects.filter(username__in=all_names)}
        to_create = [
            User(username=name, password=hashed_pw)
            for name in all_names if name not in existing
        ]
        if to_create:
            User.objects.bulk_create(to_create)
        return list(User.objects.filter(username__in=all_names))

    # ── 리뷰 생성 ─────────────────────────────────────────────
    def _create_reviews(self, users, places, places_by_cat):
        rating_weights = [1, 2, 5, 15, 27]
        rating_pool = []
        for rating, w in enumerate(rating_weights, 1):
            rating_pool.extend([rating] * w)

        existing = set(Review.objects.values_list('user_id', 'place_id'))
        to_create = []
        for user in users:
            n = random.randint(3, 8)
            candidates = [p for p in places if (user.id, p.id) not in existing]
            sample_places = random.sample(candidates, min(n, len(candidates)))
            for place in sample_places:
                texts = ALL_REVIEWS.get(place.category, REVIEWS_HISTORIC)
                to_create.append(Review(
                    user=user,
                    place=place,
                    rating=random.choice(rating_pool),
                    content=random.choice(texts),
                ))
                existing.add((user.id, place.id))
        Review.objects.bulk_create(to_create)
        return len(to_create)

    # ── 거리 계산 & 동선 최적화 ───────────────────────────────
    @staticmethod
    def _hav(lat1, lon1, lat2, lon2):
        R = 6371000
        p = math.pi / 180
        a = (math.sin((float(lat2) - float(lat1)) * p / 2) ** 2
             + math.cos(float(lat1) * p) * math.cos(float(lat2) * p)
             * math.sin((float(lon2) - float(lon1)) * p / 2) ** 2)
        return 2 * R * math.asin(math.sqrt(a))

    def _optimize_route(self, places):
        """N≤8 완전탐색, N>8 최근접이웃 — 최단 순열 반환"""
        if len(places) <= 1:
            return places

        def total_dist(order):
            return sum(self._hav(order[i].latitude, order[i].longitude,
                                 order[i+1].latitude, order[i+1].longitude)
                       for i in range(len(order) - 1))

        if len(places) <= 8:
            best = min(permutations(places), key=total_dist)
            return list(best)

        # nearest-neighbor greedy
        remaining = list(places)
        route = [remaining.pop(0)]
        while remaining:
            last = route[-1]
            nearest = min(remaining,
                          key=lambda p: self._hav(last.latitude, last.longitude,
                                                  p.latitude, p.longitude))
            remaining.remove(nearest)
            route.append(nearest)
        return route

    @staticmethod
    def _transport_mode(dist_m):
        if dist_m < 2000:  return 'walk'
        if dist_m < 8000:  return 'bike'
        if dist_m < 30000: return 'transit'
        return 'car'

    def _route_stats(self, places, short=False):
        """최적화된 장소 순서로 총 거리(m)·소요시간(분) 계산"""
        dist_m = sum(
            self._hav(places[i].latitude, places[i].longitude,
                      places[i+1].latitude, places[i+1].longitude)
            for i in range(len(places) - 1)
        )
        if short:
            visit_min = len(places) * random.randint(15, 22)  # 장소당 15~22분 (빠른 관람)
            travel_min = max(3, int(dist_m / 1000 * 4))       # 자전거 15km/h 기준
        else:
            visit_min = len(places) * random.randint(40, 80)  # 장소당 40~80분
            travel_min = int(dist_m / 1000 * 3)               # 이동 km당 3분 (차량)
        return int(dist_m), visit_min + travel_min

    # ── 코스 + 좋아요 + 댓글 생성 ─────────────────────────────
    def _create_routes(self, users, places):
        route_count = like_count = comment_count = 0
        mode_choices = ['distance', 'theme', 'time']
        valid_places = [p for p in places if p.latitude and p.longitude]
        all_routes = []

        # ── 짧은 코스 (≤60분, 반경 3km, 2~3곳) ──────────────
        short_titles = SHORT_ROUTE_TITLES[:]
        random.shuffle(short_titles)
        for i, title in enumerate(short_titles[:20]):
            owner = random.choice(users)
            n_places = random.randint(2, 3)
            anchor = random.choice(valid_places)
            for radius_km in (3, 6, 12):
                nearby = [p for p in valid_places
                          if self._hav(anchor.latitude, anchor.longitude,
                                       p.latitude, p.longitude) / 1000 <= radius_km]
                if len(nearby) >= n_places:
                    break
            chosen = random.sample(nearby, min(n_places, len(nearby)))
            chosen = self._optimize_route(chosen)
            total_dist, total_time = self._route_stats(chosen, short=True)
            route = Route.objects.create(
                user=owner, title=title, mode=random.choice(mode_choices),
                transport_mode=self._transport_mode(total_dist),
                total_distance=total_dist, total_time=total_time, is_shared=True,
            )
            for order, place in enumerate(chosen, 1):
                RoutePlace.objects.create(route=route, place=place, order=order)
            all_routes.append(route)
            route_count += 1

        # ── 일반 코스 ────────────────────────────────────────
        long_titles = ROUTE_TITLES[:]
        random.shuffle(long_titles)
        n_routes = min(40, len(long_titles))
        for i in range(n_routes):
            owner = random.choice(users)
            title = long_titles[i]
            n_places = random.randint(3, 6)
            anchor = random.choice(valid_places)
            for radius_km in (15, 25, 40):
                nearby = [p for p in valid_places
                          if self._hav(anchor.latitude, anchor.longitude,
                                       p.latitude, p.longitude) / 1000 <= radius_km]
                if len(nearby) >= n_places:
                    break
            chosen = random.sample(nearby, min(n_places, len(nearby)))
            chosen = self._optimize_route(chosen)
            total_dist, total_time = self._route_stats(chosen)
            route = Route.objects.create(
                user=owner, title=title, mode=random.choice(mode_choices),
                transport_mode=self._transport_mode(total_dist),
                total_distance=total_dist, total_time=total_time, is_shared=True,
            )
            for order, place in enumerate(chosen, 1):
                RoutePlace.objects.create(route=route, place=place, order=order)
            all_routes.append(route)
            route_count += 1

        # 좋아요: bulk_create로 한 번에
        likes_to_create = []
        for route in all_routes:
            likers = random.sample(users, random.randint(0, min(30, len(users))))
            for liker in likers:
                if liker != route.user:
                    likes_to_create.append(RouteLike(user=liker, route=route))
                    like_count += 1
        RouteLike.objects.bulk_create(likes_to_create, ignore_conflicts=True)
        for route in all_routes:
            cnt = RouteLike.objects.filter(route=route).count()
            route.like_count = cnt
        Route.objects.bulk_update(all_routes, ['like_count'])

        # 댓글: bulk_create로 한 번에
        comments_to_create = []
        for route in all_routes:
            commenters = random.sample(users, random.randint(0, min(5, len(users))))
            for commenter in commenters:
                comments_to_create.append(RouteComment(
                    route=route,
                    user=commenter,
                    content=random.choice(COMMENT_TEXTS),
                ))
                comment_count += 1
        RouteComment.objects.bulk_create(comments_to_create)

        return route_count, like_count, comment_count

    # ── 팔로우 관계 생성 ──────────────────────────────────────
    def _create_follows(self, users):
        count = 0
        for user in users:
            n = random.randint(2, 10)
            targets = random.sample([u for u in users if u != user], min(n, len(users) - 1))
            for target in targets:
                _, created = UserFollow.objects.get_or_create(follower=user, following=target)
                if created:
                    count += 1
        return count

    # ── 기존 시드 데이터 삭제 ─────────────────────────────────
    def _clear(self):
        seed_usernames = [make_username(i) for i in range(200)]
        seed_users = User.objects.filter(username__in=seed_usernames)
        deleted = seed_users.count()
        seed_users.delete()
        self.stdout.write(f'  기존 시드 유저 {deleted}명 및 연관 데이터 삭제')
