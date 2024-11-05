#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    :TODO: http接口流量回放脚本。
    1、基于requests工具的扩展脚本功能作为回放端。
    BY JACK
"""
try:
    from .cli_global import GlobalMap
    from .cli_logger import Logger
except:
    from cli_global import GlobalMap
    from cli_logger import Logger
from jinja2 import Environment, PackageLoader
from flashtext import KeywordProcessor
from jsonpath_rw import parse
from deepdiff import DeepDiff
from requests import Session
import numpy as np
import subprocess
import requests
import re
import os
import csv
import sys
import time
import json
import copy


class Hooks:
    def __init__(self):
        self.before_request_funcs = {}
        self.after_request_funcs = {}

    def before_request(self, func):
        """
        注册 before_request 钩子函数
        """
        self.before_request_funcs[func.__name__] = func
        return func

    def after_request(self, func):
        """
        注册 after_request 钩子函数
        """
        self.after_request_funcs[func.__name__] = func
        return func

    def run_before_request_hooks(self, func_names, request, json_data):
        """
        执行 before_request 钩子函数
        """
        for func_name in func_names:
            if func_name in self.before_request_funcs:
                func = self.before_request_funcs[func_name]
                json_data = func(request, json_data)
        return json_data

    def run_after_request_hooks(self, func_names, request, json_data, response):
        """
        执行 after_request 钩子函数
        """
        for func_name in func_names:
            if func_name in self.after_request_funcs:
                func = self.after_request_funcs[func_name]
                response = func(request, json_data, response)
        return response


class MyEncoder(json.JSONEncoder):
    """
    重写JSONEncoder，兼容异常数据无法转换的情况
    :return:
    """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif obj.__class__.__name__ == "PrettyOrderedSet":
            list(obj)
        else:
            return super(MyEncoder, self).default(obj)


def get_dict_value(now_dict, target_key, results: list):
    """
    递归遍历获取指定KYE的VALUE值
    :return:
    """
    for key in now_dict.keys():
        data = now_dict[key]

        if isinstance(data, dict):
            get_dict_value(data, target_key, results=results)

        if key == target_key and not isinstance(data, dict):
            results.append(now_dict[key])

    return results


def set_dict_value(now_dict, target_key, value):
    """
    递归遍历修改指定KYE的VALUE值
    :return:
    """
    for key in now_dict.keys():
        data = now_dict[key]

        if isinstance(data, dict):
            set_dict_value(data, target_key, value)

        if key == target_key and not isinstance(data, dict):
            now_dict[key] = value

    return json.dumps(now_dict)


def batch_add_keywords(var_map):
    """
    全局变量分类合并
    :return:
    """
    keyword_dict = {}
    for key, val in var_map.items():
        if val in keyword_dict.keys():
            keyword_dict[val].append(f'{{{{{key}}}}}')
        else:
            keyword_dict[val] = [f'{{{{{key}}}}}']
    return keyword_dict


def replace_keyword(request: str):
    """
    过{{var}}方式替换变量值
    :return:
    """
    var_map = GlobalMap().map
    # 替换直接变量
    keyword_dict = batch_add_keywords(var_map)
    keyword_processor = KeywordProcessor()
    keyword_processor.add_keywords_from_dict(keyword_dict)
    new_request = keyword_processor.replace_keywords(request)
    return new_request


def replace_keywords(request):
    """
    过$.data.recodes[0].name方式替换变量值
    :return:
    """
    all_res = re.findall("{{(.+?)}}", request)
    if len(all_res) > 0:
        for res in all_res:
            group_res = re.findall("(\w+)\.?\[?", res)
            target_var = group_res[0]
            variable = get_variable_value(target_var, str(res).replace(target_var, "$"))
            request = str(request).replace(f"{{{{{res}}}}}", str(variable))
    return request


def get_variable_value(variable_name: str, target_key=""):
    """
    通过$.data.recodes[0].name方式取变量值
    :return:
    """
    g_map = GlobalMap()
    var_v = g_map.get(variable_name)
    try:
        if target_key != "":
            target_obj = parse(target_key)
            model = target_obj.find(json.loads(var_v))
            if len(model) > 0:
                return model[0].value
            else:
                return None
        else:
            return var_v
    except:
        return var_v


def set_variable_value(variable_name: str, target_key: str, body_dict: dict):
    """
    通过$.data.recodes[0].name方式取变量值
    然后保存变量值到全局变量
    :param: target_key ["$.data.recodes[0].name"]
    """
    g_map = GlobalMap()
    target_obj = parse(target_key)
    model = target_obj.find(body_dict)
    if len(model) > 0:
        var_v = model[0].value
    else:
        var_v = None
    g_map.set_map(variable_name, var_v)


def set_env_variable_values(root_path: str, env: str):
    """
        获取设置的环境变量
        然后保存变量值到全局变量
    """
    try:
        g_map = GlobalMap()
        env_path = os.path.join(root_path, "env_json.json")
        with open(env_path, 'r', encoding='utf-8') as f:
            funcs_all = json.load(f)
            param = funcs_all[env]["param"]
            for key, val in param.items():
                g_map.set_map(key, val)
        return funcs_all
    except Exception as e:
        print(str(e))
        return None


def set_variable_values(target_key: str, body_dict: dict):
    """
    通过$.data.recodes[0].name方式取变量值
    然后保存变量值到全局变量
    :param: target_key [{"token": "$.data.recodes[0].name"}]
    """
    try:
        g_map = GlobalMap()
        target_dict = json.loads(target_key)
        if isinstance(target_dict, dict):
            for key, val in target_dict.items():
                if str(val).find("$.") == 0:
                    target_obj = parse(val)
                    model = target_obj.find(body_dict)
                    if len(model) > 0:
                        var_v = model[0].value
                    else:
                        var_v = None
                    g_map.set_map(key, var_v)
                else:
                    g_map.set_map(key, val)
    except Exception as e:
        print(str(e))


def read_case(case_path):
    case_data = []
    csv.field_size_limit(500 * 1024 * 1024)
    csv_read = csv.reader(open(case_path))
    for index, item in enumerate(csv_read):
        if index != 0:
            case_data.append(item)
    return case_data


# 注册钩子函数
hooks = Hooks()


def req(url, method, **kwargs):
    """
    发送请求并返回响应对象
    """
    before_hooks = kwargs.pop('before_hooks', [])
    after_hooks = kwargs.pop('after_hooks', [])
    json_data = kwargs.pop('json', {})

    session = Session()
    request = requests.Request(method=method, url=url, data=None, **kwargs)
    prepared_request = session.prepare_request(request)
    json_data = hooks.run_before_request_hooks(before_hooks, prepared_request, json_data)
    # 删除请求头中的accept-encoding，避免返回压缩数据
    json_data["request_headers"].pop('accept-encoding', {})
    prepared_request.headers = json_data["request_headers"]
    prepared_request.body = json_data["request_body"]
    prepared_request.url = json_data["request_url"]
    response = session.send(prepared_request)
    response = hooks.run_after_request_hooks(after_hooks, prepared_request, json_data, response)

    return response


@hooks.before_request
def batch_replace_keywords(request, json_data):
    """
    批量替换关键字
    """
    request_headers = json_data["request_headers"]
    request_body = json_data["request_body"]
    var_map = GlobalMap().map
    # 替换直接变量
    keyword_dict = batch_add_keywords(var_map)
    keyword_processor = KeywordProcessor()
    keyword_processor.add_keywords_from_dict(keyword_dict)
    new_request_body = keyword_processor.replace_keywords(request_body)
    new_request_headers = keyword_processor.replace_keywords(request_headers)

    # 替换间接变量
    new_request_body = replace_keywords(new_request_body)
    new_request_headers = replace_keywords(new_request_headers)

    json_data["request_headers"] = eval(new_request_headers)
    json_data["request_body"] = new_request_body

    request.headers = eval(new_request_headers)
    if request.method == "GET":
        request.url = f'{request.url}{new_request_body}'
        json_data["request_url"] = request.url
    return json_data


@hooks.before_request
def add_authentication_headers(request, json_data):
    """
    头部信息添加token
    """
    res = json_data["res"]
    auto = json_data["auto"]
    token = json_data["token"]
    request_url = json_data["request_url"]
    request_headers = json_data["request_headers"]
    request_body = json_data["request_body"]
    # 获取token
    if auto == 0:  # 手动 xxx::header::accesstoken
        if token.split("::")[1] == "header":
            request_headers = set_dict_value(request_headers, token.split("::")[2], token.split("::")[0])
        if token.split("::")[1] == "body":
            request_headers = set_dict_value(request_body, token.split("::")[2], token.split("::")[0])
    else:  # 自动  login::data::header::accesstoken
        if len(res) > 0:
            if request_url[request_url.rindex("/") + 1:] != token.split("::")[0]:
                if token.split("::")[2] == "header":
                    request_headers = set_dict_value(request_headers, token.split("::")[3], res[0])
                if token.split("::")[2] == "body":
                    request_headers = set_dict_value(request_body, token.split("::")[3], res[0])

    request.headers = request_headers
    return json_data


@hooks.before_request
def run_pre_script(request, json_data):
    """
    执行前置外部脚本
    :: 以字典的形式保存全局变量，变量名为字典的key,变量值为字典的value
    :: request_body、request_headers变量名等于这两者则认为是修改消息体何消息头
    ::param:: [["python11", "sss_script.py", "{{public_key}}", "request_body"]]
    """
    g_map = GlobalMap()
    try:
        pre_script = json_data["pre_script"]
        script_path = os.path.join(json_data["path"], "package")
        if pre_script != "" and pre_script is not None:
            script_code = eval(pre_script)
            if isinstance(script_code, list):
                for script in script_code:
                    try:
                        if isinstance(script, list):
                            script[1] = os.path.join(script_path, script[1])
                            new_script = script[:2]
                            for var in script[2:]:
                                # 替换直接变量
                                keyword_dict = batch_add_keywords(g_map.map)
                                keyword_processor = KeywordProcessor()
                                keyword_processor.add_keywords_from_dict(keyword_dict)
                                new_var = keyword_processor.replace_keywords(var)
                                # 替换间接变量
                                new_var = replace_keywords(new_var)
                                if new_var == "request_body":
                                    new_script.append(json_data["request_body"])
                                elif new_var == "request_headers":
                                    new_script.append(json.dumps(json_data["request_headers"]))
                                else:
                                    new_script.append(new_var)
                            p = subprocess.Popen(new_script, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                            out = p.stdout.readlines()
                            for result in out:
                                try:
                                    result = str(result.replace(b"\r\n", b""), encoding="utf-8")
                                    if result != "" and result is not None:
                                        if isinstance(eval(result), dict):
                                            for key, val in eval(result).items():
                                                if key == "request_body":
                                                    json_data["request_body"] = json.dumps(val)
                                                elif key == "request_headers":
                                                    if isinstance(val, dict):
                                                        json_data["request_headers"] = val
                                                    else:
                                                        json_data["request_headers"] = json.loads(val)
                                                else:
                                                    g_map.set_map(key, val)
                                except Exception as e:
                                    continue
                    except Exception as e:
                        continue
    except Exception as e:
        g_map.set_map("Error", str(e))

    request_headers = json_data["request_headers"]
    request.headers = request_headers
    return json_data


@hooks.after_request
def run_post_script(request, json_data, response):
    """
    执行后置外部脚本
    :: 以字典的形式保存全局变量，变量名为字典的key,变量值为字典的value
    :: request_body、request_headers变量名等于这两者则认为是修改消息体何消息头
    """
    g_map = GlobalMap()
    try:
        post_script = json_data["post_script"]
        script_path = os.path.join(json_data["path"], "package")
        if post_script != "" and post_script is not None:
            script_code = eval(post_script)
            if isinstance(script_code, list):
                for script in script_code:
                    try:
                        if isinstance(script, list):
                            script[1] = os.path.join(script_path, script[1])
                            new_script = script[:2]
                            for var in script[2:]:
                                # 替换直接变量
                                keyword_dict = batch_add_keywords(g_map.map)
                                keyword_processor = KeywordProcessor()
                                keyword_processor.add_keywords_from_dict(keyword_dict)
                                new_var = keyword_processor.replace_keywords(var)
                                # 替换间接变量
                                new_var = replace_keywords(new_var)
                                if new_var == "request_body":
                                    new_script.append(json.dumps(request.data))
                                elif new_var == "request_headers":
                                    new_script.append(json.dumps(request.headers))
                                else:
                                    new_script.append(new_var)
                            p = subprocess.Popen(new_script, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                            out = p.stdout.readlines()
                            for result in out:
                                try:
                                    result = str(result.replace(b"\r\n", b""), encoding="utf-8")
                                    if result != "" and result is not None:
                                        if isinstance(eval(result), dict):
                                            for key, val in eval(result).items():
                                                if key == "response":
                                                    if isinstance(val, str):
                                                        response.text = val
                                                    else:
                                                        response.text = json.dumps(val)
                                                else:
                                                    g_map.set_map(key, val)
                                except:
                                    continue
                    except:
                        continue
    except Exception as e:
        g_map.set_map("Error", str(e))

    return response


def base_requests(current_path, module_name, case_name, case_path, sleep_time=500, auto=0, log=False, token='', env='', **kwargs):
    """
    基础请求
    :return:
    """
    scripts_code = set_env_variable_values(current_path, env)
    case_list = read_case(case_path)
    api_name_list = []
    api_time_list = []
    api_time_old_list = []
    run_code_list = []
    successes = 0
    failures = 0
    skipped = 0
    res = []
    console = Logger()
    if len(case_list) > 0:
        for case in case_list:
            time.sleep(int(sleep_time)/1000)
            is_pass = True
            is_run = case[0].upper()
            set_val = case[1]
            pre_processors = case[2]
            post_processors = case[3]
            request_url = replace_keyword(case[4])
            request_headers = case[5]
            request_body = case[6]
            request_method = case[7]
            old_response_data = case[9]
            old_response_time = case[10]
            if is_run == "TRUE":
                if set_val != "":  # 设置/读取全局变量
                    set_variable_values(set_val, {})
                # 前置钩子
                before_hooks = [
                    batch_replace_keywords.__name__,
                    add_authentication_headers.__name__,
                    run_pre_script.__name__
                ]
                # 后置钩子
                after_hooks = [
                    run_post_script.__name__
                ]
                # 请求参数
                json_data = {
                    "headers": eval(request_headers),
                    "json": {
                        "res": res,
                        "auto": auto,
                        "token": token,
                        "path": current_path,
                        "pre_script": pre_processors,
                        "post_script": post_processors,
                        "request_url": request_url,
                        "request_headers": request_headers,
                        "request_body": request_body
                    }
                }
                # GET请求
                if request_method == 'GET':
                    r = req(request_url, "GET", before_hooks=before_hooks, after_hooks=after_hooks, **json_data)
                    try:
                        now_response_data = r.json()
                    except:
                        now_response_data = {}
                    if auto == 1:  # 自动
                        if request_url[request_url.rindex("/")+1:] == token.split("::")[0]:
                            get_dict_value(now_response_data, token.split("::")[1], results=res)

                    if set_val != "":   # 设置/读取全局变量
                        set_variable_values(set_val, now_response_data)
                    # 是否打印日志
                    if log:
                        console.log('********************* Requests URL: {} *********************'.format(r.url))
                        console.log('Requests HEADER: {}'.format(r.request.headers))
                        console.log('Requests BODY: {}'.format(r.request.body))
                        console.log('Response TEXT: {}'.format(r.text))
                    # 接口返回结果差异对比
                    diff_data = DeepDiff(now_response_data, eval(old_response_data), ignore_order=True)  # diff 返回数据
                    case.append(json.dumps(eval(old_response_data), indent=4, ensure_ascii=False, cls=MyEncoder))
                    case.append(json.dumps(now_response_data, indent=4, ensure_ascii=False, cls=MyEncoder))
                    case.append(json.dumps(diff_data, indent=4, ensure_ascii=False, cls=MyEncoder))
                    api_name_list.append(r.url.split('?')[0])
                    api_time_list.append(round(r.elapsed.total_seconds(), 5))
                    api_time_old_list.append(old_response_time)
                    for key, val in kwargs.items():
                        if key in now_response_data.keys():
                            if now_response_data[key] != val:
                                is_pass = False
                    if r.status_code == 200 and is_pass:
                        successes = successes + 1
                        run_code_list.append(1)
                    else:
                        failures = failures + 1
                        run_code_list.append(0)
                # POST请求
                if request_method == 'POST':
                    r = req(request_url, "POST", before_hooks=before_hooks, after_hooks=after_hooks, **json_data)
                    try:
                        now_response_data = r.json()
                    except:
                        now_response_data = {}
                    if auto == 1:  # 自动
                        if request_url[request_url.rindex("/")+1:] == token.split("::")[0]:
                            get_dict_value(now_response_data, token.split("::")[1], results=res)

                    if set_val != "":   # 设置/读取全局变量
                        set_variable_values(set_val, now_response_data)
                    # 是否打印日志
                    if log:
                        console.log('********************* Requests URL: {} *********************'.format(r.url))
                        console.log('Requests HEADER: {}'.format(r.request.headers))
                        console.log('Requests BODY: {}'.format(r.request.body))
                        console.log('Response TEXT: {}'.format(r.text.replace("\n", "")))
                    # 接口返回结果差异对比
                    try:
                        diff_data = DeepDiff(now_response_data, eval(old_response_data), ignore_order=True)  # diff 返回数据
                        case.append(json.dumps(eval(old_response_data), indent=4, ensure_ascii=False, cls=MyEncoder))
                    except:
                        diff_data = DeepDiff(str(now_response_data), str(old_response_data), ignore_order=True)  # diff 返回数据
                        case.append(json.dumps(str(old_response_data), indent=4, ensure_ascii=False, cls=MyEncoder))
                    case.append(json.dumps(now_response_data, indent=4, ensure_ascii=False, cls=MyEncoder))
                    case.append(json.dumps(diff_data, indent=4, ensure_ascii=False, cls=MyEncoder))
                    api_name_list.append(r.url.split('?')[0])
                    api_time_list.append(round(r.elapsed.total_seconds(), 5))
                    api_time_old_list.append(old_response_time)
                    for key, val in kwargs.items():
                        if key in now_response_data.keys():
                            if now_response_data[key] != val:
                                is_pass = False
                    if r.status_code == 200 and is_pass:
                        successes = successes + 1
                        run_code_list.append(1)
                    else:
                        failures = failures + 1
                        run_code_list.append(0)
            else:
                run_code_list.append(-1)
        auto_path = os.path.join(current_path, 'auto_http')
        create_report(
            auto_path, module_name, case_name, case_list,
            api_name_list, api_time_list, api_time_old_list, run_code_list, successes, failures, skipped
        )


def schema_requests(schema_list, current_path, case_path, sleep_time=500, auto=0, log=False, token='', env='', **kwargs):
    """
    流程图定制请求
    :return:
    """
    try:
        scripts_code = set_env_variable_values(current_path, env)
        case_list = read_case(case_path)
        case_len = len(case_list)
        res = []
        console = Logger()
        new_case_list = []
        if len(case_list) > 0:
            for schema in schema_list:
                if len(schema) == 1 and "Interfaces" in schema:
                    b_case = eval(schema["Interfaces"].split("-")[0])
                    a_case = eval(schema["Interfaces"].split("-")[1])
                    if a_case > case_len:
                        a_case = case_len
                    if a_case < b_case or b_case <= 0 or a_case <= 0:
                        raise "Interfaces模块参数设置异常【{}】".format(schema["Interfaces"])
                    new_case_list += copy.deepcopy(case_list[b_case-1:a_case])
                if len(schema) == 2 and "Circulate" in schema and "Interfaces" in schema:
                    b_case = eval(schema["Interfaces"].split("-")[0])
                    a_case = eval(schema["Interfaces"].split("-")[1])
                    if a_case > case_len:
                        a_case = case_len
                    if a_case < b_case or b_case <= 0 or a_case <= 0:
                        raise "Interfaces模块参数设置异常【{}】".format(schema["Interfaces"])
                    circ = eval(schema["Circulate"])
                    if isinstance(circ, int):
                        for i in range(circ):
                            new_case_list += copy.deepcopy(case_list[b_case - 1:a_case])
                    if isinstance(circ, list):
                        for val in circ:
                            if isinstance(val, dict):
                                for case in case_list[b_case - 1:a_case]:
                                    if case[1] != "":
                                        var_dict = json.loads(case[1])
                                    else:
                                        var_dict = {}
                                    if isinstance(var_dict, dict):
                                        case[1] = json.dumps(dict(var_dict, **val))
                                    new_case_list.append(copy.deepcopy(case))
                if len(schema) == 1 and "End" in schema:
                    break
            for case in new_case_list:
                time.sleep(int(sleep_time)/1000)
                is_run = case[0].upper()
                set_val = case[1]
                pre_processors = case[2]
                post_processors = case[3]
                request_url = replace_keyword(case[4])
                request_headers = case[5]
                request_body = case[6]
                request_method = case[7]
                if is_run == "TRUE":
                    if set_val != "":  # 设置/读取全局变量
                        set_variable_values(set_val, {})
                    # 前置钩子
                    before_hooks = [
                        batch_replace_keywords.__name__,
                        add_authentication_headers.__name__,
                        run_pre_script.__name__
                    ]
                    # 后置钩子
                    after_hooks = [
                        run_post_script.__name__
                    ]
                    # 请求参数
                    json_data = {
                        "headers": eval(request_headers),
                        "json": {
                            "res": res,
                            "auto": auto,
                            "token": token,
                            "path": current_path,
                            "pre_script": pre_processors,
                            "post_script": post_processors,
                            "request_url": request_url,
                            "request_headers": request_headers,
                            "request_body": request_body
                        }
                    }
                    # GET请求
                    if request_method == 'GET':
                        r = req(request_url, "GET", before_hooks=before_hooks, after_hooks=after_hooks, **json_data)
                        try:
                            now_response_data = r.json()
                        except:
                            now_response_data = {}
                        if auto == 1:  # 自动
                            if request_url[request_url.rindex("/")+1:] == token.split("::")[0]:
                                get_dict_value(now_response_data, token.split("::")[1], results=res)

                        if set_val != "":   # 设置/读取全局变量
                            set_variable_values(set_val, now_response_data)
                        # 是否打印日志
                        if log:
                            console.log('********************* Requests URL: {} *********************'.format(r.url))
                            console.log('Requests HEADER: {}'.format(r.request.headers))
                            console.log('Requests BODY: {}'.format(r.request.body))
                            console.log('Response TEXT: {}'.format(r.text))
                    # POST请求
                    if request_method == 'POST':
                        r = req(request_url, "POST", before_hooks=before_hooks, after_hooks=after_hooks, **json_data)
                        try:
                            now_response_data = r.json()
                        except:
                            now_response_data = {}
                        if auto == 1:  # 自动
                            if request_url[request_url.rindex("/")+1:] == token.split("::")[0]:
                                get_dict_value(now_response_data, token.split("::")[1], results=res)

                        if set_val != "":   # 设置/读取全局变量
                            set_variable_values(set_val, now_response_data)
                        # 是否打印日志
                        if log:
                            console.log('********************* Requests URL: {} *********************'.format(r.url))
                            console.log('Requests HEADER: {}'.format(r.request.headers))
                            console.log('Requests BODY: {}'.format(r.request.body))
                            console.log('Response TEXT: {}'.format(r.text.replace("\n", "")))
    except Exception as e:
        raise e


def create_report(current_path, module_name, case_name, records, api_name_list, api_time_list, api_time_old_list, run_code_list, successes, failures, skipped):
    """
    生成测试报告
    :return:
    """
    report_folder = os.path.join(current_path, 'reports')
    if not os.path.exists(report_folder):
        os.makedirs(report_folder)
    report_path = os.path.join(report_folder, "CaseReport{}.html".format(case_name))
    try:
        env = Environment(loader=PackageLoader(module_name, 'templates'))
        template = env.get_template("template.html")
        html_content = template.render(html_report_name="接口测试报告",
                                       records=records,
                                       apiNameList=api_name_list,
                                       apiTimeList=api_time_list,
                                       apiTimeOldList=api_time_old_list,
                                       RunCodeList=run_code_list,
                                       successes=successes,
                                       failures=failures,
                                       skipped=skipped)
        with open(report_path, "wb") as f:
            f.write(html_content.encode("utf-8"))
    except Exception as e:
        print(e)


if __name__ == '__main__':
    # 报告保存路径
    currentPath = os.path.abspath(os.path.dirname(__file__))
    casePath = sys.argv[1]
    caseName = os.path.split(casePath)[1].split("_case")[0]
    moduleName = os.path.split(sys.argv[0])[1].replace(".py", "")
    base_requests(currentPath, moduleName, caseName, casePath)
    # set_variable_values('{"token": "$.data.token", "test": 123, "lang": {"data": [{"da1": "zh-CN"},{"da2": "en-US"},{"da3": "zh-HK"}]}}', {"data": {"token": 123456789}})
    # var = get_variable_value("target", "$.data[1].da2")
    # request_headers = """{'content-length': '70', 'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
    #  'accesstoken': '{{token}}', 'version': '0.0.1', 'sec-ch-ua-mobile': '?0', 'tz': 'GMT+8',
    #  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    #  'trace': 'dda71b0a-7201-4a6f-b6cb-f9ac92f75ced', 'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
    #  'accept': 'application/json', 'lang': '{{lang.data[0].da1}}',
    #  'captcha': '03AAYGu2S2rdJJz88VerOOdHhUTBy7JSZFlNrl457dKVSHqdoWP1k4Z_aDE46svU6TTgS6AQv5M7dmK665lkSg2ZfJ_ws22GKx34lpVBUGW_1QqdnXYMokw2_dWNvwo0KJ9I4SZRh3mNbaalJeQGTliZNk0P_IM-2snRoZ_ZCAm5acMbkKEYQMvZyFBxteUkwU4UyfKweHsO4aW4X1CMtnGb-cUx-1ohk5rnuSHSWktKpXjNXIrfWSbyjK5FaJcuAjM_NE6jS-FIaVSgUp4_t50-HvZNm2bbc6f4aOdmkdyLPq0ahyzD6ZByuL9ZtPcQqJY7RnOQl3jtp8DWTb4-M-WzpSSVOMDNLkngdF1aaNsmcR_kEPIXFS6oqpRMyamqZd68u3cbojcxEfPkDHooLZTHdbrXrwUmFzzuu6EQj47hOMJqKKk6hbF2Yri-lUpOoCGwRLxcdfw7ZUClDfRQCYzfEM_IAFd_WsCr1SBYDCmYO9skCjRRKttpQpx31LacOYGUbtuD9qVTm-conhOG3M-C9_ktk7ya1Lz5-_CbO_dtF12pQoe820ojvakBzaMnCwAdXGQlYU4gJ50IQNV_a2FdS7BbKcVX8_d5IL-j-kunEvOoxDEhEM2YSakb-sdvl9qrUtM28sDzpkdm-u38FgwL9yNOXMWASqbRg4l3D9d4Mp7ea8vnTQsMWpNtdujt_v40z4wOTelL1O8iuRqQBTJIARYxOJQ-5K6rQL8e_wcmIMZ0b4MASfwdbPsXYckcXYnIao7yxELsYbS2z7sA2LfVQOwimofkra7FSHEivQxIzEzODI1JkKKyN1haP3uqIDb4nwoxaKZFaiXNfzxq3IN01nVex5AnQjDh4jJ92u082IhFVQJ4eIyPkzQN-Z_oQ4fuETq2tQaAKQYoKxHTFMoWE1Q95pFKzBUMIM5EhKPwm8Tld-TyqlVr3I4C-sVpiKBepXT7sB_M_xrnC3roYQKoFrjKNHEuy_CgIdUzC7rpMv_-Cmjs-Grx8Vo8p5G9UAi45uWHaRZNYPwLdLQEadBoHGp4utrw-XqV-4xzLTPOtdqNi-Xm_T8ZVwfqqoICyxYKtIXV4JWmHGPyt8cMdMscwlgKvOlepP6cuuz7GIM-cCAamSy_eDkQUn5BchgBykJShQHJ6LCPQth8amVEuy-dfOCXEznAC6iQMwcimkNq1DjoS4ioHBeL9ecBPqi2SMHirtwEpv3yqadC3CZZeYXP7a6d6Had9ZrSg9kXMCL_GNi3iG3MzWkyCd8xrBD31yylUT40H-W9FNKJeUxXVpiOnsdE5VjP3UFe3K2bO39jQgMf5-V6KTSSzsjvUiCdJ6uI2tMSoq1oiP6tPU9MC9B_7lAZoXAL7v9pqVVILjgk9cckS9xwKdKtxA2M8gbbJlawn_qduleENcjH8D8rjqFMsA1JiTtX-mQmXb8yxPwZkBw00fWBz8oer6Oo4RpgmUokuy_XZf2N-rNcrnNR94h9ctH4PAUeQbLuokAIpGibdUPxWZPOgpoiMwJztcVNLqHEDjlNUq9DOp53_3kbChQtjih0ZUPAg4TnQ1FYEIn-0b5vHKv--P0KPXAyKEvSmWB4Z7LsZHQrf595HIFppGPiimbMLtE270KyQoE3tx3_ovOium4SahtfvY_zBtcpTRb4cW0NhX0t9yKcSLK6QGz9PXCP-uy8Il_TDuI1rDt62phsSa-N7i47-Ax8J3zM2aE6uAvIJko734',
    #  'sec-ch-ua-platform': '"Windows"', 'origin': 'https://pre-admin-14.cmfbl.com', 'sec-fetch-site': 'same-origin',
    #  'sec-fetch-mode': 'cors', 'sec-fetch-dest': 'empty', 'referer': 'https://pre-admin-14.cmfbl.com/user/login',
    #  'accept-encoding': 'gzip, deflate, br', 'accept-language': 'zh-CN,zh;q=0.9',
    #  'cookie': 'JSESSIONID=4688968C08CC722CFBD67CC5D6C6F354'}"""
    # g_map = GlobalMap().map
    # keyword_dict = batch_add_keywords(g_map)
    # keyword_processor = KeywordProcessor()
    # keyword_processor.add_keywords_from_dict(keyword_dict)
    # # new_request_body = keyword_processor.replace_keywords(request_body)
    # new_request_headers = keyword_processor.replace_keywords(request_headers)
