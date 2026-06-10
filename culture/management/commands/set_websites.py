"""
python manage.py set_websites
직접 조사한 공식 홈페이지 URL을 Place.website 에 저장합니다.
"""
from django.core.management.base import BaseCommand
from culture.models import Place

_ROYAL_TOMBS = 'https://royaltombs.cha.go.kr/'

WEBSITE_MAP = [
    # ── 궁궐 ─────────────────────────────────────────────────
    ('경복궁',   'https://royal.khs.go.kr/ROYAL/contents/menuInfo-gbg.do?grpCode=gbg'),
    ('창덕궁',   'https://royal.khs.go.kr/ROYAL/contents/menuInfo-gbg.do?grpCode=cdg'),
    ('창경궁',   'https://cgg.cha.go.kr/'),
    ('덕수궁',   'https://royal.khs.go.kr/ROYAL/contents/menuInfo-gbg.do?grpCode=dsg'),
    ('경희궁',   'https://royal.khs.go.kr/ROYAL/contents/R110000000.do'),
    ('사직단',   'https://royal.khs.go.kr/ROYAL/contents/menuInfo-sag.do?grpCode=sag'),
    ('종묘',     'https://jm.cha.go.kr/'),
    ('운현궁',   'https://www.unhyeongung.or.kr/'),
    # ── 조선왕릉 (궁능유적본부) ──────────────────────────────
    ('서삼릉',       _ROYAL_TOMBS),
    ('선릉과 정릉',  _ROYAL_TOMBS),
    ('태릉강릉',     _ROYAL_TOMBS),
    ('헌릉',         _ROYAL_TOMBS),
    ('파주 삼릉',    _ROYAL_TOMBS),
    ('파주 장릉',    _ROYAL_TOMBS),
    ('김포 장릉',    _ROYAL_TOMBS),
    ('온릉',         _ROYAL_TOMBS),
    ('융건릉',       _ROYAL_TOMBS),
    ('광릉',         _ROYAL_TOMBS),
    # ── 성곽·산성 ────────────────────────────────────────────
    ('수원화성',  'https://www.visitsuwon.or.kr/base/main/view'),
    ('화성행궁',  'https://www.suwon.go.kr/web/visitsuwon/hs02/pages.do'),
    ('남한산성',  'https://www.gg.go.kr/namhansansung-2/main.do'),
    ('행주산성',  'https://www.goyangsi.go.kr/culture/tour/tourDetail.do?sn=10112'),
    ('광화문',    'https://gwanghwamun.seoul.go.kr/'),
    ('흥인지문',  'https://www.jongno.go.kr/jongnolife/culture/heritageDetail.do?heritageId=13'),
    # ── 사찰 ─────────────────────────────────────────────────
    ('조계사',    'https://www.jogyesa.kr/'),
    ('봉은사',    'https://www.bongeunsa.org/'),
    ('진관사',    'https://www.jinkwansa.org/'),
    ('길상사',    'https://www.gilsangsa.or.kr/'),
    ('봉선사',    'https://www.bongsunsa.net/'),
    ('봉원사',    'https://www.bongwonsa.or.kr/'),
    ('도선사',    'https://doseonsa.org/'),
    ('용주사',    'https://www.yongjoosa.or.kr/'),
    ('신륵사',    'https://www.silleuksa.org/'),
    # ── 성지·성당 ────────────────────────────────────────────
    ('명동성당',         'https://www.mdsd.or.kr/'),
    ('서소문성지',       'https://www.seosomun.org/'),
    ('절두산',           'https://www.jeoldusan.or.kr/'),
    # ── 국립박물관·미술관 ─────────────────────────────────────
    ('국립중앙박물관',   'https://www.museum.go.kr/'),
    ('국립민속박물관',   'https://www.nfm.go.kr/'),
    ('국립고궁박물관',   'https://www.gogung.go.kr/'),
    ('국립한글박물관',   'https://www.hangeul.go.kr/'),
    ('국립현대미술관',   'https://www.mmca.go.kr/'),
    ('국립항공박물관',   'https://www.aviation.or.kr/'),
    ('대한민국역사박물관', 'https://www.much.go.kr/'),
    ('국립국악',         'https://www.gugak.go.kr/'),
    ('한성백제박물관',   'https://baekjemuseum.seoul.go.kr/'),
    ('전곡선사박물관',   'https://jgpm.ggcf.kr/'),
    ('실학박물관',       'https://silhak.ggcf.kr/'),
    ('한국만화박물관',   'https://www.komacon.kr/comicsmuseum/'),
    # ── 서울시립 박물관·미술관 ───────────────────────────────
    ('서울역사박물관',   'https://museum.seoul.go.kr/'),
    ('서울생활사박물관', 'https://museum.seoul.go.kr/slhm/'),
    ('서울시립미술관',   'https://sema.seoul.go.kr/'),
    ('서울공예박물관',   'https://craftmuseum.seoul.go.kr/'),
    ('서울식물원',       'https://botanicpark.seoul.go.kr/'),
    ('서울시립과학관',   'https://science.seoul.go.kr/'),
    # ── 경기도 박물관 ────────────────────────────────────────
    ('경기도박물관',       'https://musenet.ggcf.kr/'),
    ('경기도어린이박물관', 'https://gcm.ggcf.kr/'),
    ('수원시립미술관',     'https://suma.suwon.go.kr/'),
    ('화성박물관',         'https://smuseum.suwon.go.kr/hs/main/view'),
    ('추사박물관',         'https://www.gccity.go.kr/museum.do'),
    ('양주시립회암사지박물관', 'https://www.yangju.go.kr/museum/index.do'),
    ('남양주시립박물관',   'https://www.nyj.go.kr/museum/index.do'),
    # ── 기념관·역사관 ────────────────────────────────────────
    ('전쟁기념관',         'https://www.warmemo.or.kr/'),
    ('서대문형무소역사관', 'https://sphh.sscmc.or.kr/'),
    ('백범김구기념관',     'https://www.kimkoomuseum.org/'),
    ('전태일기념관',       'https://www.taeil.org/'),
    ('윤봉길',             'https://www.yunbonggil.or.kr/'),
    ('손기정기념관',       'https://www.sonkeechung.com/'),
    ('윤동주문학관',       'https://www.jfac.or.kr/site/main/content/yoondj01'),
    ('배재학당역사박물관', 'https://www.pcu.ac.kr/appenzeller'),
    ('국립4',              'https://www.mpva.go.kr/419/index.do'),
    ('국회박물관',         'https://museum.assembly.go.kr/museum/main/main.do'),
    ('안성 3·1운동기념관', 'https://www.anseong.go.kr/tourPortal/41/main.do'),
    # ── 유적지 ───────────────────────────────────────────────
    ('암사동',    'https://sunsa.gangdong.go.kr/'),
    ('한국민속촌', 'https://www.koreanfolk.co.kr/'),
    ('독립기념관', 'https://i815.or.kr/'),
    # ── 마을·거리 ────────────────────────────────────────────
    ('북촌한옥마을', 'https://hanok.seoul.go.kr/front/kor/town/town01.do'),
    ('남산골한옥마을', 'https://www.hanokmaeul.or.kr/'),
    ('은평한옥마을', 'https://hanok.seoul.go.kr/front/kor/town/town03.do'),
    ('인사동',       'https://www.insadong.info/'),
    # ── 수목원·공원 ──────────────────────────────────────────
    ('국립수목원',  'https://www.kna.go.kr/'),
    ('서울숲',      'https://seoulforest.or.kr/'),
    ('서울대공원',  'https://grandpark.seoul.go.kr/'),
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
