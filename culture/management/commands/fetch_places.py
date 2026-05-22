from django.core.management.base import BaseCommand
from culture.api_clients import fetch_all_heritage
from culture.models import Place

# ── 수집할 카테고리 (역사적 의미 있는 것만) ───────────────────
# contentTypeId=12 관광지: cat2 기준 필터
HISTORIC_CAT2 = {
    'A0201',  # 역사관광지
    'A0205',  # 건축/조형물
}

# contentTypeId=14 문화시설: cat3 기준 필터 (cat2는 항상 A0206)
HISTORIC_CAT3_CT14 = {
    'A02060100',  # 박물관
    'A02060200',  # 기념관
}

CAT2_TO_CATEGORY = {
    'A0201': 'historic',
    'A0205': 'historic',
}

CAT3_PALACE = {'A02010100', 'A02010500'}  # 고궁, 사찰

INDOOR_CATEGORIES = {'museum'}

# ── 현대 시설 제외 키워드 ──────────────────────────────────────
EXCLUDE_KEYWORDS = [
    '전망대', '타워', '롯데월드', '국회의사당',
    '댐', '이포보', '경찰혼', '그리팅맨',
]
EXCLUDE_SUFFIXES = [
    '대교', '교량', '철교', '인도교', '보행교',
    '구름다리', '아치교', '사장교', '현수교',
]


def _map_category(cat2: str, cat3: str, content_type_id: int) -> str:
    if cat3 in CAT3_PALACE:
        return 'palace'
    if content_type_id == 14:
        return 'museum'
    return CAT2_TO_CATEGORY.get(cat2, 'historic')


def _is_historic(name: str, cat2: str, cat3: str, content_type_id: int) -> bool:
    if content_type_id == 14:
        return cat3 in HISTORIC_CAT3_CT14
    if cat2 not in HISTORIC_CAT2:
        return False
    for kw in EXCLUDE_KEYWORDS:
        if kw in name:
            return False
    for suf in EXCLUDE_SUFFIXES:
        if name.endswith(suf):
            return False
    return True


class Command(BaseCommand):
    help = (
        '한국관광공사 API에서 서울·경기 역사 문화 장소를 수집해 DB에 저장합니다.\n'
        '  --dry-run : 실제 저장 없이 수집 결과만 출력\n'
        '  --flush   : 저장 전 기존 Place 데이터 전체 삭제'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='DB 저장 없이 출력만')
        parser.add_argument('--flush',   action='store_true', help='기존 Place 전체 삭제 후 재등록')

    def handle(self, *args, **kwargs):
        dry_run = kwargs['dry_run']
        flush   = kwargs['flush']

        if flush and not dry_run:
            count, _ = Place.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'[FLUSH] 기존 Place {count}건 삭제'))

        targets = [
            {'area_code': 1,  'region': 'seoul',    'label': '서울'},
            {'area_code': 31, 'region': 'gyeonggi', 'label': '경기'},
        ]
        content_types = [
            {'id': 12, 'label': '관광지'},
            {'id': 14, 'label': '문화시설'},
        ]

        total_saved = 0
        total_skip  = 0
        total_dup   = 0

        for tgt in targets:
            for ct in content_types:
                label = f'{tgt["label"]} {ct["label"]} (contentTypeId={ct["id"]})'
                self.stdout.write(f'\n[API] {label} 수집 중...')

                items = fetch_all_heritage(
                    area_code=tgt['area_code'],
                    content_type_id=ct['id'],
                    page_size=100,
                )

                if items is None:
                    self.stdout.write(self.style.ERROR('  [FAIL] API 호출 실패 — 건너뜀'))
                    continue

                self.stdout.write(f'  → {len(items)}건 수신')

                for item in items:
                    name = (item.get('title') or '').strip()
                    lat  = item.get('mapy')
                    lng  = item.get('mapx')
                    addr = (item.get('addr1') or '').strip()
                    img  = (item.get('firstimage') or '').strip()
                    cat2 = item.get('cat2', '')
                    cat3 = item.get('cat3', '')

                    if not name or not lat or not lng:
                        total_skip += 1
                        continue

                    if not _is_historic(name, cat2, cat3, ct['id']):
                        total_skip += 1
                        continue

                    category  = _map_category(cat2, cat3, ct['id'])
                    is_indoor = category in INDOOR_CATEGORIES
                    is_active = False

                    if dry_run:
                        self.stdout.write(f'  [DRY] [{category}] {name}')
                        total_saved += 1
                        continue

                    obj, created = Place.objects.get_or_create(
                        name=name,
                        defaults={
                            'address':   addr,
                            'region':    tgt['region'],
                            'category':  category,
                            'latitude':  float(lat),
                            'longitude': float(lng),
                            'image_url': img,
                            'is_indoor': is_indoor,
                            'is_active': is_active,
                        },
                    )
                    if created:
                        total_saved += 1
                        self.stdout.write(f'  [OK] [{category}] {name}')
                    else:
                        total_dup += 1

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY-RUN] 저장 예정: {total_saved}건  |  제외: {total_skip}건'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'[DONE] 저장: {total_saved}건  |  중복: {total_dup}건  |  제외: {total_skip}건'
            ))
