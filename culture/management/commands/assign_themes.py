import re
from django.core.management.base import BaseCommand
from culture.models import Place, Theme

ERA_KEYWORDS = {
    'japanese': [
        '독립운동', '독립기념', '독립관', '독립문', '서대문형무소', '형무소',
        '순국', '광복', '임시정부', '항일', '삼일운동', '3.1운동', '기미의거', '의거',
    ],
    'three_kingdoms': [
        '삼국', '고구려', '백제', '신라', '가야', '고분군', '토성',
        '석촌동', '풍납토성', '몽촌토성', '아차산', '이성산성',
    ],
    'goryeo': ['고려'],
    'joseon': [
        '조선', '왕릉', '서원', '향교', '사직단', '종묘', '한양도성', '화성행궁',
        '행궁', '성균관', '명륜당', '창덕궁', '경복궁', '창경궁', '덕수궁',
        '동구릉', '서삼릉', '태릉', '선릉', '정릉', '홍릉', '유릉', '광릉', '세검정',
    ],
    'modern': [
        '박물관', '미술관', '기념관', '전시관', '역사관', '전쟁기념',
        '한국전쟁', '625', '근현대', '현대사',
    ],
}

CATEGORY_DEFAULT = {
    'museum':  'modern',
    'palace':  'joseon',
    'historic': 'joseon',
}

ERA_KO = {
    'three_kingdoms': '삼국시대',
    'goryeo':         '고려시대',
    'joseon':         '조선시대',
    'japanese':       '일제강점기',
    'modern':         '현대',
}


def guess_era(name: str, category: str) -> str:
    clean = re.sub(r'[\(\[（【][^\)\]）】]*[\)\]）】]', '', name).strip()
    for era, kws in ERA_KEYWORDS.items():
        for kw in kws:
            if kw in clean:
                return era
    return CATEGORY_DEFAULT.get(category, 'joseon')


class Command(BaseCommand):
    help = '모든 Place에 이름/카테고리 기반으로 Theme(시대)을 자동 할당합니다.'

    def handle(self, *args, **kwargs):
        themes = {t.era: t for t in Theme.objects.all()}
        if not themes:
            self.stdout.write(self.style.ERROR('Theme 데이터가 없습니다. loaddata를 먼저 실행하세요.'))
            return

        total = Place.objects.count()
        assigned = 0
        era_counts = {era: 0 for era in ERA_KEYWORDS}

        for place in Place.objects.all():
            era = guess_era(place.name, place.category)
            era_counts[era] = era_counts.get(era, 0) + 1
            theme = themes.get(era)
            if theme and place.theme_id != theme.pk:
                place.theme = theme
                place.save(update_fields=['theme'])
                assigned += 1

        self.stdout.write('\n[시대별 분류 결과]')
        for era, cnt in era_counts.items():
            self.stdout.write(f'  {ERA_KO.get(era, era):10s}: {cnt:3d}개')

        self.stdout.write(
            self.style.SUCCESS(f'\n[DONE] {total}개 중 {assigned}개 테마 할당 완료')
        )
