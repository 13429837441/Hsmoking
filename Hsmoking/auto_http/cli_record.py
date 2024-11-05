#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    :TODO: http接口流量录制脚本。
    1、基于mitmproxy的mitmdump工具的扩展脚本功能作为录制端。
    BY JACK
"""
try:
    from .cli_logger import Logger
except:
    from cli_logger import Logger
from configparser import ConfigParser
from urllib.parse import urlencode
from mitmproxy import http
from mitmproxy import ctx
import os
import time
import json
import csv

# 接口列表
http_list = list()

# 用例保存路径
currentPath = os.path.abspath(os.path.dirname(__file__))
currentTime = time.strftime("%Y%m%d%H%M%S", time.localtime())
savePath = os.path.join(currentPath, "case", currentTime + "_case.csv")

# 读取配置
conf = ConfigParser()
conf.read(os.path.join(os.path.split(currentPath)[0], 'config.ini'))
filtration_url = conf['proxy']['url']
filtration_type = conf['proxy']['type']
fiter_token = conf['proxy']['token']
fiter_log = conf['proxy']['log']
console = Logger()

if eval(fiter_log):
    console.log("******************** Save Case Path: {savePath} ********************".format(savePath=savePath))

with open(savePath, 'a+', newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(
        [
            "is_run",
            "set_variable",
            "pre_processors",
            "post_processors",
            "request_url",
            "request_headers",
            "request_body",
            "request_method",
            "status_code",
            "response_data",
            "response_time"
        ])


def request(flow):
    filtration = [url for url in filtration_url.split(",") if url in str(flow.request.pretty_url)]
    if len(filtration) > 0 and eval(fiter_log):
        if filtration_type in str(flow.request.method) or filtration_type == "ALL":
            console.log(flow.request.pretty_url)


def response(flow: http.HTTPFlow):
    # 加上过滤条件
    filtration = [url for url in filtration_url.split(",") if url in str(flow.request.pretty_url)]
    if len(filtration) > 0:
        pre_url = clear_url(str(flow.request.pretty_url))
        if filtration_type in str(flow.request.method) \
                or pre_url[pre_url.rindex("/")+1:] == fiter_token.split("::")[0] \
                or filtration_type == "ALL":
            if str(flow.request.pretty_url) not in http_list:
                http_list.append(str(flow.request.pretty_url))
                # 打开保存在本地的数据文件
                request_info = {'request_url': pre_url}
                data = json.loads(flow.response.content)
                request_info['is_run'] = "TRUE"
                request_info['set_variable'] = ""
                request_info['pre_processors'] = ""
                request_info['post_processors'] = ""
                request_info['request_headers'] = create_headers(flow.request.headers)
                if flow.request.method == "GET":
                    request_info['request_body'] = creat_query(flow.request.query)
                elif flow.request.method == "POST":
                    request_info['request_body'] = flow.request.get_text()
                else:
                    request_info['request_body'] = ""   # 暂时未处理
                request_info['request_method'] = flow.request.method
                request_info['status_code'] = flow.response.status_code
                request_info['reason'] = flow.response.reason
                request_info['response_data'] = data
                request_info['response_headers'] = create_headers(flow.response.headers)
                request_info['request_time_start'] = flow.request.timestamp_start
                request_info['request_time_end'] = flow.request.timestamp_end
                request_info['response_time_start'] = flow.response.timestamp_start
                request_info['response_time_end'] = flow.response.timestamp_end
                request_info['response_time'] = round(request_info['response_time_end'] - request_info['request_time_start'], 5)
                with open(savePath, 'a+', newline="") as csv_file:
                    write_obj = csv.writer(csv_file)
                    write_obj.writerow(
                        [
                            request_info['is_run'],
                            request_info['set_variable'],
                            request_info['pre_processors'],
                            request_info['post_processors'],
                            request_info['request_url'],
                            request_info['request_headers'],
                            request_info['request_body'],
                            request_info['request_method'],
                            request_info['status_code'],
                            request_info['response_data'],
                            request_info['response_time']
                        ])
                    ctx.log('********************** 写入数据成功 ********************** ')


def create_headers(headers):
    """
    组装请求头
    :param headers:
    :return:
    """
    headers_info = {}
    for k, v in headers.items():
        headers_info[k] = v
    return headers_info


def clear_url(url):
    """
    清理请求链接地址中带参数的情况
    :param url:
    :return:
    """
    return str(url).split("?")[0]


def creat_query(query):
    """
    组装请求链接地址中的参数
    :param query:
    :return:
    """
    new_list = urlencode(query)
    if new_list != "":
        new_query = f'?{new_list}'
    else:
        new_query = ''
    return new_query


def save_data(data, path):
    """
    保存数据
    :param data:
    :param path:
    :return:
    """
    header = list(data[0].keys())
    with open(path, 'a+', newline='', encoding="utf-8") as f:
        write_obj = csv.DictWriter(f, fieldnames=header)
        write_obj.writerows(data)
