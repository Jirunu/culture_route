from django.db import models
from django.contrib.auth.models import User


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
