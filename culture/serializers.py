from rest_framework import serializers
from .models import Theme, Place, Review, Route, RoutePlace, Bookmark, RouteComment
from accounts.badges import get_badge_info
from accounts.utils import get_display_name


# -----------------------------------------------
# Theme Serializer
# -----------------------------------------------
class ThemeSerializer(serializers.ModelSerializer):
    era_display = serializers.CharField(source='get_era_display', read_only=True)

    class Meta:
        model = Theme
        fields = ['id', 'name', 'era', 'era_display', 'description']


# -----------------------------------------------
# Place Serializers
# -----------------------------------------------
class PlaceListSerializer(serializers.ModelSerializer):
    """
    장소 목록 조회용 (간략 정보)
    """
    theme_name       = serializers.CharField(source='theme.name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    region_display   = serializers.CharField(source='get_region_display', read_only=True)
    avg_rating       = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = [
            'id', 'name', 'category', 'category_display',
            'region', 'region_display', 'theme_name',
            'address', 'latitude', 'longitude',
            'is_indoor', 'is_active',
            'entrance_fee', 'image_url', 'avg_rating',
        ]

    def get_avg_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews.exists():
            return None
        avg = sum(r.rating for r in reviews) / reviews.count()
        return round(avg, 1)


class PlaceDetailSerializer(serializers.ModelSerializer):
    """
    장소 상세 조회용 (전체 정보 + 리뷰 포함)
    """
    theme            = ThemeSerializer(read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    region_display   = serializers.CharField(source='get_region_display', read_only=True)
    reviews          = serializers.SerializerMethodField()
    avg_rating       = serializers.SerializerMethodField()
    review_count     = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = [
            'id', 'name', 'category', 'category_display',
            'region', 'region_display', 'theme',
            'address', 'latitude', 'longitude',
            'is_indoor', 'is_active',
            'open_time', 'entrance_fee', 'description',
            'image_url', 'website', 'avg_rating', 'review_count',
            'reviews', 'created_at', 'updated_at',
        ]

    def get_reviews(self, obj):
        reviews = obj.reviews.all()[:5]  # 최신 5개만
        return ReviewSerializer(reviews, many=True).data

    def get_avg_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews.exists():
            return None
        avg = sum(r.rating for r in reviews) / reviews.count()
        return round(avg, 1)

    def get_review_count(self, obj):
        return obj.reviews.count()


# -----------------------------------------------
# Review Serializer
# -----------------------------------------------
class ReviewSerializer(serializers.ModelSerializer):
    """
    리뷰 조회·생성·수정·삭제
    """
    username       = serializers.CharField(source='user.username', read_only=True)
    display_name   = serializers.SerializerMethodField()
    badge          = serializers.SerializerMethodField()
    place_name     = serializers.CharField(source='place.name', read_only=True)
    rating_display = serializers.CharField(source='get_rating_display', read_only=True)

    def get_badge(self, obj):
        return get_badge_info(obj.user)

    def get_display_name(self, obj):
        return get_display_name(obj.user)

    class Meta:
        model = Review
        fields = [
            'id', 'place', 'place_name',
            'user', 'username', 'display_name', 'badge',
            'rating', 'rating_display',
            'content',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['place', 'user', 'created_at', 'updated_at']

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError('별점은 1~5 사이여야 합니다.')
        return value

    def validate_content(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError('리뷰 내용은 5자 이상 입력해 주세요.')
        return value


# -----------------------------------------------
# Route Serializers
# -----------------------------------------------
class PlaceForRouteSerializer(serializers.ModelSerializer):
    """코스 카드용 최소 장소 정보 — avg_rating 제외해 N+1 쿼리 방지"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    region_display   = serializers.CharField(source='get_region_display',   read_only=True)

    class Meta:
        model = Place
        fields = [
            'id', 'name', 'category', 'category_display',
            'region', 'region_display',
            'address', 'latitude', 'longitude',
            'is_indoor', 'entrance_fee', 'image_url',
        ]


class RoutePlaceSerializer(serializers.ModelSerializer):
    """
    코스 내 장소 순서 정보
    """
    place = PlaceForRouteSerializer(read_only=True)

    class Meta:
        model = RoutePlace
        fields = ['order', 'place']


class RouteListSerializer(serializers.ModelSerializer):
    """
    동선 코스 목록 조회용 (간략 정보)
    """
    username               = serializers.CharField(source='user.username', read_only=True)
    user_id                = serializers.IntegerField(source='user.id', read_only=True)
    display_name           = serializers.SerializerMethodField()
    badge                  = serializers.SerializerMethodField()
    mode_display           = serializers.CharField(source='get_mode_display', read_only=True)
    transport_mode_display = serializers.CharField(source='get_transport_mode_display', read_only=True)
    place_count            = serializers.SerializerMethodField()
    comment_count          = serializers.SerializerMethodField()
    liked_by_me            = serializers.SerializerMethodField()
    route_places           = RoutePlaceSerializer(source='routeplace_set', many=True, read_only=True)

    class Meta:
        model = Route
        fields = [
            'id', 'title', 'username', 'user_id', 'display_name', 'badge',
            'mode', 'mode_display',
            'transport_mode', 'transport_mode_display',
            'total_distance', 'total_time',
            'place_count', 'is_shared', 'like_count',
            'comment_count', 'liked_by_me',
            'route_places', 'created_at',
        ]

    def get_place_count(self, obj):
        return len(obj.routeplace_set.all())

    def get_comment_count(self, obj):
        return len(obj.comments.all())

    def get_liked_by_me(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_badge(self, obj):
        return get_badge_info(obj.user)

    def get_display_name(self, obj):
        return get_display_name(obj.user)


class RouteDetailSerializer(serializers.ModelSerializer):
    """
    동선 코스 상세 조회용 (장소 순서 포함)
    """
    username               = serializers.CharField(source='user.username', read_only=True)
    display_name           = serializers.SerializerMethodField()
    badge                  = serializers.SerializerMethodField()
    mode_display           = serializers.CharField(source='get_mode_display', read_only=True)
    transport_mode_display = serializers.CharField(source='get_transport_mode_display', read_only=True)
    route_places           = RoutePlaceSerializer(source='routeplace_set', many=True, read_only=True)

    class Meta:
        model = Route
        fields = [
            'id', 'title', 'username', 'display_name', 'badge',
            'mode', 'mode_display',
            'transport_mode', 'transport_mode_display',
            'total_distance', 'total_time',
            'is_shared', 'like_count',
            'route_places', 'created_at',
        ]

    def get_badge(self, obj):
        return get_badge_info(obj.user)

    def get_display_name(self, obj):
        return get_display_name(obj.user)


class RouteCreateSerializer(serializers.ModelSerializer):
    """
    동선 코스 생성용
    place_ids: 순서대로 전달된 장소 id 리스트
    예) place_ids: [3, 7, 1]
    """
    place_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True
    )

    class Meta:
        model = Route
        fields = [
            'title', 'mode', 'transport_mode',
            'total_distance', 'total_time',
            'is_shared', 'is_footprint', 'place_ids',
        ]

    def validate_place_ids(self, value):
        if len(value) < 2:
            raise serializers.ValidationError('코스는 장소를 2개 이상 포함해야 합니다.')
        existing = Place.objects.filter(id__in=value).count()
        if existing != len(value):
            raise serializers.ValidationError('존재하지 않는 장소 ID가 포함되어 있습니다.')
        return value

    def create(self, validated_data):
        place_ids = validated_data.pop('place_ids')
        route = Route.objects.create(**validated_data)
        for order, place_id in enumerate(place_ids, start=1):
            RoutePlace.objects.create(route=route, place_id=place_id, order=order)
        return route

    def update(self, instance, validated_data):
        place_ids = validated_data.pop('place_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if place_ids is not None:
            instance.routeplace_set.all().delete()
            for order, place_id in enumerate(place_ids, start=1):
                RoutePlace.objects.create(route=instance, place_id=place_id, order=order)
        return instance


# -----------------------------------------------
# RouteComment Serializer
# -----------------------------------------------
class RouteCommentSerializer(serializers.ModelSerializer):
    username     = serializers.CharField(source='user.username', read_only=True)
    display_name = serializers.SerializerMethodField()
    badge        = serializers.SerializerMethodField()

    class Meta:
        model = RouteComment
        fields = ['id', 'route', 'username', 'display_name', 'badge', 'content', 'created_at', 'updated_at']
        read_only_fields = ['user', 'route', 'created_at', 'updated_at']

    def get_badge(self, obj):
        return get_badge_info(obj.user)

    def get_display_name(self, obj):
        return get_display_name(obj.user)

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError('댓글 내용을 입력해 주세요.')
        return value


# -----------------------------------------------
# Bookmark Serializer
# -----------------------------------------------
class BookmarkSerializer(serializers.ModelSerializer):
    """
    북마크 조회·생성·삭제
    place / route 중 하나만 지정해야 함
    """
    username   = serializers.CharField(source='user.username', read_only=True)
    place_name = serializers.CharField(source='place.name', read_only=True)
    route_title = serializers.CharField(source='route.title', read_only=True)

    class Meta:
        model = Bookmark
        fields = [
            'id', 'username',
            'place', 'place_name',
            'route', 'route_title',
            'created_at',
        ]
        read_only_fields = ['user', 'created_at']

    def validate(self, data):
        place = data.get('place')
        route = data.get('route')
        if not place and not route:
            raise serializers.ValidationError('장소 또는 코스 중 하나는 반드시 지정해야 합니다.')
        if place and route:
            raise serializers.ValidationError('장소와 코스를 동시에 북마크할 수 없습니다.')
        return data