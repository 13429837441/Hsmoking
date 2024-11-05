#!/usr/bin/python
# -*- coding: utf-8 -*-
import json


class GlobalMap(object):
    """
    局部变量的保存与获取
    :return:
    """
    map = {}

    def set_map(self, key, value):
        if not isinstance(value, str):
            value = json.dumps(value)
        self.map[key] = value

    def set(self, **keys):
        try:
            for key_, value_ in keys.items():
                self.map[key_] = str(value_)
        except BaseException as msg:
            raise msg

    def del_map(self, key):
        try:
            del self.map[key]
            return self.map
        except KeyError:
            raise "key:'" + str(key) + "'  不存在"

    def get(self, *args):
        try:
            dic = None
            for key in args:
                if len(args) == 1:
                    dic = self.map[key]
                elif len(args) == 1 and args[0] == 'all':
                    dic = self.map
                else:
                    dic[key] = self.map[key]
            return dic
        except KeyError:
            return None
