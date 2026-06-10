import re
import time
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from culture.api_clients import fetch_all_heritage
from culture.models import Place

DETAIL_URL = "https://apis.data.go.kr/B551011/KorService2/detailCommon2"


def get_homepage(content_id, key):
    params = {
        "serviceKey":      key,
        "contentId":       content_id,
        "MobileOS":        "ETC",
        "MobileApp":       "CultureRoute",
        "defaultYN":       "Y",
        "homepageInfoYN":  "Y",
        "_type":           "json",
    }
    try:
        resp = requests.get(DETAIL_URL, params=params, timeout=8)
        if resp.status_code == 429:
            return None  # 쿼터 초과 시그널
        resp.raise_for_status()
        body  = resp.json()["response"]["body"]
        items = body.get("items") or {}
        item  = items.get("item") if isinstance(items, dict) else None
        if not item:
            return ""
        if isinstance(item, list):
            item = item[0]
        html = item.get("homepage") or ""
        m = re.search(r'href=["\']([^"\']+)["\']', html)
        return m.group(1).strip() if m else ""
    except Exception:
        return ""


class Command(BaseCommand):
    help = 'TourAPI 목록 조회 후 장소별 홈페이지 URL을 채웁니다 (쿼터 절약형)'

    def add_arguments(self, parser):
        parser.add_argument('--overwrite', action='store_true',
                            help='이미 website가 있는 장소도 덮어쓰기')

    def handle(self, *args, **options):
        key = settings.PUBLIC_DATA_API_KEY

        # ── 1. TourAPI 목록으로 name → contentid 맵 구축 ──
        self.stdout.write('TourAPI 목록 수집 중 (서울+경기, 관광지+문화시설)…')
        name_to_id = {}
        for area_code in [1, 31]:
            for ct in [12, 14]:
                items = fetch_all_heritage(area_code=area_code, content_type_id=ct) or []
                for item in items:
                    name = (item.get('title') or '').strip()
                    cid  = item.get('contentid') or ''
                    if name and cid:
                        name_to_id[name] = str(cid)
                self.stdout.write(f'  area={area_code} ct={ct}: {len(items)}건')

        self.stdout.write(f'총 API 항목: {len(name_to_id)}건\n')

        # ── 2. DB 장소와 매칭 ─────────────────────────────
        qs = Place.objects.all() if options['overwrite'] else Place.objects.filter(website='')
        places = list(qs)
        total  = len(places)
        self.stdout.write(f'처리할 장소: {total}개\n')

        updated = missed = quota_hit = 0

        for i, place in enumerate(places, 1):
            # 정확 매칭
            cid = name_to_id.get(place.name)
            # 부분 매칭
            if not cid:
                for api_name, api_cid in name_to_id.items():
                    if place.name in api_name or api_name in place.name:
                        cid = api_cid
                        break

            if not cid:
                missed += 1
                self.stdout.write(f'[{i}/{total}] MISS  {place.name}')
                continue

            url = get_homepage(cid, key)

            if url is None:  # 쿼터 초과
                quota_hit += 1
                self.stderr.write('\n⚠ API 쿼터 초과 — 자정 이후 다시 실행하세요.')
                break

            if url:
                place.website = url
                place.save(update_fields=['website'])
                self.stdout.write(f'[{i}/{total}] OK    {place.name}  →  {url}')
                updated += 1
            else:
                missed += 1
                self.stdout.write(f'[{i}/{total}] NONE  {place.name}')

            time.sleep(0.1)

        self.stdout.write(self.style.SUCCESS(
            f'\n완료: {updated}개 업데이트, {missed}개 URL 없음'
            + (f', 쿼터 초과로 중단' if quota_hit else '')
        ))
