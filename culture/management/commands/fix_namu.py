"""
python manage.py fix_namu
괄호 있는 장소명에서 지역명을 추출해 나무위키 링크를 검증·설정합니다.

처리 흐름 (3단계):
  "달마사(서울)"
    1) https://namu.wiki/w/달마사(서울)          → 200이면 사용
    2) https://namu.wiki/w/달마사                → 200이고 페이지에 "서울" 포함이면 사용
    3) namu.wiki 검색 "달마사 서울"              → 결과 페이지에 "서울" 포함이면 사용
    → 모두 실패 시 website='' 로 초기화 (place_detail에서 "—" 표시)

옵션:
  --all    namu.wiki URL 없는 장소까지 포함 (기본: namu.wiki URL 있는 장소만)
"""
import re
import time
import requests
from urllib.parse import quote
from django.core.management.base import BaseCommand
from culture.models import Place

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}
TIMEOUT = 8
DELAY = 0.4

_TAG_RE = re.compile(r'<[^>]+>')
_SPACE_RE = re.compile(r'\s+')


def _fetch(url):
    """GET → (status_code, final_url, plain_text). 실패 시 (None, url, '')."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        text = _TAG_RE.sub(' ', r.text)
        text = _SPACE_RE.sub(' ', text)
        return r.status_code, r.url, text
    except requests.exceptions.RequestException:
        return None, url, ''


def _namu_url(name):
    return f'https://namu.wiki/w/{quote(name)}'


def _search_namu(base_name, location):
    """
    나무위키 검색으로 base_name + location 검증.
    성공 시 URL 반환, 실패 시 None.
    """
    query = f'{base_name} {location}' if location else base_name
    search_url = f'https://namu.wiki/Search?q={quote(query)}'
    status, final_url, text = _fetch(search_url)
    time.sleep(DELAY)
    if status != 200:
        return None

    # 검색이 문서로 바로 리다이렉트된 경우
    if '/w/' in final_url:
        if not location or location in text:
            return final_url
        return None

    # 검색 결과 페이지: /w/ 링크 중 상위 5개 확인
    raw_links = re.findall(r'href="/w/([^"#?]+)"', text)
    for raw in raw_links[:5]:
        candidate_url = f'https://namu.wiki/w/{raw}'
        s, _, t = _fetch(candidate_url)
        time.sleep(DELAY)
        if s == 200 and (not location or location in t):
            return candidate_url

    return None


def _resolve(place_name):
    """
    place_name에 맞는 나무위키 URL 반환. 없으면 None.
    단계: 전체명 직접 → 괄호 제거 + 지역 검증 → 검색
    """
    paren_match = re.search(r'\((.+?)\)', place_name)
    base_name = re.sub(r'\s*\(.*?\)', '', place_name).strip()
    location = paren_match.group(1) if paren_match else None

    # 1단계: 전체 이름(괄호 포함) 직접 시도
    url_full = _namu_url(place_name)
    status, _, _ = _fetch(url_full)
    time.sleep(DELAY)
    if status == 200:
        return url_full

    # 2단계: 괄호 제거 이름 + 지역 검증
    if location:
        url_base = _namu_url(base_name)
        status2, _, text2 = _fetch(url_base)
        time.sleep(DELAY)
        if status2 == 200 and location in text2:
            return url_base

    # 3단계: 나무위키 검색
    return _search_namu(base_name, location)


class Command(BaseCommand):
    help = '괄호 지역명 검증 + 검색 기반 나무위키 URL 설정'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all', action='store_true',
            help='나무위키 URL 없는 장소까지 포함 (기본: namu.wiki URL 있는 장소만)',
        )

    def handle(self, *args, **options):
        if options['all']:
            qs = Place.objects.filter(website='') | Place.objects.filter(website__contains='namu.wiki')
        else:
            qs = Place.objects.filter(website__contains='namu.wiki')
        places = list(qs.order_by('name'))
        total = len(places)
        self.stdout.write(f'대상 장소 {total}개 처리 시작...\n')

        set_count = 0
        cleared_count = 0

        for i, place in enumerate(places, 1):
            url = _resolve(place.name)
            label = f'[{i:3}/{total}] {place.name}'

            if url:
                place.website = url
                place.save(update_fields=['website'])
                set_count += 1
                self.stdout.write(f'  OK  {label}')
                self.stdout.write(f'       -> {url}')
            else:
                # 유효한 URL 없음 → 빈 값으로 초기화
                if place.website:
                    place.website = ''
                    place.save(update_fields=['website'])
                    cleared_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  --  {label} (나무위키 없음)')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n완료: {set_count}개 URL 설정 / {cleared_count}개 초기화'
            )
        )
