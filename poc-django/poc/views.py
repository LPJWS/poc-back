from random import randint
import re
from django.db.models.deletion import SET_NULL
from django.shortcuts import render
from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler
from django.contrib.auth.password_validation import validate_password

from poc.models import User
from poc.serializers import *
from poc.tasks import *

import poc.utils

import os
import json
from datetime import date


class AuthView(viewsets.ViewSet):
    """
    Авторизация пользователей + генерация токена
    """
    permission_classes = (AllowAny,)
    serializer_class = AuthorizationSerializer

    @action(methods=['POST'], detail=False, url_path='signup', url_name='Sign Up User', permission_classes=permission_classes)
    def signup(self, request):
        data = request.data
        serializer = self.serializer_class(data=data, context={"signup": True, "request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['POST'], detail=False, url_path='signin', url_name='Sign In User', permission_classes=permission_classes)
    def signin(self, request):
        data = request.data
        serializer = self.serializer_class(data=data, context={"signup": False, "request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserView(viewsets.ViewSet):
    """
    Обновление профиля пользователя. Вывод информации о пользователе
    Использую экшны только для того, чтобы сохранить исходные роутинги
    """
    permission_classes = (IsAuthenticated, )
    serializer_class = UserUpdateSerializer

    @action(methods=['PATCH'], detail=False, url_path='edit', url_name='Edit User', permission_classes=[IsAuthenticated])
    def edit_user(self, request, *args, **kwargs):
        data = request.data
        serializer = self.serializer_class(instance=request.user, data=data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserDetailSerializer(instance=user, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='me', url_name='About User', permission_classes=[IsAuthenticated])
    def about_user(self, request, *args, **kwargs):
        return Response(UserDetailSerializer(instance=request.user, context={"request": request}).data, status=status.HTTP_200_OK)


class MemberView(viewsets.ViewSet):
    """
    Действия с участником
    """
    permission_classes = (AllowAny, )
    serializer_class = MemberSerializer

    @action(methods=['GET'], detail=False, url_path='get/(?P<id>[^/]+)', url_name='Get member by vk_id', permission_classes=permission_classes)
    def get_member(self, request, id, *args, **kwargs):
        params = request.GET
        member = poc.utils.verify(params)

        try:
            member_obj = Member.objects.get(vk_id=id)
        except Member.DoesNotExist:
            return Response({"info": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.serializer_class(instance=member_obj, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='me', url_name='Get my member', permission_classes=permission_classes)
    def get_me(self, request, *args, **kwargs):
        params = request.GET
        member = poc.utils.verify(params)

        return Response(MemberDetailSerializer(instance=member, context={"request": request}).data, status=status.HTTP_200_OK)


class CheckView(viewsets.ViewSet):
    """
    Действия со счетами
    """
    permission_classes = (AllowAny, )
    serializer_class = CheckSerializer

    @action(methods=['GET'], detail=False, url_path='get/(?P<id>[^/]+)', url_name='Get check', permission_classes=permission_classes)
    def get_check(self, request, id, *args, **kwargs):
        params = request.GET
        member = poc.utils.verify(params)

        try:
            check = Check.objects.get(id=id)
        except Check.DoesNotExist:
            return Response({"info": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.serializer_class(instance=check, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='new', url_name='New check', permission_classes=permission_classes)
    def new_check(self, request, *args, **kwargs):
        data = request.data
        params = request.GET
        member = poc.utils.verify(params)
        
        serializer = CheckSerializer(data=data, context={'member': member})
        serializer.is_valid(raise_exception=True)
        check = serializer.save()
        return Response(self.serializer_class(instance=check, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(methods=['PATCH'], detail=False, url_path='edit', url_name='Update check', permission_classes=permission_classes)
    def update_check(self, request, *args, **kwargs):
        data = request.data
        params = request.GET
        member = poc.utils.verify(params)
        
        try:
            check = Check.objects.get(id=data.get('id'))
        except Check.DoesNotExist:
            return Response({"info": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CheckSerializer(instance=check, data=data, context={'member': member})
        serializer.is_valid(raise_exception=True)
        check = serializer.save()
        return Response(self.serializer_class(instance=check, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='close', url_name='Close check', permission_classes=permission_classes)
    def close_check(self, request, *args, **kwargs):
        data = request.data
        params = request.GET
        member = poc.utils.verify(params)
        
        try:
            check = Check.objects.get(id=data.get('id'))
        except Check.DoesNotExist:
            return Response({"info": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CheckSerializer(instance=check, context={'member': member})
        check = serializer.close(check)
        return Response(self.serializer_class(instance=check, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='join', url_name='Join check', permission_classes=permission_classes)
    def join_check(self, request, *args, **kwargs):
        data = request.data
        params = request.GET
        member = poc.utils.verify(params)
        
        try:
            check = Check.objects.get(id=data.get('id'))
        except Check.DoesNotExist:
            return Response({"info": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CheckSerializer(instance=check, context={'member': member})
        serializer.join(check)
        return Response(self.serializer_class(instance=check, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='leave', url_name='Leave check', permission_classes=permission_classes)
    def leave_check(self, request, *args, **kwargs):
        data = request.data
        params = request.GET
        member = poc.utils.verify(params)
        
        try:
            check = Check.objects.get(id=data.get('id'))
        except Check.DoesNotExist:
            return Response({"info": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CheckSerializer(instance=check, context={'member': member})
        serializer.leave(check)
        return Response({"info": "ok"}, status=status.HTTP_200_OK)


class CheckRecordView(viewsets.ViewSet):
    """
    Действия с записями счетов
    """
    permission_classes = (AllowAny, )
    serializer_class = CheckRecordDetailSerializer

    @action(methods=['GET'], detail=False, url_path='get/(?P<id>[^/]+)', url_name='Get check record', permission_classes=permission_classes)
    def get_check_record(self, request, id, *args, **kwargs):
        params = request.GET
        member = poc.utils.verify(params)

        try:
            check_record = CheckRecord.objects.get(id=id)
        except CheckRecord.DoesNotExist:
            return Response({"info": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.serializer_class(instance=check_record, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='new', url_name='New check record', permission_classes=permission_classes)
    def new_check_record(self, request, *args, **kwargs):
        data = request.data
        params = request.GET
        member = poc.utils.verify(params)
        
        serializer = CheckRecordSerializer(data=data, context={'member': member})
        serializer.is_valid(raise_exception=True)
        check_record = serializer.save()
        return Response(self.serializer_class(instance=check_record, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(methods=['PATCH'], detail=False, url_path='edit', url_name='Update check record', permission_classes=permission_classes)
    def update_check_record(self, request, *args, **kwargs):
        data = request.data
        params = request.GET
        member = poc.utils.verify(params)
        
        try:
            check_record = CheckRecord.objects.get(id=data.get('id'))
        except CheckRecord.DoesNotExist:
            return Response({"info": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CheckRecordSerializer(instance=check_record, data=data, context={'member': member})
        serializer.is_valid(raise_exception=True)
        check_record = serializer.save()
        return Response(self.serializer_class(instance=check_record, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='delete', url_name='Delete check record', permission_classes=permission_classes)
    def delete_check_record(self, request, *args, **kwargs):
        data = request.data
        params = request.GET
        member = poc.utils.verify(params)
        
        try:
            check_record = CheckRecord.objects.get(id=data.get('id'))
        except CheckRecord.DoesNotExist:
            return Response({"info": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CheckRecordSerializer(instance=check_record, context={'member': member})
        serializer.remove(check_record)
        return Response({"info": "ok"}, status=status.HTTP_200_OK)
