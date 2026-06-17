from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user           = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    selected_badge = models.CharField(max_length=40, blank=True, default='', verbose_name='대표 칭호')
    nickname       = models.CharField(max_length=30, unique=True, null=True, blank=True, verbose_name='닉네임')

    class Meta:
        verbose_name = '프로필'
        verbose_name_plural = '프로필 목록'

    def __str__(self):
        return f'{self.user.username}의 프로필'

    @property
    def display_name(self):
        return self.nickname or self.user.username


class UserFollow(models.Model):
    follower  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_set')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers_set')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        verbose_name = '팔로우'
        verbose_name_plural = '팔로우 목록'

    def __str__(self):
        return f'{self.follower.username} → {self.following.username}'
