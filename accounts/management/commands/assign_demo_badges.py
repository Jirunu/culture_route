import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.badges import BADGE_DEFS
from accounts.models import Profile


class Command(BaseCommand):
    help = '대표 칭호를 아직 선택하지 않은 기존 유저들에게 데모용 칭호를 무작위로 부여합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                             help='이미 칭호가 선택된 유저도 덮어씁니다.')

    def handle(self, *args, **kwargs):
        force = kwargs['force']
        badge_ids = [b['id'] for b in BADGE_DEFS]
        count = 0
        for user in User.objects.all():
            profile, _ = Profile.objects.get_or_create(user=user)
            if profile.selected_badge and not force:
                continue
            profile.selected_badge = random.choice(badge_ids)
            profile.save()
            count += 1
        self.stdout.write(self.style.SUCCESS(f'{count}명에게 데모 칭호를 부여했습니다.'))
