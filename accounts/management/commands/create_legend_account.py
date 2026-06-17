from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Profile
from culture.models import Place, Route, RoutePlace


class Command(BaseCommand):
    help = '모든 칭호를 달성하고 모든 기능에 접근 가능한 슈퍼유저 데모 계정을 생성합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='legend')
        parser.add_argument('--password', default='Legend1234!')

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        password = kwargs['password']

        user, _ = User.objects.get_or_create(username=username)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        title = '모든 칭호 달성 발자취'
        Route.objects.filter(user=user, is_footprint=True, title=title).delete()
        route = Route.objects.create(
            user=user, title=title, mode='distance', is_shared=False, is_footprint=True,
        )
        places = list(Place.objects.all())
        RoutePlace.objects.bulk_create([
            RoutePlace(route=route, place=p, order=i) for i, p in enumerate(places, start=1)
        ])

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.selected_badge = 'heritage_conqueror'
        profile.save()

        self.stdout.write(self.style.SUCCESS(
            f'슈퍼 계정 생성 완료 — username: {username} / password: {password} / 방문 장소: {len(places)}곳'
        ))
