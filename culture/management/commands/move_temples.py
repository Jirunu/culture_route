import re
from django.core.management.base import BaseCommand
from culture.models import Place


def is_temple(name: str) -> bool:
    clean = re.sub(r'[\(\[（【][^\)\]）】]*[\)\]）】]', '', name).strip()
    return (
        clean.endswith('사') or
        clean.endswith('암') or
        clean.endswith('절') or
        '선원' in name or
        '사찰' in name or
        clean.endswith('정사') or
        clean.endswith('도량')
    )


class Command(BaseCommand):
    help = 'historic 카테고리 중 사찰·암자를 palace 카테고리로 이동합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true',
                            help='실제로 DB 변경 수행 (없으면 목록만 출력)')

    def handle(self, *args, **kwargs):
        execute = kwargs['execute']
        temples = [p for p in Place.objects.filter(category='historic') if is_temple(p.name)]

        self.stdout.write(f'이동 대상 사찰·암자: {len(temples)}곳\n')
        for p in temples:
            self.stdout.write(f'  - {p.name} ({p.get_region_display()})')

        if not execute:
            self.stdout.write('\n[DRY-RUN] --execute 플래그를 추가하면 실제 변경됩니다.')
            return

        if not temples:
            self.stdout.write('[SKIP] 이동 대상 없음')
            return

        ids = [p.id for p in temples]
        Place.objects.filter(id__in=ids).update(category='palace')
        self.stdout.write(self.style.SUCCESS(f'\n[DONE] {len(temples)}곳 palace로 이동 완료'))
