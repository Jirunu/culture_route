# CultureRoute — CLAUDE.md

서울·경기 문화명소 추천 Django 웹앱. 설문 기반 AI 추천 + 카카오맵 동선 + 장소 목록/상세 페이지.

---

## 기술 스택

- **Backend**: Django 5.2 + Django REST Framework, SQLite
- **Frontend**: 순수 HTML/CSS/JS (프레임워크 없음)
- **지도**: Kakao Maps JS API (`autoload=false` → `kakao.maps.load(callback)` 패턴)
- **배포**: PythonAnywhere (`/home/cultureroute/culture_route/`)
- **GitHub**: https://github.com/Jirunu/culture_route.git (private)

---

## 환경 변수 (.env — 절대 커밋 금지)

```
PUBLIC_DATA_API_KEY=...   # 한국관광공사 TourAPI (일일 쿼터 있음)
OPENWEATHER_API_KEY=...
KAKAO_JS_KEY=...
KAKAO_REST_KEY=...
```

> GMS_API_KEY / GMS_BASE_URL / GMS_MODEL 은 **완전 제거됨** (2025-06-10). settings.py·views.py·ai/views.py 모두 정리 완료.

---

## DB 현황 (로컬 기준)

| 항목 | 수 |
|------|-----|
| Place 전체 | 531 |
| 홈페이지 URL 등록 | 63 |
| 역사유적 | 280 |
| 박물관·미술관 | 102 |
| 궁궐·사찰 | 149 |
| 서울 | 212 |
| 경기 | 319 |
| Theme | 5 (삼국·고려·조선·일제·현대) |

---

## 완료된 주요 기능

### 설문 & 추천
- **설문 수정 모달**: 프로필 카드 "✎ 수정" 버튼 → 6단계 설문 한 화면에 표시 → 저장 후 즉시 반영
- **AI 추천 (규칙 기반)**: GMS 제거 후 `_rank_candidates()` 함수로 교체 (`culture/views.py:514`)
  - 시대·카테고리·동행·목적·실내외·입장료 기준 점수 산정 → 상위 5개 반환
- **동선 재추천**: 사이드바 버튼 클릭 시 `recPlaces=[]` 리셋 → 항상 새 추천 호출

### 지도·동선
- **km 반경 슬라이더**: 5~30km, 기본 10km (`templates/app.html`)
- **카카오맵 Polyline**: 추천 장소 간 경로 시각화, 번호 마커(CustomOverlay)
- **거리 표시**: Haversine 공식으로 구간 거리·도보 시간 계산 (JS + Python 양쪽)

### 장소 목록 (`templates/places.html`)
- 검색창 (이름 검색, Enter/버튼/✕)
- 페이지네이션: 5개 번호 + «‹›» 버튼

### 장소 상세 (`templates/place_detail.html`)
- 홈페이지 링크 표시 (`Place.website` 필드, 없으면 `—`)

### 데이터 관리
- **박물관 시대 재분류**: `python manage.py fix_museum_eras` (조선·고려·삼국·일제 기준)
- **홈페이지 URL**: `python manage.py set_websites` (63개 직접 조사 등록)
- **TourAPI 홈페이지 수집**: `python manage.py fetch_websites` (쿼터 제한 있음, 현재 미활용)

---

## 핵심 파일 위치

| 파일 | 역할 |
|------|------|
| `templates/app.html` | 메인 SPA (설문·지도·동선·추천) |
| `templates/places.html` | 장소 목록·필터·검색·페이지네이션 |
| `templates/place_detail.html` | 장소 상세 (JS fetch 렌더링) |
| `templates/survey.html` | 초기 설문 페이지 |
| `culture/views.py` | 모든 API 뷰 + `_rank_candidates()` |
| `culture/models.py` | Place·Theme·Review·Route·Bookmark |
| `culture/serializers.py` | DRF 시리얼라이저 |
| `ai/views.py` | chat·guardrail 등 (현재 503 반환, GMS 제거됨) |
| `config/settings.py` | Django 설정, .env 로드 |

---

## 세션 상태 (session 키)

```python
request.session['survey_data']  # 설문 dict
request.session['survey_done']  # bool
```

설문 데이터 형식:
```json
{
  "region": "seoul_center",
  "interests": ["joseon", "royal"],
  "duration_type": "half",
  "companions": "couple",
  "purpose": "culture"
}
```

---

## 주요 API 엔드포인트

| URL | 메서드 | 설명 |
|-----|--------|------|
| `/api/places/` | GET | 장소 목록 (`?q=검색어&era=&category=&region=`) |
| `/api/places/<pk>/` | GET | 장소 상세 |
| `/api/places/filter/` | GET | 필터링 |
| `/api/places/ai-recommend/` | POST | 추천 (`{radius: km}`) |
| `/api/survey/save/` | POST | 설문 저장 |
| `/api/survey/reset/` | POST | 설문 초기화 |

---

## PythonAnywhere 배포 절차

```bash
cd /home/cultureroute/culture_route
git pull
python manage.py migrate
python manage.py fix_museum_eras   # 박물관 시대 재분류 (최초 1회)
python manage.py set_websites      # 홈페이지 URL 63개 등록 (최초 1회)
# Web 탭 → Reload
```

> `db.sqlite3`는 git에 없음 — PythonAnywhere에 직접 업로드하거나 서버 DB 유지.

---

## 알려진 이슈 / 미완성

- `fetch_websites` (TourAPI 홈페이지 자동 수집): TourAPI 일일 쿼터 소진 문제로 현재 미활용. 쿼터 리셋 후 `python manage.py fetch_websites` 시도 가능하나 대부분 NONE 반환 가능성 있음.
- `ai/views.py`의 chat·guardrail·score·image_generate: 현재 503 반환 (GMS 서비스 종료).
- 리뷰·별점 UI: Review 모델은 있으나 프론트 미구현.
- 북마크 UI: Bookmark 모델은 있으나 프론트 미구현.
- 커뮤니티 동선 공유: Route 공유 기능 미구현.
