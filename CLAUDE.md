# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CultureRoute** — 서울·경기 지역 문화 명소 추천 서비스. Django REST Framework 백엔드 + 멀티 페이지 HTML 프론트엔드(Django TemplateView 서빙).

## Commands

```powershell
# 가상환경 활성화 (PowerShell)
.\venv\Scripts\Activate.ps1

# 개발 서버 실행
python manage.py runserver

# 마이그레이션
python manage.py makemigrations
python manage.py migrate

# 샘플 데이터 로드
python manage.py loaddata sample_data

# 전체 테스트
python manage.py test

# 앱별 테스트
python manage.py test culture
python manage.py test accounts

# 슈퍼유저 생성 (Admin 접근용)
python manage.py createsuperuser
```

## Architecture

### 앱 구조

| 앱 | 역할 |
|---|---|
| `config/` | Django 프로젝트 설정 (settings, root URLs, wsgi/asgi, context_processors) |
| `culture/` | 핵심 도메인 앱 — 모델, 시리얼라이저, 뷰, URL |
| `accounts/` | 인증 앱 — 회원가입/로그인/로그아웃/me 엔드포인트 |
| `templates/` | 멀티 페이지 HTML (Django 템플릿 엔진으로 렌더링) |

### 템플릿 페이지 목록

| URL | 템플릿 | 설명 |
|---|---|---|
| `/` | `index.html` | 메인 랜딩 — 장소 그리드, 날씨 추천 섹션 |
| `/places/` | `places.html` | 장소 목록 — 필터(시대/카테고리/지역/실내외) + 그리드/지도 토글 |
| `/places/<pk>/` | `place_detail.html` | 장소 상세 — 정보, 카카오 지도, 리뷰 목록/작성 |
| `/routes/` | `routes.html` | 커뮤니티 코스 목록, 코스 생성, 좋아요 |
| `/login/` | `login.html` | 로그인 폼, `?next=` 리다이렉트 지원 |
| `/signup/` | `signup.html` | 회원가입 폼 |
| `/preview/` | `preview.html` | 셀프컨테인드 UI 미리보기 (API 연동 없음) |

모든 HTML 파일은 Django 템플릿 변수를 사용할 수 있음 (예: `{{ KAKAO_JS_KEY }}`).  
`config/context_processors.py`의 `public_settings`가 `KAKAO_JS_KEY`를 전체 템플릿에 자동 주입.

### 데이터 모델 관계

```
Theme (시대 테마)
  └─ Place (문화 장소)  FK→Theme (SET_NULL)
       ├─ Review        FK→Place + FK→User
       ├─ RoutePlace    FK→Place + FK→Route  (순서 저장 중간 테이블)
       └─ Bookmark      FK→Place (nullable)

Route (동선 코스)  FK→User
  ├─ RoutePlace    FK→Route  (M2M through)
  └─ Bookmark      FK→Route (nullable)

Bookmark — place 또는 route 중 하나만 지정 가능
           (Bookmark.clean() + BookmarkSerializer.validate() 두 곳에서 검증)
```

### API 엔드포인트

#### 인증 (`/api/accounts/`, `accounts/urls.py`)

| 경로 | 메서드 | 인증 | 설명 |
|---|---|---|---|
| `accounts/me/` | GET | 불필요 | 로그인 상태 확인 + **CSRF 쿠키 설정** (`@ensure_csrf_cookie`) |
| `accounts/login/` | POST | 불필요 | 세션 로그인 |
| `accounts/logout/` | POST | 불필요 | 세션 로그아웃 |
| `accounts/signup/` | POST | 불필요 | 회원가입 (생성 후 자동 로그인) |

> **CSRF 패턴**: 모든 페이지가 로드 시 `/api/accounts/me/`를 호출(`initNav()`)하므로 CSRF 쿠키가 항상 세팅됨. 이후 POST 요청은 `getCsrfToken()`으로 쿠키값을 읽어 `X-CSRFToken` 헤더에 담아 전송.

#### 문화 장소 / 리뷰 / 코스 / 북마크 (`/api/`, `culture/urls.py`)

| 경로 | 메서드 | 인증 | 설명 |
|---|---|---|---|
| `places/` | GET | 불필요 | 전체 장소 목록 |
| `places/filter/` | GET | 불필요 | era/category/region/is_indoor 쿼리 파라미터 필터 |
| `places/weather/` | GET | 불필요 | is_indoor/is_active 파라미터 기반 장소 필터 |
| `places/weather-current/` | GET | 불필요 | OpenWeatherMap 실시간 날씨 조회 + 실내/외 추천 |
| `places/<pk>/` | GET | 불필요 | 장소 상세 (리뷰 최신 5개 포함) |
| `places/<pk>/reviews/` | GET+POST | GET 불필요, POST 필요 | 리뷰 목록/작성 |
| `places/<pk>/reviews/<pk>/` | GET+PUT+DELETE | GET 불필요, 나머지 작성자만 | 리뷰 상세/수정/삭제 |
| `routes/` | GET+POST | GET 불필요, POST 필요 | 공유 코스 목록 / 코스 생성 |
| `routes/<pk>/` | GET+PUT+DELETE | GET 불필요, 나머지 생성자만 | 코스 상세/수정/삭제 |
| `routes/<pk>/like/` | POST | 필요 | 좋아요 +1 (중복 방지 없음) |
| `bookmarks/` | GET+POST | 필요 | 내 북마크 목록/추가 |
| `bookmarks/<pk>/` | DELETE | 필요 | 북마크 삭제 |

### 시리얼라이저 패턴

- **List/Detail 분리**: `PlaceListSerializer`(간략 + `entrance_fee`, `latitude`, `longitude` 포함) / `PlaceDetailSerializer`(전체+리뷰).
- **RouteCreateSerializer**: `place_ids: [int]` 리스트를 받아 `RoutePlace` 중간 테이블을 `create()` 내부에서 직접 생성. 장소 2개 이상 필수.
- **avg_rating**: `PlaceListSerializer`와 `PlaceDetailSerializer` 모두 `SerializerMethodField`로 계산 — 대량 데이터 시 N+1 주의.

### 외부 API 클라이언트 (`culture/api_clients.py`)

| 함수 | 용도 |
|---|---|
| `fetch_heritage_list()` | 한국관광공사 TourAPI — 지역기반 관광정보 조회 |
| `fetch_weather()` | OpenWeatherMap — 날씨 조회 및 실내/동적 여부 판단 |
| `fetch_route_distance()` | 두 좌표 간 하버사인 직선거리 + 도보 소요시간 계산 |

### 카카오 지도 (Kakao Maps)

- `KAKAO_JS_KEY`는 `.env`에서 로드되어 `config/context_processors.py`가 모든 템플릿에 주입.
- `places.html`: 그리드/지도 뷰 토글. 지도 뷰에서 필터된 전체 장소를 마커로 표시, 마커 클릭 시 상세 페이지 링크.
- `place_detail.html`: 장소 상세 페이지에 해당 장소 위치 지도 + 마커 표시.
- 지도 관련 스크립트는 `{% if KAKAO_JS_KEY %}<script src="//dapi.kakao.com/v2/maps/sdk.js?appkey={{ KAKAO_JS_KEY }}">{% endif %}` 패턴으로 조건부 로드.

## 환경 변수 (`.env`)

| 키 | 용도 |
|---|---|
| `PUBLIC_DATA_API_KEY` | 한국관광공사 TourAPI 인증키 |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API 키 |
| `KAKAO_JS_KEY` | 카카오 지도 JavaScript SDK 키 (브라우저 노출용) |
| `KAKAO_REST_KEY` | 카카오 REST API 키 (서버사이드용) |

## 샘플 데이터

`culture/fixtures/sample_data.json` — Theme 5개 + Place 12개 (서울·경기 주요 문화 명소).  
`python manage.py loaddata sample_data`로 로드.

## 주요 설계 특이사항

- `route.like_count`는 DB 컬럼에 직접 +1. 별도 Like 모델이 없어 중복 좋아요 방지 불가.
- `review_list` POST와 `create_review` POST는 동일한 역할의 중복 엔드포인트 (두 경로 모두 동작).
- `places/weather/`는 파라미터 필터 방식, `places/weather-current/`는 OpenWeatherMap 실시간 조회. 프론트는 `weather-current` 먼저 호출 후 `is_indoor` 값을 `weather/` 필터에 전달하는 방식으로 연동.
- DB는 SQLite (`db.sqlite3`). 이미지는 URL 문자열로 저장 (파일 업로드 없음).
- `accounts` 앱은 Django 기본 `User` 모델 그대로 사용. 프로필 확장 없음.
