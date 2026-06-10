from django.core.management.base import BaseCommand
from culture.api_clients import fetch_all_heritage
from culture.models import Place

MANUAL_IMAGES = {
    '국립민속박물관':     'http://tong.visitkorea.or.kr/cms/resource/05/3590405_image2_1.jpg',
    '서대문형무소역사관': 'http://tong.visitkorea.or.kr/cms/resource/12/3401412_image2_1.JPG',
    '조선왕릉 동구릉':   'http://tong.visitkorea.or.kr/cms/resource/96/2865096_image2_1.jpg',
    '한국민속촌':        'http://tong.visitkorea.or.kr/cms/resource/00/3563100_image2_1.jpg',
}


class Command(BaseCommand):
    help = '한국관광공사 API에서 image_url이 비어있는 장소의 이미지만 채웁니다.'

    def handle(self, *args, **kwargs):
        # API에서 name -> firstimage 수집
        img_map = {}
        for area_code in [1, 31]:
            for ct in [12, 14]:
                items = fetch_all_heritage(area_code=area_code, content_type_id=ct) or []
                for item in items:
                    name = (item.get('title') or '').strip()
                    img  = (item.get('firstimage') or '').strip()
                    if name and img:
                        img_map[name] = img

        img_map.update(MANUAL_IMAGES)
        self.stdout.write(f'API + 수동 이미지: {len(img_map)}건')

        updated = 0
        for place in Place.objects.filter(image_url=''):
            img = img_map.get(place.name)
            # 부분 매칭
            if not img:
                for api_name, url in img_map.items():
                    if place.name in api_name or api_name in place.name:
                        img = url
                        break

            if img:
                place.image_url = img
                place.save(update_fields=['image_url'])
                self.stdout.write(f'  [OK] {place.name}')
                updated += 1
            else:
                self.stdout.write(f'  [MISS] {place.name}')

        self.stdout.write(self.style.SUCCESS(f'\n[DONE] {updated}개 장소 이미지 업데이트 완료'))
