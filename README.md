# 09-PJT : CultureRoute - 서울·경기 지역문화 추천 서비스

## 📌 프로젝트 개요

서울·경기 지역의 역사·문화 명소를 **카테고리별로 큐레이션**하고,  
**실시간 날씨 기반 장소 추천**, **동선 추천**, **AI 챗봇** 기능을 제공하는 문화 탐방 플랫폼입니다.

| 항목 | 내용 |
|------|------|
| 프로젝트명 | CultureRoute |
| 개발 기간 | 2025.05.15 ~ 2025.05.22 |
| 개발 환경 | Python 3.11 / Django / Django REST Framework |
| 데이터베이스 | SQLite (개발) |
| 외부 API | 한국관광공사 TourAPI / OpenWeatherMap / Kakao Maps / GMS (SSAFY AI 프록시) |

---

## 🗂️ 프로젝트 구조

```
CultureRoute/
├── config/                  # Django 프로젝트 설정
│   ├── settings.py
│   ├── urls.py
│   ├── context_processors.py  # KAKAO_JS_KEY 전역 주입
│   └── wsgi.py
├── culture/                 # 장소·리뷰·코스·북마크 앱
│   ├── management/
│   │   └── commands/
│   │       └── fetch_places.py   # 공공데이터 수집 커맨드 (규칙 기반 필터링)
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── api_clients.py       # TourAPI / 날씨 / 거리 계산
├── accounts/                # 회원가입·로그인 앱
├── ai/                      # AI 챗봇·이미지 생성 앱
│   ├── views.py
│   └── urls.py
├── templates/
│   ├── index.html
│   ├── places.html
│   ├── place_detail.html
│   ├── routes.html
│   ├── login.html
│   ├── signup.html
│   └── ai_chat.html         # AI 챗봇·이미지 생성 UI
├── historic_places.txt      # 역사 장소 목록 (573건, 참고용)
├── .env                     # 환경변수 (API 키 관리)
├── manage.py
└── requirements.txt
```

---

## ✅ 구현한 기능적 요구사항

### Django Model

| 모델 | 설명 |
|------|------|
| `Theme` | 시대 테마 (삼국/고려/조선/일제강점기/현대) |
| `Place` | 문화 장소 (장소명, 카테고리, 위경도, 실내외 여부 등) |
| `Review` | 유저 리뷰 (별점 1~5, 내용) |
| `Route` + `RoutePlace` | 동선 코스 (장소 순서 포함 M2M 중간 테이블) |
| `Bookmark` | 장소·코스 북마크 |

### Serializer

| Serializer | 설명 |
|------------|------|
| `PlaceListSerializer` | 목록용 간략 정보 + 평균 별점 |
| `PlaceDetailSerializer` | 상세 정보 + 최신 리뷰 5개 포함 |
| `ReviewSerializer` | 별점·내용 유효성 검증 포함 |
| `RouteCreateSerializer` | place_ids 리스트로 코스 생성, RoutePlace 자동 저장 |
| `BookmarkSerializer` | 장소/코스 중 하나만 지정 검증 포함 |

### API View

| 메서드 | URL | 설명 |
|--------|-----|------|
| GET | `/api/places/` | 전체 장소 목록 |
| GET | `/api/places/<id>/` | 장소 상세 |
| GET | `/api/places/filter/` | 시대·카테고리·지역·실내외 필터 |
| GET | `/api/places/weather/` | 날씨 기반 실내외 장소 필터 |
| GET | `/api/places/weather-current/` | OpenWeatherMap 실시간 날씨 조회 |
| GET/POST | `/api/places/<id>/reviews/` | 리뷰 목록·작성 |
| GET/PUT/DELETE | `/api/places/<id>/reviews/<id>/` | 리뷰 상세·수정·삭제 |
| GET/POST | `/api/routes/` | 코스 목록·생성 |
| POST | `/api/routes/<id>/like/` | 코스 좋아요 |
| GET/POST | `/api/bookmarks/` | 북마크 목록·추가 |
| DELETE | `/api/bookmarks/<id>/` | 북마크 삭제 |
| POST | `/api/ai/chat/` | AI 챗봇 (로그인 필요) |
| POST | `/api/ai/image/` | AI 이미지 생성 (로그인 필요) |

---

## 🔗 외부 API 연동

### ① 한국관광공사 TourAPI (KorService2)

- **엔드포인트** : `https://apis.data.go.kr/B551011/KorService2/areaBasedList2`
- **수집 범위** : 서울(areaCode=1) + 경기(areaCode=31)
- **필터링 전략** : GMS LLM 없이 TourAPI 카테고리 코드로 역사 장소만 선별

| contentTypeId | cat2 / cat3 | 분류 |
|---|---|---|
| 12 (관광지) | A0201 | 역사관광지 |
| 12 (관광지) | A0205 | 건축/조형물 |
| 14 (문화시설) | A02060100 | 박물관 |
| 14 (문화시설) | A02060200 | 기념관 |

- **제외 키워드** : 전망대, 타워, 대교, 아치교, 댐, 롯데월드, 국회의사당 등 현대 시설
- **management command** : `python manage.py fetch_places --flush`
- **수집 결과** : 서울 230건 + 경기 344건 = **총 574건** DB 저장 완료

```
저장 분류:
  historic (역사관광지·건축/조형물) : 424건
  palace   (고궁·사찰)              :  16건
  museum   (박물관·기념관)          : 134건
```

### ② OpenWeatherMap API

- **엔드포인트** : `https://api.openweathermap.org/data/2.5/weather`
- **활용 방식** : 날씨 ID 기준으로 실내/외 장소 자동 판단
  - `weather_id < 800` → 비·눈 → 실내 장소 추천
  - `temp >= 10` → 동적 장소 추천

### ③ Kakao Maps API

- **JavaScript 키** : 장소 목록·상세 페이지 지도 렌더링
- **거리 계산** : 하버사인 공식으로 두 좌표 간 직선거리·도보 소요시간 계산

### ④ GMS (SSAFY AI 프록시)

- **엔드포인트** : `https://gms.ssafy.io/gmsapi/api.openai.com/v1`
- **모델** : `gpt-5-nano` (채팅), `gpt-image-1` (이미지 생성)
- **AI 챗봇** : 가드레일 + 답변을 단일 API 호출로 처리 (`[BLOCKED]` 마커 방식)
- **이미지 생성** : `b64_json` 포맷 반환 → `data:image/png;base64,...` 변환 후 표시

---

## 💡 학습한 내용

### 1. TourAPI 카테고리 코드 구조 분석

`contentTypeId=14` (문화시설) 항목의 cat2는 모두 `A0206`이며,  
실제 세부 분류는 cat3 코드로 구분됩니다.  
기존에 알려진 `B02xx` 코드는 이 API에서 사용되지 않습니다.

```
A02060100 = 박물관
A02060200 = 기념관
A02060300 = 전시관
A02060500 = 미술관/갤러리
A02060900 = 도서관
...
```

### 2. Django Management Command 활용

커스텀 커맨드에 `--flush`, `--dry-run` 인자를 추가해  
안전하게 DB를 초기화하거나 실제 저장 없이 결과를 미리 확인하는 패턴을 구현했습니다.

### 3. GMS API 제약 사항

`gpt-5-nano` 모델은 `response_format`, `max_tokens` 파라미터를 지원하지 않아  
이를 포함하면 400 오류가 발생합니다.  
가드레일과 답변을 별도 호출로 분리하는 대신, 단일 시스템 프롬프트에서  
`[BLOCKED]` 마커로 유해 질문을 처리해 API 호출 횟수를 절반으로 줄였습니다.

### 4. 인증 처리 패턴

- `@ensure_csrf_cookie` 데코레이터로 `/api/accounts/me/` 호출 시 CSRF 쿠키 자동 발급
- 로그인 필요 API에서 HTML 리다이렉트 대신 JSON 401을 반환하는 커스텀 데코레이터 구현

```python
def login_required_json(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper
```

### 5. gpt-image-1 응답 포맷

`dall-e-3`과 달리 `gpt-image-1`은 `url` 대신 `b64_json`을 반환합니다.  
두 포맷 모두 처리하는 코드가 필요합니다.

```python
item = resp.json()['data'][0]
if 'url' in item:
    image_url = item['url']
else:
    image_url = f"data:image/png;base64,{item['b64_json']}"
```

---

## 🔥 어려웠던 부분

### 1. GMS API 400 오류 원인 파악

가드레일 호출 시 `response_format: {"type": "json_object"}`와 `max_tokens` 파라미터가  
`gpt-5-nano`에서 지원되지 않아 400 오류가 발생했습니다.  
오류 메시지에 응답 본문이 포함되지 않아 원인 파악이 어려웠고,  
파라미터를 하나씩 제거하며 원인을 찾았습니다.

### 2. TourAPI 카테고리 코드 불일치

`B0207` (기념관), `B0209` (박물관) 코드가 실제 API 응답에서는 사용되지 않아  
문화시설 데이터가 전혀 저장되지 않는 문제가 있었습니다.  
직접 API 응답을 출력해 실제 cat3 코드(`A02060100`, `A02060200`)를 확인해 해결했습니다.

### 3. 이미지 생성 탭 미표시

CSS에서 `.image-panel { display: none; }`으로 선언된 상태에서  
JavaScript로 `element.style.display = ''`로 설정하면 CSS가 우선 적용되어 탭이 보이지 않았습니다.  
`display = 'block'`으로 명시적으로 지정해 해결했습니다.

### 4. 로그인 상태 확인 로직 오류

`/api/accounts/me/` 응답에 `is_authenticated` 필드가 없어  
`data.is_authenticated`가 항상 `undefined`로 평가됐습니다.  
HTTP 상태 코드(`res.ok`)로 로그인 여부를 판단하는 방식으로 수정했습니다.

---

## 🌱 새로 배운 것

- TourAPI `contentTypeId=14` 항목은 cat2가 모두 `A0206`이며, 세부 분류는 cat3로 구분됨
- GMS의 `gpt-5-nano`는 `response_format`, `max_tokens` 미지원 → 파라미터 제거 필요
- `gpt-image-1`은 `b64_json` 포맷으로 이미지를 반환 (`url` 아님)
- Django에서 API 뷰에 `@login_required` 대신 JSON 응답 반환 커스텀 데코레이터 적용 방법
- CSS `display: none`과 JavaScript `style.display = ''`의 우선순위 충돌 해결 방법
- 가드레일과 LLM 응답을 단일 API 호출로 처리해 응답 속도를 개선하는 방법

---

## 📸 실행 결과

### fetch_places 실행 결과

```
[API] 서울 관광지 (contentTypeId=12) 수집 중...
  → 474건 수신
[API] 서울 문화시설 (contentTypeId=14) 수집 중...
  → 281건 수신
[API] 경기 관광지 (contentTypeId=12) 수집 중...
  → 1002건 수신
[API] 경기 문화시설 (contentTypeId=14) 수집 중...
  → 246건 수신

[DONE] 저장: 574건  |  중복: 0건  |  제외: 1429건
```

### DB 저장 현황

```
전체  : 574건
서울  : 230건
경기  : 344건

카테고리별:
  historic (역사관광지·건축/조형물) : 424건
  palace   (고궁·사찰)              :  16건
  museum   (박물관·기념관)          : 134건
```

### AI 챗봇

- 로그인하지 않은 사용자 접근 시 `/login/?next=/ai/`로 리다이렉트
- 유해 질문 감지 시 `[BLOCKED]` 반환, 정상 질문은 친절하게 답변
- 이미지 생성 탭: 프롬프트 입력 → `gpt-image-1` 모델로 이미지 생성 후 표시

---

## 💭 느낀 점

공식 문서와 실제 API 응답이 다를 수 있다는 것을 다시 한번 체감했습니다.  
`B02xx` 카테고리 코드는 문서에 나와 있었지만 실제 API는 `A0206` + cat3 조합을 사용했고,  
직접 응답 데이터를 출력해서 확인해야만 해결할 수 있었습니다.

LLM 기반 필터링(GMS 호출)은 정확도가 높지만 API 호출 비용과 속도 문제가 있습니다.  
TourAPI가 이미 `A0201 (역사관광지)`으로 분류한 데이터를 신뢰하고,  
현대 시설 키워드만 추가로 제외하는 방식이 실용적인 대안이 될 수 있다는 것을 배웠습니다.

AI 기능 구현 시 외부 API의 제약사항(지원 파라미터, 응답 포맷 등)을 사전에 확인하는 것이  
디버깅 시간을 크게 줄일 수 있다는 점도 느꼈습니다.
