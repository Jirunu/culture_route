import json
import re
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


def login_required_json(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def _unavailable():
    return JsonResponse({'error': '현재 사용할 수 없는 기능입니다.'}, status=503)


def _get_ai_client():
    """GEMINI_API_KEY가 설정돼 있으면 Gemini(OpenAI 호환 엔드포인트) 클라이언트, 아니면 None."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return None
    try:
        import openai as _oai
    except ImportError:
        return None
    return _oai.OpenAI(api_key=api_key, base_url=settings.GEMINI_BASE_URL)


def _parse_json_body(request):
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _strip_json_fence(text):
    if '```' in text:
        text = re.sub(r'```(?:json)?', '', text).strip()
    return text


GUARDRAIL_SYSTEM_PROMPT = (
    '당신은 한국 문화유산·여행 안내 챗봇의 질문 검수기입니다. '
    '사용자 질문이 한국의 문화유산, 역사, 여행지, 동선 등과 관련된 적절한 질문인지 판단하세요. '
    '욕설·혐오·개인정보 요청·서비스와 무관한 질문은 부적절합니다.\n\n'
    'JSON만 응답 (다른 텍스트 없이): {"is_valid": <true|false>, "reason": "<한 줄 이유>"}'
)

CHAT_SYSTEM_PROMPT = (
    '당신은 "나리"라는 이름의 AI 문화 해설 로봇입니다. '
    '갓과 한복을 차려입은 귀여운 로봇 캐릭터로, CultureRoute에서 한국 문화유산·여행 코스를 안내합니다. '
    '친근하고 정중한 안내자 말투를 쓰되 과하게 격식을 차리지 말고, 가끔 자신을 "나리"라 칭하며 답하세요. '
    '여행자의 질문에 친절하고 간결하게(3~4문장 이내) 한국어로 답변하세요.'
)

SCORE_SYSTEM_PROMPT = (
    '당신은 AI 챗봇 답변의 적합도를 평가하는 채점관입니다. '
    '질문과 답변을 보고 답변이 질문에 얼마나 적절하고 유용한지 0~100점으로 채점하세요.\n\n'
    'JSON만 응답 (다른 텍스트 없이): {"score": <0~100 정수>, "reason": "<한 줄 평가>"}'
)


def _check_guardrail(client, question):
    """질문의 적절성을 OpenAI로 판단. 실패 시 통과(True) 처리."""
    try:
        completion = client.chat.completions.create(
            model=settings.GEMINI_MODEL,
            max_tokens=200,
            extra_body={'reasoning_effort': 'none'},
            messages=[
                {'role': 'system', 'content': GUARDRAIL_SYSTEM_PROMPT},
                {'role': 'user', 'content': question},
            ],
        )
        result = json.loads(_strip_json_fence(completion.choices[0].message.content.strip()))
        return bool(result.get('is_valid', True)), result.get('reason', '')
    except Exception:
        return True, ''


@require_http_methods(['POST'])
@login_required_json
def guardrail(request):
    """POST /api/ai/guardrail/ — body: { question } → { is_valid, reason }"""
    client = _get_ai_client()
    if client is None:
        return _unavailable()

    question = _parse_json_body(request).get('question', '').strip()
    if not question:
        return JsonResponse({'error': '질문을 입력해 주세요.'}, status=400)

    is_valid, reason = _check_guardrail(client, question)
    return JsonResponse({'is_valid': is_valid, 'reason': reason})


@require_http_methods(['POST'])
@login_required_json
def chat(request):
    """
    POST /api/ai/chat/ — body: { question 또는 message, history? }
    → { is_valid, answer, reply, message } (reply/message는 answer와 동일값,
    플로팅 챗봇·저니모드 위젯이 reply/message 필드를 기대하기 때문)
    """
    client = _get_ai_client()
    if client is None:
        return _unavailable()

    data = _parse_json_body(request)
    question = (data.get('question') or data.get('message') or '').strip()
    if not question:
        return JsonResponse({'error': '질문을 입력해 주세요.'}, status=400)

    is_valid, reason = _check_guardrail(client, question)
    if not is_valid:
        blocked_msg = '부적절한 질문으로 판단되어 답변할 수 없습니다.'
        return JsonResponse({'is_valid': False, 'reason': reason, 'reply': blocked_msg, 'message': blocked_msg})

    history = data.get('history', [])
    messages = [{'role': 'system', 'content': CHAT_SYSTEM_PROMPT}]
    for turn in history[-10:]:
        role = turn.get('role')
        if role in ('user', 'assistant') and turn.get('content'):
            messages.append({'role': role, 'content': turn['content']})
    messages.append({'role': 'user', 'content': question})

    try:
        completion = client.chat.completions.create(
            model=settings.GEMINI_MODEL,
            max_tokens=500,
            extra_body={'reasoning_effort': 'none'},
            messages=messages,
        )
        answer = completion.choices[0].message.content.strip()
    except Exception:
        return JsonResponse({'error': '답변 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.'}, status=503)

    return JsonResponse({'is_valid': True, 'answer': answer, 'reply': answer, 'message': answer})


@require_http_methods(['POST'])
@login_required_json
def image_generate(request):
    """POST /api/ai/image/ — body: { prompt } → { image_url }"""
    client = _get_ai_client()
    if client is None:
        return _unavailable()

    prompt = _parse_json_body(request).get('prompt', '').strip()
    if not prompt:
        return JsonResponse({'error': '이미지 설명을 입력해 주세요.'}, status=400)

    try:
        result = client.images.generate(
            model=settings.GEMINI_IMAGE_MODEL,
            prompt=prompt,
            n=1,
            size='512x512',
        )
        return JsonResponse({'image_url': result.data[0].url})
    except Exception:
        return JsonResponse({'error': '이미지 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.'}, status=503)


@require_http_methods(['POST'])
@login_required_json
def score(request):
    """POST /api/ai/score/ — body: { question, answer } → { score, reason }"""
    client = _get_ai_client()
    if client is None:
        return _unavailable()

    data = _parse_json_body(request)
    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    if not question or not answer:
        return JsonResponse({'error': '질문과 답변이 모두 필요합니다.'}, status=400)

    try:
        completion = client.chat.completions.create(
            model=settings.GEMINI_MODEL,
            max_tokens=200,
            extra_body={'reasoning_effort': 'none'},
            messages=[
                {'role': 'system', 'content': SCORE_SYSTEM_PROMPT},
                {'role': 'user', 'content': f'질문: {question}\n답변: {answer}'},
            ],
        )
        result = json.loads(_strip_json_fence(completion.choices[0].message.content.strip()))
        return JsonResponse({'score': result.get('score'), 'reason': result.get('reason', '')})
    except Exception:
        return JsonResponse({'score': None, 'reason': ''})
