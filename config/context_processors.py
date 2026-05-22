from django.conf import settings


def public_settings(request):
    return {'KAKAO_JS_KEY': getattr(settings, 'KAKAO_JS_KEY', '')}
