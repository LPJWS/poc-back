from datetime import datetime, timedelta
import re
from django.utils import timezone
from email.policy import default
import random
from typing import List
from django.db.models.deletion import CASCADE, SET_NULL
import jwt as jwt
from django.contrib.auth.models import AbstractUser
from django.db import models
from configs import settings
from django.db.models import Avg, Sum, Count

from .validators import *

from math import sqrt
import re


class User(AbstractUser):
    """
    [User]
    Переопределенный класс пользователя. Использует кастомный менеджер.
    """

    name = models.CharField(max_length=30, blank=True, null=True, verbose_name="имя пользователя")
    username = models.CharField(max_length=50, unique=True, verbose_name='номер телефона/email')
    photo = models.ImageField(upload_to='user_images', blank=True, null=True)

    USERNAME_FIELD = 'username'

    def __str__(self) -> str:
        return f"{self.username}"

    @property
    def token(self) -> str:
        return self._generate_jwt_token()

    def _generate_jwt_token(self) -> str:
        """
        Генерирует веб-токен JSON, в котором хранится идентификатор этого
        пользователя, срок действия токена составляет 30 дней от создания
        """
        dt = datetime.now() + timedelta(days=30)

        token = jwt.encode({
            'id': self.pk,
            'expire': str(dt)
        }, settings.SECRET_KEY, algorithm='HS256')

        return token.decode('utf-8')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Member(models.Model):
    """
    [Member]
    Модель участника
    """
    vk_id = models.IntegerField(unique=True, verbose_name='VK id')
    name = models.CharField(max_length=75, null=True, blank=True, verbose_name='Имя')
    photo = models.CharField(max_length=500, null=True, blank=True, verbose_name='Ссылка на фото')

    def __str__(self) -> str:
        return f"{self.name} ({self.vk_id})"

    class Meta:
        verbose_name = 'Участник'
        verbose_name_plural = 'Участники'
