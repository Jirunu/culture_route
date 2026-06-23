from django.db import models
from django.contrib.auth.models import User


# F803 - Theme 클래스
class Theme(models.Model):
    """
    시대 테마 모델
    예: 삼국시대, 고려시대, 조선시대, 일제강점기, 현대
    """
    ERA_CHOICES = [
        ('three_kingdoms', '삼국시대'),
        ('goryeo',         '고려시대'),
        ('joseon',         '조선시대'),
        ('japanese',       '일제강점기'),
        ('modern',         '현대'),
    ]

    name        = models.CharField(max_length=50, unique=True, verbose_name='테마명')
    era         = models.CharField(max_length=20, choices=ERA_CHOICES, verbose_name='시대 구분')
    description = models.TextField(blank=True, verbose_name='테마 설명')

    class Meta:
        verbose_name = '테마'
        verbose_name_plural = '테마 목록'

    def __str__(self):
        return self.name


# F802 - Place 클래스
class Place(models.Model):
    """
    문화 장소 모델
    문화재청 OpenAPI / 공공데이터 포털에서 수집한 서울·경기 문화 명소
    """
    CATEGORY_CHOICES = [
        ('historic',  '역사 유적'),
        ('museum',    '박물관·미술관'),
        ('palace',    '궁궐·사찰'),
    ]

    REGION_CHOICES = [
        ('seoul',   '서울'),
        ('gyeonggi', '경기'),
    ]

    name         = models.CharField(max_length=100, verbose_name='장소명')
    category     = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='카테고리')
    region       = models.CharField(max_length=20, choices=REGION_CHOICES, verbose_name='지역')
    theme        = models.ForeignKey(Theme, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='places', verbose_name='테마')
    address      = models.CharField(max_length=200, verbose_name='주소')
    latitude     = models.DecimalField(max_digits=9, decimal_places=6, verbose_name='위도')
    longitude    = models.DecimalField(max_digits=9, decimal_places=6, verbose_name='경도')
    is_indoor    = models.BooleanField(default=False, verbose_name='실내 여부')
    is_active    = models.BooleanField(default=False, verbose_name='동적 장소 여부')
    open_time    = models.CharField(max_length=100, blank=True, verbose_name='운영 시간')
    entrance_fee = models.PositiveIntegerField(default=0, verbose_name='입장료 (원)')
    description  = models.TextField(blank=True, verbose_name='장소 설명')
    image_url    = models.URLField(blank=True, verbose_name='대표 이미지 URL')
    website      = models.URLField(blank=True, verbose_name='공식 홈페이지 URL')
    created_at   = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    updated_at   = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        verbose_name = '문화 장소'
        verbose_name_plural = '문화 장소 목록'

    def __str__(self):
        return f'[{self.get_region_display()}] {self.name}'


# F804 - Review 클래스
class Review(models.Model):
    """
    리뷰 모델
    유저가 특정 장소에 작성하는 리뷰·별점
    """
    place      = models.ForeignKey(Place, on_delete=models.CASCADE,
                                   related_name='reviews', verbose_name='장소')
    user       = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='reviews', verbose_name='작성자')
    rating     = models.PositiveSmallIntegerField(
                     choices=[(i, f'{i}점') for i in range(1, 6)],
                     verbose_name='별점')
    content    = models.TextField(verbose_name='리뷰 내용')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        verbose_name = '리뷰'
        verbose_name_plural = '리뷰 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.place.name} ({self.rating}점)'


# F805 - Route 클래스
class Route(models.Model):
    """
    동선 코스 모델
    자동 생성 코스 및 유저가 커뮤니티에 공유한 코스를 저장
    """
    MODE_CHOICES = [
        ('distance', '거리 기준'),
        ('theme',    '테마 기준'),
        ('time',     '소요시간 기준'),
    ]
    TRANSPORT_CHOICES = [
        ('walk',    '도보'),
        ('bike',    '자전거'),
        ('transit', '대중교통'),
        ('car',     '자동차'),
        ('train',   '기차'),
    ]

    user           = models.ForeignKey(User, on_delete=models.CASCADE,
                                       related_name='routes', verbose_name='생성 유저')
    title          = models.CharField(max_length=100, verbose_name='코스명')
    places         = models.ManyToManyField(Place, through='RoutePlace',
                                            related_name='routes', verbose_name='장소 목록')
    mode           = models.CharField(max_length=20, choices=MODE_CHOICES, verbose_name='추천 모드')
    transport_mode = models.CharField(max_length=20, choices=TRANSPORT_CHOICES, default='car', verbose_name='이동수단')
    total_distance = models.PositiveIntegerField(default=0, verbose_name='총 거리 (m)')
    total_time     = models.PositiveIntegerField(default=0, verbose_name='총 소요시간 (분)')
    is_shared      = models.BooleanField(default=False, verbose_name='커뮤니티 공유 여부')
    is_footprint   = models.BooleanField(default=False, verbose_name='여행 완료 시 자동 기록된 발자취 여부')
    like_count     = models.PositiveIntegerField(default=0, verbose_name='좋아요 수')
    created_at     = models.DateTimeField(auto_now_add=True, verbose_name='생성일')

    class Meta:
        verbose_name = '동선 코스'
        verbose_name_plural = '동선 코스 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username}의 코스 - {self.title}'


class RoutePlace(models.Model):
    """
    Route ↔ Place 중간 테이블
    코스 내 장소 순서를 저장
    """
    route = models.ForeignKey(Route, on_delete=models.CASCADE, verbose_name='코스')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, verbose_name='장소')
    order = models.PositiveSmallIntegerField(verbose_name='순서')

    class Meta:
        verbose_name = '코스 장소 순서'
        ordering = ['order']
        unique_together = ('route', 'order')

    def __str__(self):
        return f'{self.route.title} - {self.order}번째: {self.place.name}'


# F806 - Bookmark 클래스
class Bookmark(models.Model):
    """
    북마크 모델
    유저가 저장한 장소 또는 코스를 관리
    place / route 중 하나만 저장 (둘 다 null이면 안 됨 — clean()으로 검증)
    """
    user       = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='bookmarks', verbose_name='유저')
    place      = models.ForeignKey(Place, on_delete=models.CASCADE,
                                   null=True, blank=True,
                                   related_name='bookmarked_by', verbose_name='장소')
    route      = models.ForeignKey(Route, on_delete=models.CASCADE,
                                   null=True, blank=True,
                                   related_name='bookmarked_by', verbose_name='코스')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='저장일')

    class Meta:
        verbose_name = '북마크'
        verbose_name_plural = '북마크 목록'
        unique_together = [('user', 'place'), ('user', 'route')]

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.place and not self.route:
            raise ValidationError('장소 또는 코스 중 하나는 반드시 지정해야 합니다.')
        if self.place and self.route:
            raise ValidationError('장소와 코스를 동시에 북마크할 수 없습니다.')

    def __str__(self):
        target = self.place.name if self.place else self.route.title
        return f'{self.user.username} → {target}'


class RouteLike(models.Model):
    user  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='route_likes')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'route')
        verbose_name = '코스 좋아요'
        verbose_name_plural = '코스 좋아요 목록'

    def __str__(self):
        return f'{self.user.username} ♥ {self.route.title}'


class RouteComment(models.Model):
    route   = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='comments')
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='route_comments')
    content = models.TextField(verbose_name='댓글 내용')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = '코스 댓글'
        verbose_name_plural = '코스 댓글 목록'

    def __str__(self):
        return f'{self.user.username} on {self.route.title}: {self.content[:30]}'