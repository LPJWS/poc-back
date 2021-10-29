import os
import vk_api
import random
import urllib.parse as urlparse
from urllib.parse import urlencode
from base64 import b64encode
from hashlib import sha256
from hmac import HMAC

from rest_framework.exceptions import PermissionDenied

from poc.models import *

VK_SERVICE = os.environ.get('VK_SERVICE')
VK_OAUTH = os.environ.get('VK_OAUTH')
VK_GROUP_ID = os.environ.get('VK_GROUP_ID')
VK_MINI_APP_SECRET=os.environ.get('VK_APP_SECRET')


def get_name_by_id(user_id):
    vk_session = vk_api.VkApi(token=VK_SERVICE)
    vk = vk_session.get_api()
    t = vk.users.get(user_ids=(user_id,), fields='photo_200', lang='ru')[0]
    return t


def wall_post(message='TEST', copyright=None):
    vk_session = vk_api.VkApi(token=VK_OAUTH)
    vk = vk_session.get_api()

    vk.wall.post(owner_id=f'-{VK_GROUP_ID}', from_group=1, message=message, copyright=copyright)


def verify(query, secret=VK_MINI_APP_SECRET):
    if not query.get("sign"):
        raise PermissionDenied({"info": "Forbidden"})
        return False
    vk_subset = sorted(
        filter(
            lambda key: key.startswith("vk_"), 
            query
        )
    )
    if not vk_subset:
        raise PermissionDenied({"info": "Forbidden"})
        return False
    ordered = {k: query[k] for k in vk_subset}
    hash_code = b64encode(
        HMAC(
            secret.encode(), 
            urlencode(ordered, doseq=True).encode(), 
            sha256
        ).digest()
    ).decode("utf-8")
    if hash_code[-1] == "=":
        hash_code = hash_code[:-1]
    fixed_hash = hash_code.replace('+', '-').replace('/', '_')

    if fixed_hash == query.get('sign'):
        vk_user_id = query.get('vk_user_id')
        try:
            member = Member.objects.get(vk_id=vk_user_id)
        except Member.DoesNotExist:
            member = Member.objects.create(vk_id=vk_user_id)
            vk_user_object = get_name_by_id(vk_user_id)
            name = f"{vk_user_object['first_name']} {vk_user_object['last_name']}"
            photo = vk_user_object['photo_200']
            member.name = name
            member.photo = photo
            member.save()
        return member
    else:
        raise PermissionDenied({"info": "Forbidden"})