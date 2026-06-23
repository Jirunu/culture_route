"""
전체 장소 이미지 감사 + 교체 커맨드.
Gemini 비전으로 이미지 적합성 검증 후 부적합 이미지는 TourAPI로 교체.
Usage: python manage.py audit_images [--execute] [--limit N] [--start-id N]
"""
import time
import urllib.parse
from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from culture.models import Place

CATEGORY_CONTENT_TYPE = {
    'historic':  '12',
    'museum':    '14',
    'palace':    '14',
}

PROMPT_VISION = (
    '이 사진이 한국 문화 장소 "{name}"을 대표하는 적합한 사진입니까? '
    '화장실, 지도, 스크린샷, 메뉴판, 안내판만 나온 사진이면 "부적합"이라고만 답하고, '
    '건물 외관·내부 전시·관람 공간 등 장소 소개에 적합한 사진이면 "적합"이라고만 답하세요.'
)


def _check_image(client, model: str, name: str, image_url: str) -> str:
    """'적합' or '부적합' or 'error' 반환."""
    try:
        completion = client.chat.completions.create(
            model=model,
            max_tokens=20,
            extra_body={'reasoning_effort': 'none'},
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'image_url', 'image_url': {'url': image_url}},
                    {'type': 'text', 'text': PROMPT_VISION.format(name=name)},
                ]
            }],
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return 'error'


def _fetch_replacement(name: str, category: str, api_key: str) -> str:
    """TourAPI searchKeyword2로 대체 이미지 URL 탐색. 없으면 빈 문자열."""
    content_type = CATEGORY_CONTENT_TYPE.get(category, '12')
    base = 'https://apis.data.go.kr/B551011/KorService2/searchKeyword2'
    params = {
        'serviceKey':   api_key,
        'numOfRows':    '5',
        'pageNo':       '1',
        'MobileOS':     'ETC',
        'MobileApp':    'AppTesting',
        '_type':        'json',
        'keyword':      name,
        'contentTypeId': content_type,
    }
    try:
        resp = requests.get(base, params=params, timeout=15)
        if not resp.ok:
            return ''
        items = resp.json().get('response', {}).get('body', {}).get('items', '')
        if not items or isinstance(items, str):
            return ''
        item_list = items.get('item', [])
        if isinstance(item_list, dict):
            item_list = [item_list]
        for item in item_list:
            img = item.get('firstimage') or item.get('firstimage2') or ''
            if img:
                return img
        return ''
    except Exception:
        return ''


class Command(BaseCommand):
    help = '전체 장소 이미지 감사 및 부적합 이미지 교체'

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true', help='실제 DB 업데이트 실행')
        parser.add_argument('--limit', type=int, default=0, help='처리 개수 제한 (0=전체)')
        parser.add_argument('--start-id', type=int, default=0, help='시작 ID (재개용)')

    def handle(self, *args, **options):
        execute    = options['execute']
        limit      = options['limit']
        start_id   = options['start_id']

        import openai
        client    = openai.OpenAI(api_key=settings.GEMINI_API_KEY, base_url=settings.GEMINI_BASE_URL)
        model     = settings.GEMINI_MODEL
        api_key   = settings.PUBLIC_DATA_API_KEY

        qs = Place.objects.exclude(image_url='').order_by('id')
        if start_id:
            qs = qs.filter(id__gte=start_id)
        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f'감사 대상: {total}개 (이미지 있는 장소)')

        bad_fixed   = []
        bad_nofix   = []
        error_count = 0
        ok_count    = 0

        for idx, place in enumerate(qs, 1):
            verdict = _check_image(client, model, place.name, place.image_url)

            if verdict == '부적합' or '부적합' in verdict:
                repl = _fetch_replacement(place.name, place.category, api_key)
                if repl and repl != place.image_url:
                    old_url = place.image_url
                    if execute:
                        place.image_url = repl
                        place.save(update_fields=['image_url'])
                    bad_fixed.append((place.id, place.name, old_url, repl))
                    self.stdout.write(
                        f'[{idx}/{total}] 부적합→교체 [{place.id}] {place.name}'
                    )
                else:
                    old_url = place.image_url
                    if execute:
                        place.image_url = ''
                        place.save(update_fields=['image_url'])
                    bad_nofix.append((place.id, place.name, old_url))
                    self.stdout.write(
                        f'[{idx}/{total}] 부적합→대체없음(클리어) [{place.id}] {place.name}'
                    )
            elif verdict == 'error':
                error_count += 1
                if idx % 20 == 0 or error_count <= 3:
                    self.stdout.write(f'[{idx}/{total}] 비전오류 [{place.id}] {place.name}')
            else:
                ok_count += 1
                if idx % 50 == 0:
                    self.stdout.write(f'[{idx}/{total}] 진행중 ... 적합 {ok_count}개 누적')

            # API 레이트 리밋 방지
            time.sleep(0.3)

        mode = '(실행)' if execute else '(dry-run)'
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'[완료] {mode}')
        self.stdout.write(f'  적합:         {ok_count}개')
        self.stdout.write(f'  부적합→교체:  {len(bad_fixed)}개')
        self.stdout.write(f'  부적합→클리어:{len(bad_nofix)}개')
        self.stdout.write(f'  비전오류:     {error_count}개')

        if bad_fixed:
            self.stdout.write('\n--- 교체 완료 목록 ---')
            for pid, name, old, new in bad_fixed:
                self.stdout.write(f'  [{pid}] {name}')
                self.stdout.write(f'       이전: {old}')
                self.stdout.write(f'       신규: {new}')

        if bad_nofix:
            self.stdout.write('\n--- 대체 이미지 없음 (클리어) ---')
            for pid, name, old in bad_nofix:
                self.stdout.write(f'  [{pid}] {name}  (이전: {old})')
