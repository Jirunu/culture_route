from django.urls import path
from . import views

urlpatterns = [
    # ── 장소 ──────────────────────────────────────────
    path('places/',                views.place_list,         name='place_list'),         # F808
    path('places/filter/',         views.place_by_theme,     name='place_by_theme'),     # F810
    path('places/visited-ids/',    views.visited_place_ids,  name='visited_place_ids'),
    path('places/weather/',         views.weather_recommend,  name='weather_recommend'),  # F816
    path('places/weather-current/', views.weather_current,   name='weather_current'),    # F818
    path('places/<int:place_pk>/',  views.place_detail,      name='place_detail'),       # F809
    path('places/<int:place_pk>/similar/', views.place_similar, name='place_similar'),

    # ── 리뷰 ──────────────────────────────────────────
    path('places/<int:place_pk>/reviews/',                    views.review_list,   name='review_list'),   # F811
    path('places/<int:place_pk>/reviews/create/',             views.create_review, name='create_review'), # F813
    path('places/<int:place_pk>/reviews/<int:review_pk>/',    views.review_detail, name='review_detail'), # F812

    # ── 동선 코스 ─────────────────────────────────────
    path('routes/',                  views.route_recommend, name='route_recommend'), # F814
    path('routes/<int:route_pk>/',   views.route_detail,    name='route_detail'),
    path('routes/<int:route_pk>/like/', views.route_like,   name='route_like'),     # F819
    path('routes/<int:route_pk>/comments/', views.route_comments, name='route_comments'),
    path('routes/<int:route_pk>/comments/<int:comment_pk>/', views.route_comment_detail, name='route_comment_detail'),

    # ── 북마크 ────────────────────────────────────────
    path('bookmarks/',                    views.bookmark_list,   name='bookmark_list'),   # F815
    path('bookmarks/<int:bookmark_pk>/',  views.bookmark_detail, name='bookmark_detail'), # F815

    # ── AI 추천 ───────────────────────────────────────
    path('places/ai-recommend/',   views.ai_recommend,   name='ai_recommend'),
    path('places/route-optimize/',   views.route_optimize,   name='route_optimize'),
    path('places/route-story/',      views.route_story,      name='route_story'),
    path('places/route-directions/', views.route_directions, name='route_directions'),
    path('places/route-transit-info/', views.route_transit_info, name='route_transit_info'),
]
