# -*- coding: utf-8 -*-

import koji
import requests

from message_tagging_service.mts_config import mts_conf

koji_config = koji.get_profile_module(mts_conf['koji_profile']).config


def retrieve_modulemd_content(name, stream, version, context):
    """Retrieve and return modulemd.txt from Koji/Brew

    :param str name: module's name.
    :param str stream: module's stream.
    :param str version: module's version.
    :param str context: module's context.
    :return: modulemd content.
    :rtype: str
    """
    url = (f'{koji_config["topurl"]}/{name}/{stream}/{version}.{context}'
           f'/files/module/modulemd.txt')
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.content
