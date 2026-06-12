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
| 관련 URL 등록 | 531 (전체) |
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
- 카테고리 필터: 공원·자연, 문화 시설 버튼 제거됨
- 이미지 없는 장소 카드: `景` 문자 + "이미지 없음" 텍스트 표시

### 장소 상세 (`templates/place_detail.html`)
- **관련 URL** 행: 항상 표시, URL 있으면 `장소명 ↗` 링크, 없으면 `—`
- URL 종류별 링크:
  - 공식 홈페이지 (궁궐·박물관 등)
  - 한국민족문화대백과 (`encykorea.aks.ac.kr`)
  - 대한민국 구석구석 (`korean.visitkorea.or.kr`)
  - 나무위키 (`namu.wiki/w/장소명`) — URL 없는 장소 자동 폴백

### 데이터 관리 (`python manage.py set_websites`)
URL 등록 우선순위 (순서대로 적용, 이미 URL 있으면 스킵):

1. 공식 홈페이지 (궁궐·왕릉·박물관·기념관 등 63개 직접 조사)
2. 한국민족문화대백과 encykorea 링크 (향교 10 + 서원·사우 8 + 역사유적 7 = 25개)
3. 대한민국 구석구석 visitkorea 링크 (역사유적 52 + 박물관 1 + 사찰 20 = 73개)
4. 나머지 전체 → 나무위키 자동 설정 (`urllib.parse.quote(place.name)`)

- **박물관 시대 재분류**: `python manage.py fix_museum_eras` (조선·고려·삼국·일제 기준)
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
| `culture/management/commands/set_websites.py` | URL 일괄 등록 커맨드 |
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
python manage.py set_websites      # URL 전체 등록 (공식→encykorea→visitkorea→나무위키 순)
# Web 탭 → Reload
```

> `db.sqlite3`는 git에 없음 — PythonAnywhere에 직접 업로드하거나 서버 DB 유지.

---

## 알려진 이슈 / 미완성

- `fetch_websites` (TourAPI 홈페이지 자동 수집): TourAPI 일일 쿼터 소진 문제로 현재 미활용.
- `ai/views.py`의 chat·guardrail·score·image_generate: 현재 503 반환 (GMS 서비스 종료).
- 리뷰·별점 UI: Review 모델은 있으나 프론트 미구현.
- 북마크 UI: Bookmark 모델은 있으나 프론트 미구현.
- 커뮤니티 동선 공유: Route 공유 기능 미구현.
- 나무위키 링크: 장소명과 나무위키 문서명이 다를 경우 404 가능 (자동 설정이므로 검증 안 됨).
