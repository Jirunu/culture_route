from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    password2 = request.data.get('password2', '')

    if not username:
        return Response({'detail': '아이디를 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(username) < 3:
        return Response({'detail': '아이디는 3자 이상이어야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(password) < 8:
        return Response({'detail': '비밀번호는 8자 이상이어야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    if password != password2:
        return Response({'detail': '비밀번호가 일치하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({'detail': '이미 사용 중인 아이디입니다.'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password)
    login(request, user)
    return Response({'username': user.username, 'id': user.id}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response({'detail': '아이디와 비밀번호를 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({'detail': '아이디 또는 비밀번호가 올바르지 않습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

    login(request, user)
    return Response({'username': user.username, 'id': user.id})


@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({'detail': '로그아웃 되었습니다.'})


# ensure_csrf_cookie: 모든 페이지 로드 시 이 엔드포인트를 호출해 CSRF 쿠키를 설정한다
@api_view(['GET'])
@ensure_csrf_cookie
def me(request):
    if request.user.is_authenticated:
        return Response({'username': request.user.username, 'id': request.user.id})
    return Response({'detail': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
