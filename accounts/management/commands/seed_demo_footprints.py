import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.badges import compute_badges
from accounts.models import Profile
from culture.models import Place, Route, RoutePlace


class Command(BaseCommand):
    help = (
        '발자취가 없는 기존 유저들에게 무작위 장소 방문 기록을 부여해 '
        '커뮤니티에서 실제로 달성한 칭호가 보이도록 합니다. '
        '이미 발자취가 있는 유저(직접 여행을 다녀온 유저, legend/ADMIN 등)는 건드리지 않습니다.'
    )

    def handle(self, *args, **kwargs):
        all_places = list(Place.objects.all())
        if not all_places:
            self.stdout.write(self.style.WARNING('등록된 장소가 없습니다.'))
            return

        count = 0
        for user in User.objects.all():
            if Route.objects.filter(user=user, is_footprint=True).exists():
                continue

            n = random.randint(3, 40)
            sample = random.sample(all_places, min(n, len(all_places)))
            route = Route.objects.create(
                user=user, title='나의 발자취', mode='distance',
                is_shared=False, is_footprint=True,
            )
            RoutePlace.objects.bulk_create([
                RoutePlace(route=route, place=p, order=i) for i, p in enumerate(sample, start=1)
            ])

            earned = [b for b in compute_badges(user) if b['earned']]
            if earned:
                best = max(earned, key=lambda b: b['threshold'])
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.selected_badge = best['id']
                profile.save()

            count += 1

        self.stdout.write(self.style.SUCCESS(f'{count}명에게 데모 발자취를 부여했습니다.'))
