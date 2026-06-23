from .models import Profile


def get_display_name(user):
    """닉네임이 설정되어 있으면 닉네임, 아니면 아이디(username)를 반환"""
    try:
        return user.profile.display_name
    except Profile.DoesNotExist:
        return user.username


def get_avatar_url(user):
    """프로필 사진 URL, 없으면 기본 이미지 경로를 반환"""
    try:
        return user.profile.profile_image_url
    except Profile.DoesNotExist:
        return '/static/culture/images/default_profile.png'
