from django.core.management.base import BaseCommand
from culture.models import Place, Theme


ERA_MAP = {
    # ── 삼국시대 ──────────────────────────────────
    'three_kingdoms': [
        '전곡선사박물관',          # 구석기 선사유적
        '시흥오이도박물관',         # 오이도 선사유적
        '하남역사박물관',           # 백제 위례성 관련
    ],

    # ── 고려시대 ──────────────────────────────────
    'goryeo': [
        '양주시립회암사지박물관',    # 고려 나옹왕사 창건 사찰
        '유금와당박물관',           # 삼국·고려 시대 기와
    ],

    # ── 조선시대 ──────────────────────────────────
    'joseon': [
        '국립국악박물관',
        '은평역사한옥박물관',
        '서울역사박물관',
        '북촌생활사박물관',
        '가회민화박물관',
        '국립기상박물관',           # 측우기 = 세종대왕
        '떡박물관',
        '짚풀생활사박물관',
        '목인박물관 목석원',
        '호림박물관 신림본관',
        '한상수자수박물관',
        '우리옛돌박물관',
        '경기여고 경운박물관(서울)',
        '서울공예박물관',
        '농업박물관',
        '서소문성지역사박물관',      # 조선 말기 천주교 박해
        '용인시박물관',
        '한국조리박물관',
        '충현박물관',
        '여성생활사박물관',
        '화성시 향토박물관',
        '아해박물관',
        '이경순 소리박물관',
        '국립지도박물관',           # 대동여지도 등
        '평택농업전시관',
        '목아박물관',
        '풀짚공예박물관',
        '박물관 얼굴',              # 전통 탈/가면
        '덕포진교육박물관',         # 신미양요(1871) = 조선
        '추사박물관(과천)',          # 추사 김정희
        '두루뫼박물관',
        '성호박물관',               # 이익(성호)
        '벽봉한국장신구박물관',
        '세미원 연꽃박물관',
        '판교박물관',
        '수원화성박물관',           # 수원화성 = 정조
        '남양주시립박물관',
        '실학박물관',
        '한과문화박물관 한가원',
        '예아리박물관',
        '다도박물관',
        '수원광교박물관',
    ],

    # ── 일제강점기 ────────────────────────────────
    'japanese': [
        '백범김구기념관',
        '식민지역사박물관',
        '매헌 윤봉길의사 기념관',
        '배재학당역사박물관',       # 1885 창립
        '손기정기념관',             # 1936 베를린올림픽
        '전쟁과여성인권박물관',     # 위안부
        '이화여고100주년기념관',    # 1886 창립
        '윤동주문학관',
        '고당기념관',               # 조만식
        '안성 3·1운동기념관',
        '한국기독교역사박물관',     # 근대 선교
        '몽양여운형기념관',
        '최용신기념관',
        '조소앙기념관',
    ],
}


class Command(BaseCommand):
    help = '박물관 시대 분류를 이름 기반으로 재설정'

    def handle(self, *args, **options):
        themes = {t.era: t for t in Theme.objects.all()}
        updated = 0
        skipped = 0

        for era, names in ERA_MAP.items():
            theme = themes.get(era)
            if not theme:
                self.stderr.write(f'테마 없음: {era}')
                continue
            for name in names:
                try:
                    place = Place.objects.get(name=name, category='museum')
                    old_era = place.theme.era if place.theme else 'none'
                    if old_era == era:
                        skipped += 1
                        continue
                    place.theme = theme
                    place.save(update_fields=['theme'])
                    self.stdout.write(f'  [{old_era} → {era}] {name}')
                    updated += 1
                except Place.DoesNotExist:
                    self.stderr.write(f'  장소 없음: {name}')
                except Place.MultipleObjectsReturned:
                    places = Place.objects.filter(name=name, category='museum')
                    for p in places:
                        old_era = p.theme.era if p.theme else 'none'
                        p.theme = theme
                        p.save(update_fields=['theme'])
                        self.stdout.write(f'  [{old_era} → {era}] {name} (id={p.id})')
                        updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n완료: {updated}개 업데이트, {skipped}개 이미 정확'
        ))
