"""
python manage.py check_namu
나무위키 자동 설정 URL이 실제로 존재하는지 HTTP 요청으로 확인합니다.

옵션:
  --fix   404 확인된 URL을 빈 값으로 초기화 (place_detail에서 '—' 표시)
"""
import time
import requests
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
DELAY = 0.4  # 요청 간 딜레이(초) — 서버 부하 방지


class Command(BaseCommand):
    help = '나무위키 URL 유효성 확인 (404 탐지)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='404로 확인된 URL을 빈 값으로 초기화',
        )

    def handle(self, *args, **options):
        fix = options['fix']
        places = list(Place.objects.filter(website__contains='namu.wiki').order_by('name'))
        total = len(places)
        self.stdout.write(f'나무위키 URL {total}개 확인 시작…\n')

        ok_list = []
        fail_list = []

        for i, place in enumerate(places, 1):
            url = place.website
            try:
                resp = requests.get(
                    url, headers=HEADERS, timeout=TIMEOUT,
                    allow_redirects=True,
                )
                status = resp.status_code
            except requests.exceptions.Timeout:
                status = 'timeout'
            except requests.exceptions.RequestException:
                status = 'error'

            label = f'[{i:3}/{total}] {place.name}'
            if status == 200:
                ok_list.append(place)
                self.stdout.write(f'  OK  {label}')
            else:
                fail_list.append(place)
                self.stdout.write(
                    self.style.WARNING(f'  NG  {label}  ({status})')
                )

            time.sleep(DELAY)

        self.stdout.write(f'\n결과: 정상 {len(ok_list)}개 / 오류 {len(fail_list)}개')

        if fail_list:
            self.stdout.write('\n오류 장소 목록:')
            for p in fail_list:
                self.stdout.write(f'  - {p.name}  ({p.website})')

            if fix:
                ids = [p.id for p in fail_list]
                updated = Place.objects.filter(pk__in=ids).update(website='')
                self.stdout.write(
                    self.style.SUCCESS(f'\n{updated}개 URL 초기화 완료.')
                )
            else:
                self.stdout.write(
                    '\n초기화하려면 --fix 옵션을 추가하세요: '
                    'python manage.py check_namu --fix'
                )
        else:
            self.stdout.write(self.style.SUCCESS('\n모든 나무위키 URL 정상.'))
