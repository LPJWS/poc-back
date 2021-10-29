import os
from collections import OrderedDict
from django import utils

from django.core.validators import ProhibitNullCharactersValidator
from django.db.models import fields, Sum
import requests
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.contrib.auth.password_validation import validate_password
from rest_framework.fields import FileField, SkipField, ImageField
from rest_framework.relations import PKOnlyObject

from .models import *
import poc.utils

class BaseImageSerializer(serializers.ModelSerializer):

    def build_image_url(self, field):
        path = f'{"https" if settings.DEBUG is False else "http"}://' \
               f'{os.getenv("HOST_NAME") if settings.DEBUG is False else "0.0.0.0:8000"}{settings.MEDIA_URL}{field}'
        return path


    def to_representation(self, instance):
        ret = OrderedDict()
        fields = self._readable_fields

        for field in fields:
            try:
                attribute = field.get_attribute(instance)
            except SkipField:
                continue

            check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            if check_for_none is None:
                ret[field.field_name] = None
            else:
                # тут проверка
                if isinstance(field, ImageField) or isinstance(field, FileField):
                    try:
                        ret[field.field_name] = self.build_image_url(attribute)
                    except:
                        ret[field.field_name] = field.to_representation(attribute)
                else:
                    ret[field.field_name] = field.to_representation(attribute)
        return ret


class AuthorizationSerializer(BaseImageSerializer):
    """ Сериализация авторизации """

    token = serializers.CharField(max_length=255, read_only=True)
    username = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=50, required=False)
    password = serializers.CharField(max_length=50, write_only=True)
    # password = serializers.CharField(max_length=50, validators=(validate_password,), write_only=True)
    photo = serializers.ImageField(required=False, use_url=True)

    def create(self, validated_data):
        is_signup = self.context['signup']
        user, created = User.objects.get_or_create(username=validated_data.get('username'))
        if created:
            if not is_signup:
                user.delete()
                raise serializers.ValidationError({'info': 'Bad username/password'})
            # user.name = validated_data['name'] # Так почему то он сохраняет в виде кортежа из одного элемента
            setattr(user, 'name', validated_data['name']) # А вот так как строку
            user.set_password(validated_data.get('password'))
            user.photo = validated_data.get('photo')
            user.save()
        else:
            if is_signup:
                raise serializers.ValidationError({'info': f'User with phone/email {validated_data.get("username")} already exists'})
            if not user.check_password(validated_data.get('password')):
                raise serializers.ValidationError({'info': 'Bad username/password'})
        return user

    class Meta:
        model = User
        fields = "__all__"


class UserDetailSerializer(BaseImageSerializer):
    """
    Сериализатор для детального отображения пользователя
    """

    class Meta:
        model = User
        fields = ['username', 'name', 'photo']


class UserUpdateSerializer(BaseImageSerializer):
    """
    Сериализатор для обновления пользователя
    """
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name')
        instance.photo = validated_data.get('photo')
        old_pass = validated_data.get('old_password')
        new_pass = validated_data.get('new_password')
        if old_pass is not None and new_pass is not None:
            if instance.check_password(old_pass):
                # try:
                #     validate_password(new_pass)
                # except Exception as e:
                #     raise ValidationError(e)
                instance.set_password(new_pass)
            else:
                raise ValidationError({'info': 'Wrong password'})
        instance.save()
        return instance

    class Meta:
        model = User
        fields = ['username', 'name', 'photo', 'old_password', 'new_password']


class MemberSerializer(BaseImageSerializer):
    """
    Сериализатор для общего отображения пользователя
    """

    def create(self, validated_data):
        member, created = Member.objects.get_or_create(
            vk_id=validated_data.get('vk_id')
        )
        if created:
            vk_user_object = poc.utils.get_name_by_id(validated_data.get('vk_id'))
            name = f"{vk_user_object['first_name']} {vk_user_object['last_name']}"
            photo = vk_user_object['photo_200']
            member.name = name
            member.photo = photo
            member.save()
        return member

    class Meta:
        model = Member
        fields = '__all__'


class MemberDetailSerializer(BaseImageSerializer):
    """
    Сериализатор для детального пользователя
    """
    debts = serializers.SerializerMethodField()
    debtors = serializers.SerializerMethodField()
    checks = serializers.SerializerMethodField()

    def get_debts(self, object):
        member_debts = Debt.objects.filter(from_member=object, is_confirmed=False)
        return DebtSerializer(instance=member_debts, many=True).data

    def get_debtors(self, object):
        member_debtors = Debt.objects.filter(to_member=object, is_confirmed=False)
        return DebtSerializer(instance=member_debtors, many=True).data

    def get_checks(self, object):
        member_checks = Check.objects.filter(checkmember__in=CheckMember.objects.filter(member=object), active=True)
        return CheckListSerializer(instance=member_checks, many=True).data

    class Meta:
        model = Member
        fields = '__all__'


class CheckSerializer(BaseImageSerializer):
    """
    Сериализатор для счетов
    """
    organizer = MemberSerializer(read_only=True)
    records = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    debts = serializers.SerializerMethodField()

    def get_members(self, object):
        members_ = Member.objects.filter(checkmember__in=CheckMember.objects.filter(check_obj=object))
        return MemberSerializer(instance=members_, many=True, context=self.context).data

    def get_records(self, object):
        records_ = CheckRecord.objects.filter(check_obj=object)
        return CheckRecordListSerializer(instance=records_, many=True, context=self.context).data

    def get_total_amount(self, object):
        total_amount_ = CheckRecord.objects.filter(check_obj=object).aggregate(Sum('amount'))['amount__sum']
        return total_amount_ if total_amount_ else 0.0

    def get_debts(self, object):
        check_debts = Debt.objects.filter(check_obj=object)
        return DebtSerializer(instance=check_debts, many=True, context=self.context).data
        

    def create(self, validated_data):
        member = self.context.get('member')
        check = Check.objects.create(
            title=validated_data.get('title'),
            organizer=member
        )
        check.save()
        check_member = CheckMember.objects.create(check_obj=check, member=member)
        check_member.save()
        return check

    def update(self, instance: Check, validated_data):
        member = self.context.get('member')
        if instance.organizer != member:
            raise PermissionDenied({"info": "You can't edit this check"})
        if not instance.active:
            raise ValidationError({"info": "Check closed"})

        title = validated_data.get('title')

        instance.title = title if title else instance.title

        instance.save()
        return instance

    def close(self, instance: Check):
        member = self.context.get('member')
        if member != instance.organizer:
            raise PermissionDenied({"info": "You can't close this check"})
        if instance.active or not instance.closed_at:
            instance.active = False
            instance.closed_at = timezone.now()
            instance.save()

            records_ = CheckRecord.objects.filter(check_obj=instance)
            members_ = Member.objects.filter(checkmember__in=CheckMember.objects.filter(check_obj=instance))
            count = len(members_)
            total = {member: 0.0 for member in members_}

            for record in records_:
                total[record.member] += record.amount

            for i in total.keys():
                total[i] /= count

            for member in members_:
                for member_ in members_:
                    if member == member_:
                        continue
                    if total[member] < total[member_]:
                        Debt.objects.create(
                            from_member = member,
                            to_member=member_,
                            amount=total[member_] - total[member],
                            check_obj=instance
                        )
        return instance

    def join(self, instance: Check):
        member = self.context.get('member')
        
        check_member, created = CheckMember.objects.get_or_create(member=member, check_obj=instance)
        if created:
            check_member.save()

        return instance

    def leave(self, instance: Check):
        member = self.context.get('member')
        
        try:
            check_member = CheckMember.objects.get(member=member, check_obj=instance)
        except CheckMember.DoesNotExist:
            raise ValidationError({"info": "You are not a member of this check"})
        if instance.organizer == member:
            raise ValidationError({"info": "You can't leave this check (you are organizer)"})

        check_member.delete()

    class Meta:
        model = Check
        fields = '__all__'


class CheckListSerializer(BaseImageSerializer):
    """
    Сериализатор для счетов
    """
    total_amount = serializers.SerializerMethodField()

    def get_total_amount(self, object):
        total_amount_ = CheckRecord.objects.filter(check_obj=object).aggregate(Sum('amount'))['amount__sum']
        return total_amount_ if total_amount_ else 0.0

    class Meta:
        model = Check
        fields = '__all__'


class CheckRecordSerializer(BaseImageSerializer):
    """
    Сериализатор для записей счетов
    """

    def create(self, validated_data):
        member = self.context.get('member')
        check_obj = validated_data.get('check_obj')
        check_member = CheckMember.objects.filter(member=member, check_obj=check_obj)
        if not check_obj.active:
            raise ValidationError({"info": "Check closed"})
        if not check_member:
            raise PermissionDenied({"info": "Forbidden"})

        check_record = CheckRecord.objects.create(
            object=validated_data.get('object'),
            member=member,
            check_obj=validated_data.get('check_obj'),
            desc=validated_data.get('desc'),
            amount=validated_data.get('amount')
        )
        check_record.save()
        return check_record

    def update(self, instance: CheckRecord, validated_data):
        member = self.context.get('member')
        if instance.member != member and instance.check_obj.organizer != member:
            raise PermissionDenied({"info": "You can't edit this check record"})
        if not instance.check_obj.active:
            raise ValidationError({"info": "Check closed"})

        object = validated_data.get('object')
        desc = validated_data.get('desc')
        amount = validated_data.get('amount')

        instance.object = object if object else instance.object
        instance.desc = desc if desc else instance.desc
        instance.amount = amount if amount else instance.amount

        instance.save()
        return instance

    def remove(self, instance: CheckRecord):
        member = self.context.get('member')
        if instance.member != member and instance.check_obj.organizer != member:
            raise PermissionDenied({"info": "You can't delete this record"})
        if not instance.check_obj.active:
            raise ValidationError({"info": "Check closed"})
        instance.delete()

    class Meta:
        model = CheckRecord
        fields = '__all__'


class CheckRecordDetailSerializer(BaseImageSerializer):
    """
    Сериализатор для детального отображения записей счетов
    """
    member = MemberSerializer()
    check_obj = CheckListSerializer()

    class Meta:
        model = CheckRecord
        fields = '__all__'


class CheckRecordListSerializer(BaseImageSerializer):
    """
    Сериализатор для листингового отображения записей счетов
    """
    member = MemberSerializer()

    class Meta:
        model = CheckRecord
        fields = '__all__'


class DebtSerializer(BaseImageSerializer):
    """
    Сериализатор для долгов
    """
    from_member = MemberSerializer()
    to_member = MemberSerializer()
    check_obj = CheckListSerializer()

    class Meta:
        model = Debt
        fields = '__all__'
