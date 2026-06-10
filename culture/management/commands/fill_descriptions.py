import time
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from culture.models import Place

CATEGORY_KO = {
    'historic': '역사 유적',
    'museum':   '박물관·미술관',
    'palace':   '궁궐·사찰',
}


def generate_description(name, category, address):
    gms_url = getattr(settings, 'GMS_BASE_URL', '') + '/chat/completions'
    gms_key = getattr(settings, 'GMS_API_KEY', '')
    model   = getattr(settings, 'GMS_MODEL', 'gpt-4o-mini')
    if not gms_url.strip('/') or not gms_key:
        return None
    prompt = (
        f'다음 장소에 대해 방문자에게 흥미를 줄 수 있는 한국어 한 줄 소개를 50자 이내로 작성해줘. '
        f'문장 부호로 마무리하고, 장소명을 직접 언급하지 마. '
        f'장소명: {name}, 카테고리: {CATEGORY_KO.get(category, category)}, 위치: {address}'
    )
    try:
        resp = requests.post(
            gms_url,
            headers={
                'Authorization': f'Bearer {gms_key}',
                'Content-Type':  'application/json',
            },
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': '한 줄 장소 소개만 출력하세요. 따옴표 없이.'},
                    {'role': 'user',   'content': prompt},
                ],
                'max_completion_tokens': 150,
            },
            timeout=20,
        )
        resp.raise_for_status()
        text = resp.json()['choices'][0]['message']['content'].strip().strip('"\'')
        return text[:200]
    except Exception:
        return None


class Command(BaseCommand):
    help = 'description이 비어있는 Place에 GMS로 한 줄 설명 자동 생성'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50,
                            help='처리 건수 제한 (기본 50)')
        parser.add_argument('--all', action='store_true',
                            help='전체 빈 장소 처리 (--limit 무시)')

    def handle(self, *args, **kwargs):
        qs = Place.objects.filter(description='')
        total_empty = qs.count()
        limit = kwargs['limit']
        do_all = kwargs['all']

        if not do_all:
            qs = qs[:limit]

        target = qs.count()
        self.stdout.write(f'description 없는 장소 총 {total_empty}건 중 {target}건 처리 시작\n')

        ok = fail = 0
        for place in qs:
            desc = generate_description(place.name, place.category, place.address)
            if desc:
                place.description = desc
                place.save(update_fields=['description'])
                self.stdout.write(f'  [OK] {place.name}: {desc[:50]}')
                ok += 1
            else:
                self.stdout.write(f'  [실패] {place.name}')
                fail += 1
            time.sleep(0.3)

        self.stdout.write(self.style.SUCCESS(f'\n[DONE] 성공 {ok}건 / 실패 {fail}건'))
