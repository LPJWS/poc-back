from django.conf.urls import url, include
from django.urls import path
from rest_framework.routers import SimpleRouter

from poc.views import *

router = SimpleRouter()
router.register(r'auth', AuthView, basename='auth')
router.register(r'user', UserView, basename='user')
router.register(r'member', MemberView, basename='member')
router.register(r'check', CheckView, basename='check')
router.register(r'record', CheckRecordView, basename='record')
router.register(r'debt', DebtView, basename='debt')

urlpatterns = [
    # path('auth/send/', reset_password),
    # path('auth/send/', send_sms_code),
    # url(r'^auth/registration/$', TokenViewSet.as_view()),
    # path('fcm/', FCMDeviceAuthorizedViewSet.as_view({'post': 'create'}), name='create_fcm_device'),
    # url('', include('social_django.urls'))
]

urlpatterns += router.urls
