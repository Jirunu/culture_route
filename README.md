# 09-PJT : CultureRoute - 서울·경기 지역문화 추천 서비스

## 📌 프로젝트 개요

서울·경기 지역의 역사·문화 명소를 **설문 기반 취향 분석**으로 큐레이션하고,  
**실시간 날씨 연동**, **GMS AI 장소 추천**, **카카오맵 동선 시각화** 기능을 제공하는 문화 탐방 플랫폼입니다.

| 항목 | 내용 |
|------|------|
| 프로젝트명 | CultureRoute |
| 개발 기간 | 2025.05.15 ~ 2025.05.29 |
| 개발 환경 | Python 3.11 / Django 5.2 / Django REST Framework |
| 데이터베이스 | SQLite (개발) |
| 외부 API | 한국관광공사 TourAPI / OpenWeatherMap / Kakao Maps JS / GMS (SSAFY AI 프록시) |

---

## 🗂️ 프로젝트 구조

```
CultureRoute/
├── config/                  # Django 프로젝트 설정
│   ├── settings.py          # STATICFILES_DIRS, GMS_* 환경변수 포함
│   ├── urls.py
│   ├── context_processors.py  # KAKAO_JS_KEY 전역 주입
│   └── wsgi.py
├── culture/                 # 장소·리뷰·코스·북마크·AI추천 앱
│   ├── management/
│   │   └── commands/
│   │       └── fetch_places.py   # TourAPI 수집 커맨드 (firstimage URL 포함)
│   ├── migrations/
│   ├── static/
│   │   └── culture/
│   │       └── images/
│   │           └── no_map_image.png  # 이미지 없는 장소의 기본 이미지
│   ├── models.py
│   ├── serializers.py
│   ├── views.py             # ai_recommend 뷰 포함
│   ├── urls.py
│   └── api_clients.py       # TourAPI / 날씨 / 거리 계산
├── accounts/                # 회원가입·로그인 앱
├── ai/                      # AI 챗봇·이미지 생성 앱
│   ├── views.py
│   └── urls.py
├── templates/
│   ├── landing.html         # 메인 랜딩
│   ├── survey.html          # 6단계 온보딩 설문 (취향 수집)
│   ├── loading.html         # 설문 완료 후 AI 분석 대기 화면
│   ├── app.html             # 추천 메인 (설문+날씨 필터, AI 동선, 카카오맵)
│   ├── places.html          # 장소 목록 (필터 + 그리드/지도 + 페이지네이션)
│   ├── place_detail.html    # 장소 상세 + 리뷰
│   ├── routes.html          # 커뮤니티 코스 (생성·수정·삭제·좋아요·댓글)
│   ├── login.html
│   ├── signup.html
│   └── ai_chat.html         # AI 챗봇·이미지 생성 UI
├── no_map_image.png         # 원본 기본 이미지 (static 복사본 참고용)
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
| `Place` | 문화 장소 (장소명, 카테고리, 위경도, 실내외·동적 여부, image_url) |
| `Review` | 유저 리뷰 (별점 1~5, 내용) |
| `Route` + `RoutePlace` | 동선 코스 (장소 순서 포함 M2M 중간 테이블) |
| `RouteLike` | 코스 좋아요 (중복 방지, 토글) |
| `RouteComment` | 코스 댓글 |
| `Bookmark` | 장소·코스 북마크 (둘 중 하나만 지정 가능) |

### Serializer

| Serializer | 설명 |
|------------|------|
| `PlaceListSerializer` | 목록용 간략 정보 + `image_url` + 평균 별점 |
| `PlaceDetailSerializer` | 상세 정보 + 최신 리뷰 5개 포함 |
| `ReviewSerializer` | 별점·내용 유효성 검증 포함 |
| `RouteCreateSerializer` | `place_ids` 리스트로 코스 생성, `RoutePlace` 자동 저장 |
| `RouteCommentSerializer` | 댓글 작성자 정보 포함 |
| `BookmarkSerializer` | 장소/코스 중 하나만 지정 검증 포함 |

### API View

| 메서드 | URL | 설명 |
|--------|-----|------|
| GET | `/api/places/` | 전체 장소 목록 |
| GET | `/api/places/<id>/` | 장소 상세 |
| GET | `/api/places/filter/` | 시대·카테고리·지역·실내외·동적 여부 필터 **(다중값 지원)** |
| GET | `/api/places/weather/` | 날씨 파라미터 기반 실내외 장소 필터 |
| GET | `/api/places/weather-current/` | OpenWeatherMap 실시간 날씨 + 실내/외 추천 |
| **POST** | **`/api/places/ai-recommend/`** | **세션 설문 기반 GMS AI 장소 5개 추천 (신규)** |
| GET/POST | `/api/places/<id>/reviews/` | 리뷰 목록·작성 |
| GET/PUT/DELETE | `/api/places/<id>/reviews/<id>/` | 리뷰 상세·수정·삭제 |
| GET/POST | `/api/routes/` | 코스 목록·생성 |
| GET/PUT/**DELETE** | `/api/routes/<id>/` | 코스 상세·수정·**삭제 (본인만)** |
| POST | `/api/routes/<id>/like/` | 코스 좋아요 토글 |
| GET/POST | `/api/routes/<id>/comments/` | 코스 댓글 목록·작성 |
| DELETE | `/api/routes/<id>/comments/<id>/` | 코스 댓글 삭제 (본인만) |
| GET/POST | `/api/bookmarks/` | 북마크 목록·추가 |
| DELETE | `/api/bookmarks/<id>/` | 북마크 삭제 |
| POST | `/api/survey/save/` | 설문 응답 세션 저장 |
| POST | `/api/survey/reset/` | 설문 세션 초기화 |
| POST | `/api/ai/chat/` | AI 챗봇 (로그인 필요) |
| POST | `/api/ai/image/` | AI 이미지 생성 (로그인 필요) |

---

## 🔗 외부 API 연동

### ① 한국관광공사 TourAPI (KorService2)

- **엔드포인트** : `https://apis.data.go.kr/B551011/KorService2/areaBasedList2`
- **수집 범위** : 서울(areaCode=1) + 경기(areaCode=31)
- **저장 필드** : 장소명, 주소, 위·경도, `firstimage` → `image_url` 저장

| contentTypeId | cat2 / cat3 | 분류 |
|---|---|---|
| 12 (관광지) | A0201 | 역사관광지 |
| 12 (관광지) | A0205 | 건축/조형물 |
| 14 (문화시설) | A02060100 | 박물관 |
| 14 (문화시설) | A02060200 | 기념관 |

- **제외 키워드** : 전망대, 타워, 대교, 아치교, 댐, 롯데월드, 국회의사당 등 현대 시설
- **management command** : `python manage.py fetch_places --flush`
- **수집 결과** : 서울 230건 + 경기 344건 = **총 574건** DB 저장

```
카테고리별:
  historic (역사관광지·건축/조형물) : 424건
  palace   (고궁·사찰)              :  16건
  museum   (박물관·기념관)          : 134건
```

### ② OpenWeatherMap API

- **엔드포인트** : `https://api.openweathermap.org/data/2.5/weather`
- **활용 방식** : 날씨 ID(`weather_id`) 기준으로 실내/외 자동 판단
  - `weather_id == 800` → 맑음 → 실외 추천
  - `801 ~ 802` → 구름 조금 → 실외 가능
  - 나머지 (비·눈·천둥 등) → 실내 추천
- **설문 연동** : `place_type === 'weather'` 선택 시 날씨 응답 후 `is_indoor` 자동 반영

### ③ Kakao Maps API

- **스크립트 로드** : `autoload=false` + `kakao.maps.load()` 콜백으로 지연 초기화
- **places.html** : 그리드/지도 뷰 토글. 전체 장소 마커 표시, 마커 클릭 시 상세 링크
- **app.html** : 동선 탭 클릭 시 AI 추천 결과를 마커로 표시
  - `kakao.maps.LatLngBounds()` 로 마커 전체 범위 자동 조정
  - 인포윈도우에 장소명 / 주소 / AI 추천 이유 표시

### ④ GMS (SSAFY AI 프록시)

- **엔드포인트** : `https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions`
- **모델** : `gpt-5-nano` (추론 모델)
- **AI 장소 추천 흐름** :
  1. 세션의 설문 데이터(region, interests, eras, place_type, activity 등) 읽기
  2. DB에서 조건에 맞는 후보 장소 최대 20개 조회
  3. 후보 목록 + 사용자 선호를 프롬프트로 구성해 GMS에 전달
  4. LLM 응답(JSON 배열)에서 장소 id와 추천 이유 파싱
  5. 실패 시 후보 앞 5개를 폴백으로 반환
- **AI 챗봇** : 가드레일 + 답변을 단일 API 호출로 처리 (`[BLOCKED]` 마커 방식)
- **이미지 생성** : `gpt-image-1` 모델, `b64_json` 포맷 반환

---

## 💡 학습한 내용

### 1. 설문 → 필터 → 추천 전체 흐름 설계

6단계 설문(지역/관심분야/시대/장소유형/소요시간/활동유형)을 Django 세션에 저장하고,  
`/app/` 페이지에서 `SURVEY` 객체로 주입해 초기 필터와 AI 추천에 모두 활용했습니다.

```
survey.html → POST /api/survey/save/ → session 저장
→ /loading/ → /app/  (app_view에서 session 읽어 context 주입)
→ JS: initFiltersFromSurvey() + loadWeather() + loadPlaces()
```

### 2. Django `getlist()`로 다중 필터 처리

단일 파라미터(`?era=joseon`)만 받던 뷰를 `getlist()`로 개선해  
`?era=joseon&era=modern` 같은 다중 선택을 `__in` 쿼리로 처리했습니다.

```python
era_list = request.query_params.getlist('era')
if era_list:
    places = places.filter(theme__era__in=era_list)
```

프론트에서는 `URLSearchParams.append()`로 같은 키를 반복 추가해 전달합니다.

### 3. gpt-5-nano 추론 모델 파라미터 제약

`gpt-5-nano`는 `o`-시리즈 계열 추론 모델로 `max_tokens`, `temperature` 파라미터를 지원하지 않습니다.  
`max_completion_tokens`로 교체해야 하며, 내부 추론 토큰을 포함해 4000 이상을 할당해야  
충분한 출력을 얻을 수 있습니다. API 타임아웃도 30초로 늘렸습니다.

```python
json={
    'model': gms_model,
    'messages': [...],
    'max_completion_tokens': 4000,  # max_tokens 사용 시 400 오류
},
timeout=30,  # 추론 모델은 응답까지 시간이 더 걸림
```

### 4. Kakao Maps `autoload=false` 패턴

지도 탭이 숨겨진 상태에서 SDK를 로드하면 컨테이너 크기를 0으로 인식합니다.  
`autoload=false`로 SDK만 먼저 로드하고, 탭 전환 시 `kakao.maps.load()` 콜백 안에서  
`new kakao.maps.Map()`을 호출해 정확한 크기로 초기화했습니다.

```javascript
function switchTab(tab) {
  if (tab === 'route') {
    rv.style.display = 'block';
    initKakaoMap();  // 여기서 kakao.maps.load() 트리거
  }
}
```

### 5. 정적 파일(Static Files) 설정

앱 내부 `static/` 디렉토리를 `STATICFILES_DIRS`에 등록하고,  
이미지 로드 실패 시 `onerror` 핸들러로 기본 이미지를 표시하는 패턴을 적용했습니다.

```python
# settings.py
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'culture' / 'static']
```

```javascript
const imgSrc = p.image_url || '/static/culture/images/no_map_image.png';
// <img onerror="this.src='/static/culture/images/no_map_image.png'">
```

### 6. 프론트엔드 페이지네이션 패턴

API 응답 전체를 `allPlaces` 배열에 보관하고, 클라이언트 사이드에서 15개씩 슬라이싱합니다.  
지도 뷰는 페이지와 무관하게 전체 마커를 표시합니다.

```javascript
function goPage(page) {
  const pageData = allPlaces.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  grid.innerHTML = pageData.map(placeCardHTML).join('');
  renderPagination(Math.ceil(allPlaces.length / PAGE_SIZE), page);
}
```

---

## 🔥 어려웠던 부분

### 1. gpt-5-nano 400 오류 원인 특정

`max_tokens` 파라미터가 해당 모델에서 지원되지 않아 400이 반환됐는데,  
AI 추천 뷰에서 예외를 `except Exception: pass`로 처리하고 있어  
에러 로그 없이 폴백 결과만 조용히 반환되었습니다.  
GMS API를 별도 스크립트로 직접 호출해보며 오류 메시지를 확인한 뒤 원인을 파악했습니다.

### 2. 날씨맞춤 선택 시 이중 로드 문제

설문에서 `place_type === 'weather'`를 선택하면  
`loadPlaces()`가 먼저 실행(날씨 미반영)되고 이후 `loadWeather()`가 다시 `loadPlaces()`를 호출해  
화면이 두 번 깜빡이는 문제가 있었습니다.  
초기화 순서를 조건 분기로 해결했습니다.

```javascript
if (SURVEY.place_type === 'weather') {
  loadWeather();          // 내부에서 is_indoor 반영 후 loadPlaces() 호출
} else {
  loadPlaces();
  loadWeather();          // 날씨 정보는 표시만 하고 장소 재조회 없음
}
```

### 3. era 필터 결과 0건 문제

DB의 574개 장소 모두 `theme=None` 상태(TourAPI 수집 시 시대 테마가 미지정)라  
`theme__era__in` 필터 적용 시 항상 0건이 반환됐습니다.  
era 파라미터 포함 결과가 0건이면 era를 제거하고 재요청하는 클라이언트 폴백을 구현했습니다.

```javascript
if (data.length === 0 && params.getAll('era').length > 0) {
  const fallback = new URLSearchParams(params);
  fallback.delete('era');
  data = await fetch('/api/places/filter/?' + fallback).then(r => r.json());
}
```

### 4. 커뮤니티 코스 삭제 버튼 이벤트 버블링

삭제 버튼이 코스 카드 내부에 있어, 버튼 클릭 이벤트가 카드 클릭(페이지 이동)으로 버블링됐습니다.  
`event.stopPropagation()`으로 해결했습니다.

---

## 🌱 새로 배운 것

- `gpt-5-nano`는 추론 모델이라 `max_tokens` 대신 `max_completion_tokens` 사용, 타임아웃 30초 필요
- Django `request.query_params.getlist(key)`로 동일 키의 다중 값을 리스트로 받을 수 있음
- `URLSearchParams.append()` vs `.set()` — 다중값 전송은 `append()` 반복 사용
- Kakao Maps SDK `autoload=false` + `kakao.maps.load()` 콜백으로 지연 초기화
- `kakao.maps.LatLngBounds()`와 `map.setBounds()`로 마커 전체 범위 자동 맞춤
- CSS `object-fit: cover`로 이미지 비율 깨짐 없이 카드 썸네일 처리
- `<img onerror="...">` 핸들러로 이미지 로드 실패 시 기본 이미지로 즉시 대체

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

### 설문 → AI 추천 흐름

```
1. /survey/  → 6단계 취향 설문 완료
2. POST /api/survey/save/  → {"status": "ok", "redirect": "/loading/"}
3. /loading/  → 3.2초 대기 후 /app/ 이동
4. /app/  → 설문 데이터 기반 필터 자동 적용, 날씨 is_indoor 반영
5. [동선 탭]  → POST /api/places/ai-recommend/
             → GMS gpt-5-nano가 후보 20개 중 5개 선별 + 추천 이유 반환
             → 카카오맵에 마커 표시, 인포윈도우에 추천 이유 노출
```

### 장소 목록 페이지네이션

```
서울 전체 장소 조회 시: 230건 → 16페이지 (15개/페이지)
경기 전체 장소 조회 시: 344건 → 23페이지
필터 적용 후 15건 이하: 페이지네이션 버튼 미표시
```

### 커뮤니티 코스

```
- 본인 코스 카드에만 [수정] [삭제] 버튼 표시
- 삭제: confirm() → DELETE /api/routes/<id>/ → 204 → 카드 DOM 즉시 제거
- 좋아요: 토글 방식, RouteLike 모델로 중복 방지
- 댓글: 실시간 등록/삭제 (본인 댓글만 삭제 버튼 노출)
```

---

## 💭 느낀 점

설문 → 날씨 → AI 추천까지 여러 API와 세션을 연결하는 흐름을 설계하면서,  
각 단계의 실행 순서와 비동기 처리가 얼마나 중요한지 체감했습니다.  
특히 `loadWeather()`와 `loadPlaces()`의 호출 순서 하나로 화면 깜빡임이 생기거나 사라지는 경험은  
프론트엔드에서 비동기 흐름 제어가 기능만큼 중요하다는 것을 가르쳐 줬습니다.

GMS `gpt-5-nano`가 추론 모델이라는 것을 API 응답을 직접 뜯어보고 나서야 알았습니다.  
문서만 믿지 않고 실제 요청-응답을 확인하는 습관이 디버깅 시간을 크게 줄여준다는 것을  
이번 프로젝트에서 다시 한번 확인했습니다.

클라이언트 사이드 페이지네이션은 API 호출 횟수를 줄이면서도 빠른 페이지 전환을 제공하는  
실용적인 선택이었습니다. 다만 데이터가 수천 건으로 늘어나면 서버 사이드 페이지네이션이  
필요하다는 점도 함께 인식할 수 있었습니다.
