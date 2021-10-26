import os
import vk_api
import random

from poc.models import *

VK_SERVICE = os.environ.get('VK_SERVICE')
VK_OAUTH = os.environ.get('VK_OAUTH')
VK_GROUP_ID = os.environ.get('VK_GROUP_ID')


def get_name_by_id(user_id):
    vk_session = vk_api.VkApi(token=VK_SERVICE)
    vk = vk_session.get_api()
    t = vk.users.get(user_ids=(user_id,), lang='ru')[0]
    return t


def wall_post(message='TEST', copyright=None):
    vk_session = vk_api.VkApi(token=VK_OAUTH)
    vk = vk_session.get_api()

    vk.wall.post(owner_id=f'-{VK_GROUP_ID}', from_group=1, message=message, copyright=copyright)
