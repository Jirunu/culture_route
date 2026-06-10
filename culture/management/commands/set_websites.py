"""
python manage.py set_websites
직접 조사한 공식 홈페이지 URL을 Place.website 에 저장합니다.
"""
from django.core.management.base import BaseCommand
from culture.models import Place

# 장소명(부분 일치) → 공식 홈페이지 URL
# 더 구체적인 이름을 먼저 작성 (긴 것 우선 매칭)
WEBSITE_MAP = [
    # ── 궁궐·왕릉 ────────────────────────────────────────────
    ('경복궁',   'https://royal.khs.go.kr/ROYAL/contents/menuInfo-gbg.do?grpCode=gbg'),
    ('창덕궁',   'https://royal.khs.go.kr/ROYAL/contents/menuInfo-gbg.do?grpCode=cdg'),
    ('창경궁',   'https://cgg.cha.go.kr/'),
    ('덕수궁',   'https://royal.khs.go.kr/ROYAL/contents/menuInfo-gbg.do?grpCode=dsg'),
    ('경희궁',   'https://royal.khs.go.kr/ROYAL/contents/R110000000.do'),
    ('사직단',   'https://royal.khs.go.kr/ROYAL/contents/menuInfo-sag.do?grpCode=sag'),
    ('종묘',     'https://jm.cha.go.kr/'),
    ('수원화성', 'https://www.visitsuwon.or.kr/base/main/view'),
    ('화성행궁', 'https://www.suwon.go.kr/web/visitsuwon/hs02/pages.do'),
    ('남한산성', 'https://www.gg.go.kr/namhansansung-2/main.do'),
    ('행주산성', 'https://www.goyangsi.go.kr/culture/tour/tourDetail.do?sn=10112'),
    # ── 사찰 ─────────────────────────────────────────────────
    ('조계사',   'https://www.jogyesa.kr/'),
    ('봉은사',   'https://www.bongeunsa.org/'),
    ('진관사',   'https://www.jinkwansa.org/'),
    ('길상사',   'https://www.gilsangsa.or.kr/'),
    ('흥천사',   'https://www.heungcheonsa.org/'),
    # ── 국립박물관·미술관 ──────────────────────────────────────
    ('국립중앙박물관',   'https://www.museum.go.kr/'),
    ('국립민속박물관',   'https://www.nfm.go.kr/'),
    ('국립고궁박물관',   'https://www.gogung.go.kr/'),
    ('국립한글박물관',   'https://www.hangeul.go.kr/'),
    ('국립현대미술관',   'https://www.mmca.go.kr/'),
    ('국립항공박물관',   'https://www.aviation.or.kr/'),
    ('대한민국역사박물관', 'https://www.much.go.kr/'),
    # ── 서울시립 박물관·미술관 ────────────────────────────────
    ('서울역사박물관',   'https://museum.seoul.go.kr/'),
    ('서울시립미술관',   'https://sema.seoul.go.kr/'),
    ('서울공예박물관',   'https://craftmuseum.seoul.go.kr/'),
    ('서울식물원',      'https://botanicpark.seoul.go.kr/'),
    ('서울시립과학관',   'https://science.seoul.go.kr/'),
    # ── 경기도 박물관·미술관 ──────────────────────────────────
    ('경기도박물관',     'https://musenet.ggcf.kr/'),
    ('경기도어린이박물관', 'https://gcm.ggcf.kr/'),
    ('수원시립미술관',   'https://suma.suwon.go.kr/'),
    ('화성박물관',      'https://smuseum.suwon.go.kr/hs/main/view'),
    # ── 기념관·역사관 ─────────────────────────────────────────
    ('전쟁기념관',       'https://www.warmemo.or.kr/'),
    ('서대문형무소역사관', 'https://sphh.sscmc.or.kr/'),
    ('한국민속촌',       'https://www.koreanfolk.co.kr/'),
    ('독립기념관',       'https://i815.or.kr/'),
    # ── 마을·거리 ─────────────────────────────────────────────
    ('북촌한옥마을',     'https://hanok.seoul.go.kr/front/kor/town/town01.do'),
    ('남산골한옥마을',   'https://www.hanokmaeul.or.kr/'),
    ('은평한옥마을',     'https://hanok.seoul.go.kr/front/kor/town/town03.do'),
    ('인사동',          'https://www.insadong.info/'),
    ('수원 행리단길',    'https://www.suwon.go.kr/'),
    # ── 기념관·역사관 (추가) ──────────────────────────────────
    ('백범김구기념관',   'https://www.kimkoomuseum.org/'),
    ('전태일기념관',     'https://www.taeil.org/'),
    ('윤봉길',          'https://www.yunbonggil.or.kr/'),
    # ── 궁·고택 (추가) ────────────────────────────────────────
    ('운현궁',          'https://www.unhyeongung.or.kr/'),
    # ── 음악·예술 ─────────────────────────────────────────────
    ('국립국악',         'https://www.gugak.go.kr/'),
    # ── 수목원·공원 ───────────────────────────────────────────
    ('국립수목원',       'https://www.kna.go.kr/'),
    ('서울숲',          'https://seoulforest.or.kr/'),
    ('서울대공원',       'https://grandpark.seoul.go.kr/'),
    ('서울식물원',       'https://botanicpark.seoul.go.kr/'),
]


class Command(BaseCommand):
    help = '공식 홈페이지 URL을 Place.website에 저장합니다'

    def add_arguments(self, parser):
        parser.add_argument('--overwrite', action='store_true',
                            help='이미 website가 있는 장소도 덮어쓰기')

    def handle(self, *args, **options):
        overwrite = options['overwrite']
        updated = skipped = 0

        for keyword, url in WEBSITE_MAP:
            qs = Place.objects.filter(name__icontains=keyword)
            if not overwrite:
                qs = qs.filter(website='')
            count = qs.update(website=url)
            if count:
                self.stdout.write(f'  [{count}건] {keyword} → {url}')
                updated += count
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n완료: {updated}개 업데이트, {skipped}개 키워드 미매칭'
        ))
