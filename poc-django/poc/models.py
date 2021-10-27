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


class Check(models.Model):
    """
    [Check]
    Модель счета
    """
    title = models.CharField(max_length=75, blank=True, null=True, verbose_name="Название")
    organizer = models.ForeignKey(Member, on_delete=SET_NULL, null=True, verbose_name="Создатель счета")
    active = models.BooleanField(default=True, verbose_name="Активен?")
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата закрытия')

    def __str__(self) -> str:
        return f"{self.title}"

    class Meta:
        verbose_name = 'Счет'
        verbose_name_plural = 'Счета'


class CheckMember(models.Model):
    """
    [CheckMember]
    Модель участника счета
    """
    member = models.ForeignKey(Member, on_delete=SET_NULL, null=True, verbose_name="Участник")
    check_obj = models.ForeignKey(Check, on_delete=SET_NULL, null=True, verbose_name="Счет")

    def __str__(self) -> str:
        return f"{self.member} ({self.check_obj})"

    class Meta:
        verbose_name = 'Участник счета'
        verbose_name_plural = 'Участники счетов'


class CheckRecord(models.Model):
    """
    [CheckRecord]
    Модель траты по счету
    """
    member = models.ForeignKey(Member, on_delete=SET_NULL, null=True, verbose_name="Участник счета")
    check_obj = models.ForeignKey(Check, on_delete=SET_NULL, null=True, verbose_name="Счет")
    object = models.CharField(max_length=75, blank=True, null=True, verbose_name="Объект траты")
    desc = models.TextField(blank=True, null=True, verbose_name="Описание траты")
    amount = models.FloatField(default=0.0, verbose_name="Сумма")

    def __str__(self) -> str:
        return f"{self.member} -> {self.amount} ({self.object}) (Счет: {self.check_obj})"

    class Meta:
        verbose_name = 'Трата по счету'
        verbose_name_plural = 'Траты по счетам'
