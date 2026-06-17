from .models import Profile


def get_display_name(user):
    """닉네임이 설정되어 있으면 닉네임, 아니면 아이디(username)를 반환"""
    try:
        return user.profile.display_name
    except Profile.DoesNotExist:
        return user.username
