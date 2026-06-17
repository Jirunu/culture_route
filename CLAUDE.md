# CultureRoute — CLAUDE.md

서울·경기 문화명소 추천 Django 웹앱. 설문 기반 AI 추천 + 카카오맵 동선 + 장소 목록/상세/커뮤니티.

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
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=cultureroute.pythonanywhere.com

PUBLIC_DATA_API_KEY=...   # 한국관광공사 TourAPI (일일 쿼터 있음)
OPENWEATHER_API_KEY=...
KAKAO_JS_KEY=...
KAKAO_REST_KEY=...
ANTHROPIC_API_KEY=...     # Claude API (미입력 시 ai/ 503 반환)
```

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

## 구현된 전체 기능

### 설문 & 추천 (`templates/app.html`)
- **설문 수정 모달**: 프로필 카드 "✎ 수정" 버튼 → 6단계 설문 한 화면에 표시 → 저장 후 즉시 반영
- **AI 추천 (규칙 기반)**: `_rank_candidates()` (`culture/views.py`) — 시대·카테고리·동행·목적·실내외·입장료 점수 → 상위 5개
- **동선 재추천**: 사이드바 버튼 클릭 시 `recPlaces=[]` 리셋 → 항상 새 추천 호출

### 지도·동선 (`templates/app.html`)
- **km 반경 슬라이더**: 5~30km, 기본 10km
- **최단 동선 최적화**: `_shortest_route()` — N≤8 완전탐색(itertools.permutations), N>8 nearest-neighbor
- **카카오맵 Polyline**: 최적 순서로 번호 마커(CustomOverlay) + 경로선 시각화
- **구간 거리·도보 시간**: Haversine 공식 (JS + Python)
- **동선 저장 모달**: "↓ 이 동선 저장하기" 버튼 → 제목 입력 + 공유 여부 체크 → `/api/routes/` POST

### 장소 목록 (`templates/places.html`)
- 이름 검색 (Enter·버튼·✕), 페이지네이션 (5개 번호 + «‹›»)
- 카드 북마크 버튼 (☆/★) — 로그인 시 내 북마크 상태 자동 로드
- 카드 클릭 시 지도 마커 하이라이트, 마커 클릭 시 카드 스크롤 + 테두리 강조

### 장소 상세 (`templates/place_detail.html`)
- **관련 URL**: URL 있으면 `장소명 ↗` 링크, 없으면 `—`
- **북마크 버튼**: 상세 페이지 헤더에서 토글 (로그인 필요)
- **리뷰**: 별점 선택·내용·이미지URL 입력 → 등록, 본인 리뷰 삭제 버튼 표시
- **리뷰 더 보기**: 초기 preview 개수 초과 시 "리뷰 더 보기 (N개 더)" 버튼
- **비슷한 장소**: 같은 카테고리 OR 시대 기반 4개 카드 (페이지 하단)
- **설명 더보기/접기**: 120자 이상 소개 축약·펼치기
- **소형 카카오맵**: 장소 위치 마커 + 말풍선

### 커뮤니티 코스 (`templates/routes.html`)
- 코스 목록 (2열 그리드), 좋아요·댓글
- **코스 만들기 모달**: 제목·모드·장소 선택(체크박스 + 검색필터)·거리·시간·공유여부
- **수정·삭제**: 본인 코스에만 버튼 표시
- **지도 보기 모달**: 코스 장소들을 번호 마커 + Polyline으로 Kakao맵에 시각화

### 로딩 (`templates/loading.html`)
- 3.2초 후 `/app/` 자동 이동
- **바로 시작 →** 스킵 버튼으로 즉시 이동 가능

### 데이터 관리 (`python manage.py set_websites`)
URL 등록 우선순위 (이미 URL 있으면 스킵):
1. 공식 홈페이지 (63개 직접 조사)
2. 한국민족문화대백과 encykorea (25개)
3. 대한민국 구석구석 visitkorea (73개)
4. 나머지 → 나무위키 자동 (`urllib.parse.quote(name)`)

---

## 핵심 파일 위치

| 파일 | 역할 |
|------|------|
| `templates/app.html` | 메인 SPA (설문·지도·동선·추천·동선저장) |
| `templates/places.html` | 장소 목록·검색·북마크·지도 연동 |
| `templates/place_detail.html` | 장소 상세·리뷰·북마크·비슷한장소 |
| `templates/routes.html` | 커뮤니티 코스·지도모달·댓글 |
| `templates/loading.html` | 로딩 화면 + 스킵 버튼 |
| `templates/survey.html` | 초기 설문 페이지 |
| `templates/profile.html` | 유저 프로필 (내 코스·북마크·리뷰) |
| `culture/views.py` | 모든 API 뷰, `_rank_candidates()`, `_shortest_route()`, `_haversine_km()` |
| `culture/models.py` | Place·Theme·Review·Route·RoutePlace·RouteComment·RouteComment·Bookmark |
| `culture/serializers.py` | DRF 시리얼라이저 (RouteListSerializer·RouteCreateSerializer 포함) |
| `culture/urls.py` | API URL 라우팅 |
| `culture/management/commands/set_websites.py` | URL 일괄 등록 |
| `ai/views.py` | chat·guardrail (현재 503 반환, ANTHROPIC_API_KEY 미설정) |
| `config/settings.py` | Django 설정, .env 로드 |
| `config/urls.py` | 전체 URL conf |
| `config/context_processors.py` | KAKAO_JS_KEY 템플릿 컨텍스트 |

---

## 주요 API 엔드포인트

| URL | 메서드 | 설명 |
|-----|--------|------|
| `/api/places/` | GET | 목록 (`?q=&era=&category=&region=`) |
| `/api/places/<pk>/` | GET | 상세 |
| `/api/places/filter/` | GET | 필터링 |
| `/api/places/<pk>/similar/` | GET | 비슷한 장소 4개 |
| `/api/places/ai-recommend/` | POST | 규칙 기반 추천 (`{radius: km}`) |
| `/api/places/route-optimize/` | POST | 최단 동선 정렬 |
| `/api/places/<pk>/reviews/` | GET·POST | 리뷰 목록·작성 |
| `/api/places/<pk>/reviews/<pk>/` | DELETE | 리뷰 삭제 |
| `/api/routes/` | GET·POST | 코스 목록·생성 |
| `/api/routes/<pk>/` | GET·PUT·DELETE | 코스 상세·수정·삭제 |
| `/api/routes/<pk>/like/` | POST | 좋아요 토글 |
| `/api/routes/<pk>/comments/` | GET·POST | 댓글 목록·작성 |
| `/api/routes/<pk>/comments/<pk>/` | DELETE | 댓글 삭제 |
| `/api/bookmarks/` | GET·POST | 북마크 목록(`?place=id`)·추가 |
| `/api/bookmarks/<pk>/` | DELETE | 북마크 삭제 |
| `/api/survey/save/` | POST | 설문 저장 |
| `/api/survey/reset/` | POST | 설문 초기화 |
| `/api/accounts/me/` | GET | 현재 로그인 유저 정보 |

---

## 세션 상태

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

## PythonAnywhere 최초 배포 (처음 등록할 때)

### 1. 계정 및 Web App 생성

1. [pythonanywhere.com](https://www.pythonanywhere.com) 접속 → 계정 생성 (무료 플랜 가능)
2. **Web** 탭 → **Add a new web app** → **Manual configuration** → **Python 3.12** 선택
   - Domain: `cultureroute.pythonanywhere.com` (무료 플랜 기본)

### 2. Bash 콘솔에서 코드 클론

**Consoles** 탭 → **New console: Bash**

```bash
# 홈 디렉토리에서 작업
cd ~

# private repo이면 GitHub 토큰 사용 (Settings → Developer settings → Personal access tokens → Classic)
git clone https://<토큰>@github.com/Jirunu/culture_route.git culture_route

cd culture_route
```

### 3. 가상환경 생성 및 패키지 설치

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. .env 파일 생성

```bash
nano .env
```

아래 내용 붙여넣기 (값 채우기):

```
SECRET_KEY=랜덤한_긴_문자열_여기에_입력
DEBUG=False
ALLOWED_HOSTS=cultureroute.pythonanywhere.com

PUBLIC_DATA_API_KEY=한국관광공사_키
OPENWEATHER_API_KEY=오픈웨더_키
KAKAO_JS_KEY=카카오_JS_키
KAKAO_REST_KEY=카카오_REST_키
ANTHROPIC_API_KEY=
```

> `SECRET_KEY` 생성: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

### 5. DB 업로드 및 정적 파일 수집

**DB는 로컬 `db.sqlite3`를 그대로 업로드한다** (장소·URL·시드 데이터·관리자 계정 포함).

1. PythonAnywhere **Files** 탭 → `/home/cultureroute/culture_route/` 경로 이동
2. `db.sqlite3` 파일 업로드 (덮어쓰기)
3. Bash 콘솔에서:

```bash
source venv/bin/activate
python manage.py migrate          # 혹시 미적용 마이그레이션 있으면 반영
python manage.py collectstatic --noinput
```

> 로컬 DB 기준: Place 531개, Route 58개(시드), Review 533개, User 101명(master 포함)
> master 계정은 is_superuser=True — 로컬에서 쓰는 비밀번호로 그대로 로그인 가능

> **DB 재업로드 시점**: 로컬에서 장소 추가·URL 세팅·시드 데이터 변경 등 데이터 작업 후
> 코드만 바뀐 경우엔 git pull + Reload만으로 충분

### 6. WSGI 파일 설정

**Web** 탭 → **WSGI configuration file** 링크 클릭 (보통 `/var/www/cultureroute_pythonanywhere_com_wsgi.py`)

기존 내용을 전부 지우고 아래로 교체:

```python
import sys
import os

path = '/home/cultureroute/culture_route'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 7. 가상환경 경로 설정

**Web** 탭 → **Virtualenv** 섹션:

```
/home/cultureroute/culture_route/venv
```

### 8. 정적 파일 설정

**Web** 탭 → **Static files** 섹션에 아래 두 줄 추가:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/cultureroute/culture_route/staticfiles` |

### 9. Reload

**Web** 탭 상단 **Reload** 버튼 클릭 → `cultureroute.pythonanywhere.com` 접속 확인

---

## PythonAnywhere 이후 업데이트 배포

코드 변경 후 PythonAnywhere에 반영하는 절차:

```bash
# Bash 콘솔 열기
cd ~/culture_route
source venv/bin/activate

git pull

# 모델 변경이 있으면
python manage.py migrate

# requirements.txt 변경이 있으면
pip install -r requirements.txt

# 정적 파일 변경이 있으면
python manage.py collectstatic --noinput
```

그 후 **Web** 탭 → **Reload** 클릭.

---

## 알려진 이슈 / 미완성

- `ai/views.py` chat·guardrail: `ANTHROPIC_API_KEY` 미설정 시 503 반환. 키 등록 후 구현 예정.
- `fetch_websites` (TourAPI 자동 수집): 일일 쿼터 소진으로 미활용. `set_websites`로 대체.
- 나무위키 링크: 장소명 ≠ 나무위키 문서명일 경우 404 가능 (자동 설정이므로 검증 안 됨).
- 리뷰 이미지: URL 입력 방식만 지원. S3 파일 업로드는 미구현.
- `ai/` 챗봇 페이지: 로그인 필요 (`login_required`), 현재 503 반환.
