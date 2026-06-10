from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from functools import wraps


def login_required_json(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


_UNAVAILABLE = JsonResponse({'error': '현재 사용할 수 없는 기능입니다.'}, status=503)


def _unavailable(_request):
    return JsonResponse({'error': '현재 사용할 수 없는 기능입니다.'}, status=503)


@require_http_methods(['POST'])
@login_required_json
def guardrail(request):
    return _unavailable(request)


@require_http_methods(['POST'])
@login_required_json
def chat(request):
    return _unavailable(request)


@require_http_methods(['POST'])
@login_required_json
def image_generate(request):
    return _unavailable(request)


@require_http_methods(['POST'])
@login_required_json
def score(request):
    return _unavailable(request)
