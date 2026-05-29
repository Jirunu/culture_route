import json
import re
import requests
from django.conf import settings
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

GMS_BASE = settings.GMS_BASE_URL
GMS_MODEL = settings.GMS_MODEL


def _headers():
    return {
        'Authorization': f'Bearer {settings.GMS_API_KEY}',
        'Content-Type': 'application/json',
    }


def _extract_json(text):
    """텍스트에서 JSON 객체를 추출"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*?\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


_SYSTEM_PROMPT = (
    '당신은 친절하고 유용한 AI 어시스턴트입니다. '
    '단, 폭력·불법·유해한 질문에는 반드시 첫 줄에 "[BLOCKED]"라고만 쓰고 그 이상 답하지 마세요. '
    '그 외 모든 질문에는 정상적으로 친절하게 답변하세요.'
)


def _call_llm(messages):
    resp = requests.post(
        f'{GMS_BASE}/chat/completions',
        headers=_headers(),
        json={'model': GMS_MODEL, 'messages': messages},
        timeout=30,
    )
    if not resp.ok:
        raise Exception(f'{resp.status_code} {resp.reason} — {resp.text[:300]}')
    return resp.json()['choices'][0]['message']['content']


# ── F102 ──────────────────────────────────────────────────────────────────────

@require_http_methods(['POST'])
@login_required_json
def guardrail(request):
    """Guardrail만 독립 호출 (Postman 테스트용)"""
    data = json.loads(request.body)
    question = data.get('question', '').strip()
    if not question:
        return JsonResponse({'error': '질문을 입력하세요.'}, status=400)
    try:
        content = _call_llm([
            {'role': 'system', 'content': _SYSTEM_PROMPT},
            {'role': 'user', 'content': question},
        ])
        is_valid = not content.strip().startswith('[BLOCKED]')
        return JsonResponse({'is_valid': is_valid})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── F101 + F103 ───────────────────────────────────────────────────────────────

@require_http_methods(['POST'])
@login_required_json
def chat(request):
    """Guardrail + LLM 응답을 단일 API 호출로 처리"""
    data = json.loads(request.body)
    question = data.get('question', '').strip()
    history = data.get('history', [])

    if not question:
        return JsonResponse({'error': '질문을 입력하세요.'}, status=400)

    messages = [{'role': 'system', 'content': _SYSTEM_PROMPT}]
    messages.extend(history[-10:])
    messages.append({'role': 'user', 'content': question})

    try:
        answer = _call_llm(messages)
    except Exception as e:
        return JsonResponse({'error': f'LLM 오류: {e}'}, status=500)

    if answer.strip().startswith('[BLOCKED]'):
        return JsonResponse({'is_valid': False, 'answer': None})

    return JsonResponse({'is_valid': True, 'answer': answer})


# ── F105 ──────────────────────────────────────────────────────────────────────

_GEMINI_IMAGE_MODEL = 'gemini-2.0-flash-exp-image-generation'

# GMS_BASE_URL 값에 무관하게 루트만 추출해 Gemini 경로 조립
# 예) https://gms.ssafy.io/gmsapi/api.openai.com/v1 → https://gms.ssafy.io/gmsapi/
import re as _re
_gms_root = _re.match(r'(https?://[^/]+/gmsapi/)', GMS_BASE)
_gms_root = _gms_root.group(1) if _gms_root else GMS_BASE.rstrip('/') + '/'
_GEMINI_BASE = f'{_gms_root}generativelanguage.googleapis.com/v1beta'


@require_http_methods(['POST'])
@login_required_json
def image_generate(request):
    """이미지 생성 — Gemini generateContent API 사용"""
    data = json.loads(request.body)
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return JsonResponse({'error': '프롬프트를 입력하세요.'}, status=400)

    url = (
        f'{_GEMINI_BASE}/models/{_GEMINI_IMAGE_MODEL}:generateContent'
        f'?key={settings.GMS_API_KEY}'
    )
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'responseModalities': ['IMAGE']},
    }
    gemini_headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': settings.GMS_API_KEY,
    }
    try:
        resp = requests.post(url, headers=gemini_headers, json=payload, timeout=60)
        if not resp.ok:
            raise Exception(f'{resp.status_code} {resp.reason} — {resp.text[:300]}')

        parts = resp.json()['candidates'][0]['content']['parts']
        for part in parts:
            if 'inlineData' in part:
                b64 = part['inlineData']['data']
                mime = part['inlineData'].get('mimeType', 'image/png')
                return JsonResponse({'image_url': f'data:{mime};base64,{b64}'})

        raise Exception('이미지 데이터를 찾을 수 없습니다.')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── F106 ──────────────────────────────────────────────────────────────────────

@require_http_methods(['POST'])
@login_required_json
def score(request):
    """질문-답변 적합도 점수 계산 (0~100)"""
    data = json.loads(request.body)
    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    if not question or not answer:
        return JsonResponse({'error': '질문과 답변을 모두 입력하세요.'}, status=400)

    payload = {
        'model': GMS_MODEL,
        'messages': [
            {
                'role': 'system',
                'content': (
                    '질문과 답변을 분석하여 답변이 질문에 얼마나 적합한지 0~100 점수로 평가하세요. '
                    '반드시 {"score": 숫자, "reason": "한 줄 이유"} 형식의 JSON만 반환하세요.'
                ),
            },
            {'role': 'user', 'content': f'질문: {question}\n답변: {answer}'},
        ],
    }
    try:
        resp = requests.post(
            f'{GMS_BASE}/chat/completions',
            headers=_headers(),
            json=payload,
            timeout=15,
        )
        if not resp.ok:
            raise Exception(f'{resp.status_code} — {resp.text[:300]}')
        result = _extract_json(resp.json()['choices'][0]['message']['content'])
        return JsonResponse({
            'score': int(result.get('score', 0)),
            'reason': result.get('reason', ''),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
