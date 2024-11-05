#!/usr/bin/python
# -*- coding: utf-8 -*-
"""接口录制与回放项目"""
import json

from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from streamlit_ace import st_ace, KEYBINDINGS, LANGUAGES, THEMES
from barfi import st_barfi, barfi_schemas, Block
from auto_http.cli_replay import *
import streamlit.components.v1 as components
from configparser import ConfigParser
from multipage import MultiApp
from pathlib import Path
import streamlit as st
from tools import Tool
from PIL import Image
import pandas as pd
import subprocess
import platform
import base64
import pickle
import shutil
import time
import ast
import os


def get_node_param(nodes, node_id):
    result = []
    for node in nodes:
        if node["interfaces"][0][1]["id"] == node_id:
            if node["type"] not in ["Begin", "End"]:
                result = [node["type"], node["name"], node["interfaces"][1][1]["id"]]
            else:
                result = [node["type"], node["name"], node["interfaces"][0][1]["id"]]
    return result


def get_connect_step(nodes, connections, begin_id, results: list):
    for connection in connections:
        if connection["from"] == begin_id:
            node_type, node_name, node_id = get_node_param(nodes, connection["to"])
            results.append({node_type: node_name})
            if node_type != "End":
                get_connect_step(nodes, connections, node_id, results=results)

    return results


def img_to_bytes(img_path):
    img_bytes = Path(os.path.split(os.path.realpath(__file__))[0] + "\\" + img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded


def pick_module(name):
    plugin_suffix = "py"
    if name.endswith(plugin_suffix):  # 检查文件名后缀是否是.py
        return name.split(".")[0]  # 后缀是.py 就提取文件名
    else:
        return ""  # 后缀不是.py 就把这项置空


def delete_schema(schema_name: str):
    try:
        with open('schemas.barfi', 'rb') as handle_read:
            schemas = pickle.load(handle_read)
    except FileNotFoundError:
        schemas = {}

    if schema_name in schemas:
        del schemas[schema_name]
    else:
        raise ValueError(
            f'Schema :{schema_name}: not found in the saved schemas')

    with open('schemas.barfi', 'wb') as handle_write:
        pickle.dump(schemas, handle_write, protocol=pickle.HIGHEST_PROTOCOL)


st.set_page_config(
    page_title='Cats Test Team',
    page_icon=':tm:',
    layout="wide",
    initial_sidebar_state="expanded",
)

pt = platform.system()
conf = ConfigParser()
main_path = os.path.split(os.path.realpath(__file__))[0]
config_path = os.path.join(os.path.split(os.path.realpath(__file__))[0], 'config.ini')
record_and_replay_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'auto_http')
package_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'package')


def session_init():
    if 'case_change' not in st.session_state:
        st.session_state.case_change = False
    if 'start_record' not in st.session_state:
        st.session_state.start_record = True
    if 'start_replay' not in st.session_state:
        st.session_state.start_replay = True
    if 'start_stream' not in st.session_state:
        st.session_state.start_stream = False
    if 'case_stream' not in st.session_state:
        st.session_state.case_stream = None
    if 'env_name' not in st.session_state:
        st.session_state.env_name = None
    if 'add_table' not in st.session_state:
        st.session_state.add_table = None
    if 'env_rows' not in st.session_state:
        st.session_state.env_rows = 1
    if 'pid' not in st.session_state:
        st.session_state.pid = 0


def css_init():
    st.markdown('''<style>
.edw49t12 {
    max-width: 500px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>''', unsafe_allow_html=True)


def main():
    if pt in ["Windows"]:
        session_init()  # session缓存初始化
        css_init()  # 前端css样式初始化
        html_init()  # 前端html布局初始化
    else:
        cs_404()
    return None


def cs_404():
    # 背景图片的网址
    img_url = 'https://img.zcool.cn/community/0156cb59439764a8012193a324fdaa.gif'

    # 修改背景样式
    st.markdown('''<span style="color: cyan"> ''' + f"不支持当前系统 {pt} 运行" + '''</span>''', unsafe_allow_html=True)
    st.markdown('''<style>.css-fg4pbf{background-image:url(''' + img_url + ''');
    background-size:100% 100%;background-attachment:fixed;}</style>''', unsafe_allow_html=True)


def html_init():
    app = MultiApp()
    app.st = st
    js_code = '''
    $(document).ready(function(){
        $("footer", window.parent.document).remove()
    });
    '''
    # 引用了JQuery v2.2.4
    components.html(f'''<script src="https://cdn.bootcdn.net/ajax/libs/jquery/2.2.4/jquery.min.js"></script>
        <script>{js_code}</script>''', width=0, height=0)
    # sidebar图标
    st.sidebar.markdown(
        '''<a href="#"><img src='data:image/png;base64,{}' class='img-fluid' width=80 height=80 target='_self'></a>'''.format(
            img_to_bytes("img/logomark_website.png")), unsafe_allow_html=True)
    # sidebar标题
    st.sidebar.header('自动化测试工具集')

    st.sidebar.subheader('1.HTTP接口录制回放')

    app.add_app("参数设置", case0)
    app.add_app("接口录制", case1)
    app.add_app("接口回放", case2)
    app.add_app("执行报告", case3)
    app.run("选择你想要的场景:")

    st.sidebar.markdown("---")

    st.sidebar.markdown('''<small style='float: right'>By <a id="reload" href="#">@Jack</a></small>''',
                        unsafe_allow_html=True)

    return None


########################################
#               参数设置                #
#######################################


def case0():
    try:
        type_list = ['GET', 'POST', 'ALL']
        # 读取配置
        conf.read(config_path)
        # 进度条
        my_bar = st.progress(0)
        for percent_complete in range(21):
            time.sleep(0.03)
            my_bar.progress(percent_complete * 5)
        # 标题
        st.title('参数配置')
        # 分列布局
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            proxy_url = st.text_input("1.过滤请求地址：", value=conf['proxy']['url'], key='lz_url')
            proxy_type = st.selectbox('2.过滤请求类型', type_list, index=type_list.index(conf['proxy']['type']))
            proxy_time = st.slider("3.接口回放间隔时间(ms)：", 0, 1000, int(conf['proxy']['time']), 100)
            proxy_check = st.text_input("4.接口返回结果检查：", value=conf['proxy']['check'], key='lz_check', help="输入json格式数据")
            proxy_auto = st.radio("5.选择接口TOKEN传入方式：", ("手动", "自动"), int(conf['proxy']['auto']))
            if proxy_auto == "手动":
                label = "6.请输入TOKEN："
            else:
                label = "6.请输入TOKEN获取方式："
            proxy_token = st.text_input(label,
                                        value=conf['proxy']['token'],
                                        help="例如：自动(login:data:header::Accesstoken 获取login接口返回的data字段赋值给header中的accesstoken); 手动(token:header::Accesstoken) 把token赋值给header中的accesstoken")
        # 打印日志
        proxy_log = st.checkbox("7.是否打印运行日志", value=eval(conf['proxy']['log']), key=None)

        with col3:
            # 保存配置
            if st.button('保存配置'):
                try:
                    if isinstance(eval(proxy_check), dict):
                        if proxy_auto == "手动":
                            conf['proxy'] = {
                                'url': proxy_url,
                                'type': proxy_type,
                                'time': proxy_time,
                                'check': proxy_check,
                                'auto': 0,
                                'token': proxy_token,
                                "log": proxy_log
                            }
                        else:
                            conf['proxy'] = {
                                'url': proxy_url,
                                'type': proxy_type,
                                'time': proxy_time,
                                'check': proxy_check,
                                'auto': 1,
                                'token': proxy_token,
                                "log": proxy_log
                            }
                        with open(config_path, 'w', encoding='utf-8') as f:
                            conf.write(f)
                        with st.spinner('保存中...'):
                            time.sleep(1)
                        st.balloons()
                    else:
                        st.error("【接口返回结果检查】输入数据只支持json格式数据")
                except:
                    st.error("【接口返回结果检查】输入数据只支持json格式数据")
    except Exception as e:
        st.exception(e)


########################################
#               接口录制                #
#######################################


def case1():
    tab1_1, tab2_1 = st.tabs(["自动", "手动"])
    with tab1_1:
        try:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.title('1.启动录制')
            with col2:
                col2_1, col2_2 = st.columns([1, 1])
                with col2_1:
                    if st.button('⏳开始录制'):
                        # st.write('STATR B= ', st.session_state.start_record)
                        if bool(st.session_state.start_record):
                            st.session_state.update({"start_record": False})
                            # st.write('STATR A= ', st.session_state.start_record)
                            cmd_path = os.path.join(main_path, "auto_http", "cli_record.py")
                            cmd = r"mitmdump -s {cmd_path}".format(cmd_path=cmd_path)
                            result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            if pt == 'Linux':
                                st.session_state.update({"pid": os.getpgid(result.pid)})
                                with st.spinner('开始录制中...'):
                                    time.sleep(2)
                            elif pt == 'Windows':
                                st.session_state.update({"pid": result.pid})
                                with st.spinner('开始录制中...'):
                                    time.sleep(2)
                            else:
                                st.error(f"不支持当前系统【{pt}】运行")
                            # while True:
                            #     record = result.stdout.readline().decode("GBK").encode("utf8").decode("utf8")
                            #     if record != "":
                            #         components.html(f'''<script>console.log({str(record)});</script>''', width=0, height=0)
                            #     time.sleep(1)
                        else:
                            st.warning("你已开启脚本录制功能，请不要重复开启")

                with col2_2:
                    if st.button('⌛停止录制'):
                        # st.write('STOP B= ', st.session_state.start_record)
                        if not bool(st.session_state.start_record):
                            st.session_state.update({"start_record": True})
                            # st.write('STOP A= ', st.session_state.start_record)
                            if pt == 'Linux':
                                os.killpg(st.session_state.pid, 9)
                                with st.spinner('正在结束录制...'):
                                    time.sleep(2)
                                st.balloons()
                            elif pt == 'Windows':
                                os.system('taskkill /t /f /pid {}'.format(st.session_state.pid))
                                # os.kill(st.session_state.pid, 9)
                                with st.spinner('正在结束录制...'):
                                    time.sleep(2)
                                st.balloons()
                            else:
                                st.error(f"不支持当前系统【{pt}】运行")
                        else:
                            st.warning("当前没有需要结束的录制线程")
        except Exception as e:
            st.session_state.update({"start_record": True})
            st.exception(e)

        code1 = '''mitmdump -p 8080
# -p指定监听8080端口
# 启动mitmdump开始录制接口'''
        st.code(code1, language='git')

        st.title('2.开启代理')
        with st.expander("开启谷歌浏览器代理方法👇"):
            st.markdown('''<small>注意：开启代理后点一下保存</small>''', unsafe_allow_html=True)
            image = Image.open(Path(main_path + "\\img\\chrome.png"))
            st.image(image)
        with st.expander("开启火狐浏览器代理方法👇"):
            image = Image.open(Path(main_path + "\\img\\firefox.png"))
            st.image(image)

        st.title('3.安装证书')
        st.text("已经安装过可跳过次步骤")
        with st.expander("安装抓包证书👇"):
            st.markdown('''<small>[证书下载地址](http://mitm.it/)</small>''', unsafe_allow_html=True)
            image = Image.open(Path(main_path + "\\img\\cer.png"))
            st.image(image)

        st.title('4.开始录制')
        code2 = '''谷歌：打开谷歌无痕窗口，访问目标地址
火狐：打开火狐隐私窗口，访问目标地址'''
        st.code(code2, language='git')
    with tab2_1:
        # 调用工具集
        tl = Tool()
        case_path = os.path.join(record_and_replay_path, "case")
        case_list = tl.read_file(case_path, "_case")
        file_list = [case[1] for case in case_list]
        file_list.sort(key=lambda x: str(x).split("_case")[0], reverse=True)
        file_list.insert(0, "请选择文件")
        file_name = st.selectbox(
            label='选择脚本文件',
            options=file_list,
            index=0,
            key='name',
            help='未选择则认为是新建文件，已选择则追加保存',
        )
        with st.form(key='excel', clear_on_submit=True):
            st.text_area(
                label='fetch格式数据',
                height=240,
                # max_chars=10000,
                key='notes',
                help='fetch脚本chrome的F12调试模式接口右键菜单点击复制"以fetch格式复制"或者"以fetch格式复制所有内容"',
                placeholder='输入fetch脚本',
            )
            st.form_submit_button(label='添加', on_click=on_form)

        if st.session_state.add_table is not None:
            st.table(st.session_state.add_table)
            if st.button('⌛保存'):
                new_add_table_list = []
                add_table_save = st.session_state.add_table
                add_table_list = add_table_save.values.tolist()
                for add_table_index in add_table_list:
                    new_add_table_list.append(["TRUE", "", "", ""] + add_table_index + ["200", "{}", 0.0])
                if file_name == "请选择文件":
                    # 用例保存路径
                    current_time = time.strftime("%Y%m%d%H%M%S", time.localtime())
                    save_path = os.path.join(record_and_replay_path, "case", current_time + "_case.csv")
                    with open(save_path, 'a+', newline="") as csvfile:
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
                            ]
                        )
                    with open(save_path, 'a+', newline="") as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerows(new_add_table_list)
                else:
                    save_path = os.path.join(record_and_replay_path, "case", file_name)
                    with open(save_path, 'a+', newline="") as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerows(new_add_table_list)
                st.session_state.add_table = None
                with st.spinner('保存中...'):
                    time.sleep(2)
                st.experimental_rerun()


def on_form():
    try:
        notes = st.session_state.notes
        if notes != "":
            if notes.count("fetch(") > 1:
                if notes[-2:] == ');':
                    notes = notes[:-2]
                request_list = notes.split('); ;')
                for req in request_list:
                    new_note = "@" + str(req).strip() + ");@"
                    request_url = json.loads(new_note.replace('@fetch(', '[').replace(');@', ']'))[0]
                    request_info = json.loads(new_note.replace('@fetch(', '[').replace(');@', ']'))[1]
                    request_header = request_info['headers']
                    request_body = request_info['body']
                    request_method = request_info['method']
                    new_add_table = st.session_state.add_table
                    if request_method == "GET":
                        if request_url.find('?') > 0:
                            request_url_list = request_url.split('?')
                            request_url = request_url_list[0]
                            request_body = "?" + request_url_list[1]
                        else:
                            request_body = ""
                    if new_add_table is None:
                        new_add_table = pd.DataFrame(
                            [[request_url, request_header, request_body, request_method]],
                            columns=('request_url', 'request_header', 'request_body', 'request_method'))
                    else:
                        new_add_table = pd.concat([new_add_table, pd.DataFrame(
                            [[request_url, request_header, request_body, request_method]],
                            columns=('request_url', 'request_header', 'request_body', 'request_method'))],
                                                  ignore_index=True)
                    st.session_state.add_table = new_add_table
            else:
                new_note = "@" + str(notes).strip() + "@"
                request_url = json.loads(new_note.replace('@fetch(', '[').replace(');@', ']'))[0]
                request_info = json.loads(new_note.replace('@fetch(', '[').replace(');@', ']'))[1]
                request_header = request_info['headers']
                request_body = request_info['body']
                request_method = request_info['method']
                new_add_table = st.session_state.add_table
                if request_method == "GET":
                    if request_url.find('?') > 0:
                        request_url_list = request_url.split('?')
                        request_url = request_url_list[0]
                        request_body = "?" + request_url_list[1]
                    else:
                        request_body = ""
                if new_add_table is None:
                    new_add_table = pd.DataFrame([[request_url, request_header, request_body, request_method]],
                                                 columns=('request_url', 'request_header', 'request_body', 'request_method'))
                else:
                    new_add_table = pd.concat([new_add_table, pd.DataFrame(
                        [[request_url, request_header, request_body, request_method]],
                        columns=('request_url', 'request_header', 'request_body', 'request_method'))], ignore_index=True)
                st.session_state.add_table = new_add_table
    except Exception as e:
        placeholder = st.empty()
        placeholder.error("fetch文件格式错误！！！")
        time.sleep(2)
        placeholder.empty()

########################################
#               接口回放                #
#######################################


def case2():
    try:
        # 读取配置
        conf.read(config_path)
        # 调用工具集
        tl = Tool()
        case_path = os.path.join(record_and_replay_path, "case")
        env_path = os.path.join(main_path, "env_json.json")
        case_list = tl.read_file(case_path, "_case")
        file_list = [case[1] for case in case_list]
        file_list.sort(key=lambda x: str(x).split("_case")[0], reverse=True)
        file_list.insert(0, "选择回放文件")
        tab1_1, tab2_1, tab3_1 = st.tabs(["环境", "回放", "流程"])
        with tab1_1:
            func_list = []
            func_dict = {}
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    funcs_all = json.load(f)
            except:
                funcs_all = {}
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col1:
                if st.session_state.env_name is not None:
                    pre_env = st.session_state.env_name
                else:
                    pre_env = conf['env']['pre_env']
                if pre_env and pre_env in funcs_all:
                    env_name = st.selectbox("请选择环境配置：",
                                            options=funcs_all.keys(),
                                            index=list(funcs_all.keys()).index(pre_env)
                                            )
                else:
                    env_name = st.text_input(label="请输入环境配置：", key="env")
            with col4:
                save = st.button("保存配置")

            st.markdown("---")
            st.markdown("* 环境变量")
            add = st.button(label="➕", help="添加环境变量")
            if add:
                st.session_state.env_rows += 1
                st.session_state.env_name = pre_env
                st.experimental_rerun()

            if env_name in funcs_all:
                env_param_dict = funcs_all[env_name]["param"]
                env_param_list = list(funcs_all[env_name]["param"].keys())
                env_funcs_list = list(funcs_all[env_name].keys())
                env_funcs_list.remove("param")
                if st.session_state.env_name is None:
                    st.session_state.env_rows = len(env_param_list)
            else:
                env_param_dict = None
                env_param_list = None
                env_funcs_list = []

            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            env_key_list = []
            env_value_list = []
            for i in range(st.session_state.env_rows):
                if i % 2 == 0:
                    with col1:
                        if env_param_dict is not None and i < len(env_param_list):
                            env_key = st.text_input(label="变量名{}：".format(str(i + 1)),
                                                    key="key" + str(i),
                                                    value=env_param_list[i]
                                                    )
                        else:
                            env_key = st.text_input(label="变量名{}：".format(str(i + 1)),
                                                    key="key" + str(i)
                                                    )
                        if env_key:
                            env_key_list.append(env_key)
                    with col2:
                        if env_param_dict is not None and i < len(env_param_list):
                            env_param = st.text_input(label="变量值{}：".format(str(i + 1)),
                                                      key="value" + str(i),
                                                      value=env_param_dict[env_param_list[i]]
                                                      )
                        else:
                            env_param = st.text_input(label="变量值{}：".format(str(i + 1)),
                                                      key="value" + str(i)
                                                      )
                        if env_param:
                            env_value_list.append(env_param)
                else:
                    with col3:
                        if env_param_dict is not None and i < len(env_param_list):
                            env_key = st.text_input(label="变量名{}：".format(str(i + 1)),
                                                    key="key" + str(i),
                                                    value=env_param_list[i]
                                                    )
                        else:
                            env_key = st.text_input(label="变量名{}：".format(str(i + 1)),
                                                    key="key" + str(i)
                                                    )
                        if env_key:
                            env_key_list.append(env_key)
                    with col4:
                        if env_param_dict is not None and i < len(env_param_list):
                            env_param = st.text_input(label="变量值{}：".format(str(i + 1)),
                                                      key="value" + str(i),
                                                      value=env_param_dict[env_param_list[i]]
                                                      )
                        else:
                            env_param = st.text_input(label="变量值{}：".format(str(i + 1)),
                                                      key="value" + str(i)
                                                      )
                        if env_param:
                            env_value_list.append(env_param)

            # st.markdown("---")
            # st.markdown("* 外部脚本")
            # things_in_plugin_dir = os.listdir(package_path)
            # files_in_plugin_dir = map(pick_module, things_in_plugin_dir)  # 挑选出.py 为后缀的文件
            # # 去除列表中的空值
            # files_in_plugin_dir = [_ for _ in files_in_plugin_dir if _ != "" and _ != "__init__"]
            #
            # # 已配置的插件列表
            # if env_funcs_list is not None:
            #     pack_list = [val.split("@")[0] for val in env_funcs_list]
            # else:
            #     pack_list = []
            #
            # packs = st.multiselect("请选择插件【多选】：", files_in_plugin_dir, default=pack_list)
            # if packs:
            #     for filename in packs:
            #         func_path = os.path.join(package_path, filename + ".py")
            #         with open(func_path, 'r') as fp:
            #             data = fp.readlines()
            #             data = ''.join(data)
            #             tree = ast.parse(data)
            #             for node in ast.walk(tree):
            #                 if isinstance(node, ast.Assign):
            #                     func_name = node.targets[0].__dict__["id"]
            #                     func_list.append(filename + "@" + func_name)
            #                     func_dict[filename + "@" + func_name] = node.value.__dict__["value"] \
            #                         if "value" in node.value.__dict__ else node.value.__dict__["s"]
            #
            # funcs = st.multiselect("请选择功能【多选】：", func_list, default=env_funcs_list)
            funcs_choice = {}
            # if funcs:
            #     for func in funcs:
            #         if func in func_dict:
            #             funcs_choice[func] = func_dict[func]
            # else:
            #     funcs_choice = func_dict
            if save:
                funcs_choice["param"] = dict(zip(env_key_list, env_value_list))
                funcs_all[env_name] = funcs_choice
                with open(env_path, 'w') as write_f:
                    json.dump(funcs_all, write_f, indent=4, ensure_ascii=False)
                with open(config_path, 'w', encoding='utf-8') as f:
                    conf['env'] = {"pre_env": env_name}
                    conf.write(f)
                st.session_state.env_name = None
                st.experimental_rerun()

        with tab2_1:
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col1:
                file_name = st.selectbox("请选择回放用例：", file_list, on_change=on_select_box_change,
                                         help='pre_processors（前置脚本）:例：[["python11", "sss_script.py", "{{public_key}}", "request_body"]]'
                                        '\npost_processors（后置脚本）:例：[["python11", "sss_script.py", "{{public_key}}", "request_body"]]'
                                              '\nis_run（是否执行）:例：TRUE[执行]、FALSE[不执行]'
                                              '\nset_variable（设置变量）:例：{{var}}、$.data.[0].code')
                if file_name == "选择回放文件":
                    st.session_state.update({"case_change": False})
                else:
                    st.session_state.update({"case_change": True})
            with col4:
                try:
                    if st.button("🧭回放接口"):
                        if file_name != "选择回放文件":
                            if bool(st.session_state.start_replay):
                                st.session_state.update({"start_replay": False})
                                with st.spinner('正在回放脚本...'):
                                    re_current_path = record_and_replay_path
                                    re_case_path = os.path.join(re_current_path, 'case', file_name)
                                    re_case_name = str(file_name).split("_case")[0]
                                    re_module_name = "auto_http"
                                    # 开始回放
                                    base_requests(
                                        main_path,
                                        re_module_name,
                                        re_case_name,
                                        re_case_path,
                                        sleep_time=conf["proxy"]["time"],
                                        auto=int(conf["proxy"]["auto"]),
                                        log=eval(conf["proxy"]["log"]),
                                        token=conf["proxy"]["token"],
                                        env=conf["env"]["pre_env"],
                                        **eval(conf["proxy"]["check"])
                                    )
                                    # 生成报告
                                    re_report_name = f"CaseReport{re_case_name}.html"
                                    re_file_path = os.path.join("auto_http", "reports", re_report_name)
                                    text = img_to_bytes(re_file_path)
                                    st.markdown(
                                        f'''<a href="data:application/octet-stream;base64,{text}" 
                                        download="{os.path.basename(re_file_path)}" target="_self">点击下载 {re_report_name}</a>''',
                                        unsafe_allow_html=True
                                    )
                                    st.session_state.update({"start_replay": True})
                            else:
                                st.warning("你已执行脚本回放功能，请耐心等待")
                        else:
                            st.warning("请先选中需要回放的文件")
                except Exception as e:
                    st.session_state.update({"start_replay": True})
                    st.exception(e)
            if not bool(st.session_state.case_change):
                if case_list is None:
                    st.write("文件名称必须满足以下条件：【^%Y%m%d%H%M%S_case(.*).csv$】")
                else:
                    df = pd.DataFrame(
                        case_list,
                        columns=[
                            "录制日期",
                            "录制脚本名称",
                            "录制接口数量"
                        ]
                    )
                    st.table(df)
            else:
                tab1_1_1, tab1_1_2 = st.tabs(["用例", "编辑"])
                with tab1_1_1:
                    data_converters = {
                        "is_run": str,
                        "set_variable": str,
                        "pre_processors": str,
                        "post_processors": str,
                        "request_headers": str,
                        "request_body": str,
                        "request_method": str,
                        "status_code": str,
                        "response_time": float,
                    }
                    df = pd.read_csv(os.path.join(case_path, file_name), encoding='gb18030', converters=data_converters)
                    with st.form("my_form"):
                        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 3])
                        with col1:
                            submitted = st.form_submit_button("提交更新")
                        with col2:
                            submitted_del = st.form_submit_button("删除选中行")
                        gb = GridOptionsBuilder.from_dataframe(df)
                        selection_mode = 'multiple'
                        enable_enterprise_modules = True
                        return_mode_value = DataReturnMode.FILTERED
                        gb.configure_selection(selection_mode,
                                               use_checkbox=True,
                                               header_checkbox=True
                                               )
                        gb.configure_side_bar()
                        # 分页设置
                        # gb.configure_pagination(paginationAutoPageSize=False)
                        gb.configure_column('is_run',
                                            pinned='left',
                                            width=120,
                                            editable=True,
                                            rowDrag=True,
                                            sortable=False,
                                            cellEditor='agRichSelectCellEditor',
                                            cellEditorParams={'values': ['TRUE', 'FALSE']}
                                            )
                        gb.configure_column('set_variable', pinned='right', width=300, editable=True)
                        gb.configure_column('pre_processors', width=100, editable=True)
                        gb.configure_column('post_processors', width=100, editable=True)
                        gb.configure_column('request_headers', editable=True)
                        gb.configure_column('request_body', editable=True)
                        gb.configure_column('request_method', width=80)
                        gb.configure_column('status_code', width=80)
                        gb.configure_column('response_time', width=80)
                        gb.configure_default_column(sortable=True, filterable=True)
                        gb.configure_grid_options(domLayout='normal', animateRows=True, rowDragManaged=True, rowDragMultiRow=True)
                        grid_options = gb.build()
                        update_mode_value = GridUpdateMode.MODEL_CHANGED
                        new_df = AgGrid(df,
                                        gridOptions=grid_options,
                                        data_return_mode=return_mode_value,
                                        update_mode=update_mode_value,
                                        enable_enterprise_modules=enable_enterprise_modules,
                                        editable=True,
                                        pagination=True,
                                        # paginationAutoPageSize=True,
                                        # suppressPaginationPanel=True,
                                        # paginationPageSize=10
                        )
                        if submitted:
                            with st.spinner('正在保存中...'):    # 选中的行
                                select_index = [new_df.selected_rows[index]["_selectedRowNodeInfo"]["nodeRowIndex"] for
                                                index in
                                                range(len(new_df.selected_rows))]
                                for index in range(len(new_df.data["is_run"])):
                                    if index in select_index:
                                        new_df.data["is_run"][index] = "TRUE"
                                new_df.data.to_csv(os.path.join(case_path, file_name), mode='w', index=False,
                                                   encoding='gb18030')
                                time.sleep(1)
                                st.experimental_rerun()
                        if submitted_del:
                            with st.spinner('正在删除中...'):
                                select_index = [new_df.selected_rows[index]["_selectedRowNodeInfo"]["nodeRowIndex"] for
                                                index in
                                                range(len(new_df.selected_rows))]
                                new_df = new_df.data.drop(select_index)
                                new_df.to_csv(os.path.join(case_path, file_name), mode='w', index=False,
                                              encoding='gb18030')
                                time.sleep(1)
                                st.experimental_rerun()
                with tab1_1_2:
                    c1, c2 = st.columns([3, 1])
                    # c2.text("Parameters")
                    with c1:
                        content = st_ace(
                            placeholder="Write your code here",
                            language=c2.selectbox("Language mode", options=LANGUAGES, index=121),
                            theme=c2.selectbox("Theme", options=THEMES, index=10),
                            keybinding=c2.selectbox("Keybinding mode", options=KEYBINDINGS, index=3),
                            font_size=c2.slider("Font size", 5, 24, 14),
                            tab_size=c2.slider("Tab size", 1, 8, 4),
                            show_gutter=c2.checkbox("Show gutter", value=True),
                            auto_update=c2.checkbox("Auto update", value=True),
                            show_print_margin=c2.checkbox("Show print margin", value=False),
                            wrap=c2.checkbox("Wrap enabled", value=False),
                            readonly=c2.checkbox("Read-only", value=False),
                            min_lines=45,
                            key="ace",
                        )
        with tab3_1:
            begin = Block(name='Begin')
            begin.add_output("Start")

            def begin_func(self):
                self.get_interface(name='Start')

            begin.add_compute(begin_func)

            feeds = Block(name='Interfaces')
            feeds.add_input("Input")
            feeds.add_output("Output")

            def feeds_func(self):
                self.set_interface(name='Output', value=2)

            feeds.add_compute(feeds_func)

            circulate = Block(name='Circulate')
            circulate.add_input("For in")
            circulate.add_output("For out")

            def circulate_func(self):
                self.get_interface(name='For in')
                self.set_interface(name='For out', value=3)

            circulate.add_compute(circulate_func)

            splitter = Block(name='Splitter')
            splitter.add_input()
            splitter.add_output()
            splitter.add_output()

            def splitter_func(self):
                self.get_interface(name='Input 1')
                self.set_interface(name='Output 1', value=4)
                self.set_interface(name='Output 2', value=4)

            splitter.add_compute(splitter_func)

            mixer = Block(name='Mixer')
            mixer.add_input()
            mixer.add_input()
            mixer.add_output()

            def mixer_func(self):
                self.get_interface(name='Input 1')
                self.get_interface(name='Input 2')
                self.set_interface(name='Output 1', value=5)

            mixer.add_compute(mixer_func)

            end = Block(name='End')
            end.add_input("Terminal")

            def end_func(self):
                self.get_interface(name='Terminal')

            end.add_compute(end_func)

            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col1:
                load_schema = st.selectbox('选择已保存的流程:', barfi_schemas(),
                                           help="流程保存名称与用例名称相同；例如：20230731224859_case_额度调整.csv")
            with col3:
                if st.button("🎞执行流程"):
                    if bool(st.session_state.start_stream):
                        st.session_state.update({"start_stream": False})
                        re_current_path = record_and_replay_path
                        load_schema_name = load_schema.split(".csv")[0] + ".csv"
                        re_cases_path = os.path.join(re_current_path, 'case', load_schema_name)
                        if os.path.exists(re_cases_path):
                            new_case_stream = st.session_state.case_stream
                            if len(new_case_stream) > 0:
                                with st.spinner('正在执行流程...'):
                                    schema_requests(
                                        new_case_stream,
                                        main_path,
                                        re_cases_path,
                                        sleep_time=conf["proxy"]["time"],
                                        auto=int(conf["proxy"]["auto"]),
                                        log=eval(conf["proxy"]["log"]),
                                        token=conf["proxy"]["token"],
                                        env=conf["env"]["pre_env"]
                                    )
                                    time.sleep(1)
                                    st.experimental_rerun()
                            else:
                                st.warning("流程异常，无有效的流程可执行！")
                        else:
                            st.warning("流程异常，该流程名称与用例名称不匹配！")
                    else:
                        st.warning("请先执行流程图，👇点击左上角【Execute】")
            with col4:
                try:
                    if st.button("🗑删除流程"):
                        if load_schema != "":
                            delete_schema(load_schema)
                            with st.spinner('正在删除中...'):
                                time.sleep(1)
                                st.experimental_rerun()
                        else:
                            st.warning("请先选择需要删除的流程！")
                except Exception as e:
                    st.exception(e)

            # compute_engine = st.checkbox('Activate barfi compute engine', value=False)

            barfi_result = st_barfi(base_blocks=[begin, feeds, circulate, end],
                                    compute_engine=False, load_schema=load_schema)

            if barfi_result:
                try:
                    begin_id = None
                    results = []
                    new_results = []
                    nodes = barfi_result["editor_state"]["nodes"]
                    connections = barfi_result["editor_state"]["connections"]
                    type_list = [node["type"] for node in nodes]
                    if type_list.count("Begin") != 1: raise Exception("流程异常，流程中开始模块异常！")
                    if type_list.count("End") != 1: raise Exception("流程异常，流程中结束模块异常！")
                    if type_list.count("Interfaces") == 0: raise Exception("流程异常，流程中缺少接口模块！")
                    if len(connections) == 0: raise Exception("流程异常，流程没有形成完整闭环！")
                    for node in nodes:
                        if node["type"] == "Begin":
                            begin_id = node["interfaces"][0][1]["id"]
                    get_connect_step(nodes, connections, begin_id, results)
                    if len(results) == 0: raise Exception("流程异常，流程没有形成完整闭环！")
                    if len([res for res in results if "End" in res]) == 0: raise Exception("流程异常，流程没有形成完整闭环！")
                    pre_node = [results[index - 1] for index, res in enumerate(results) if "Circulate" in res]
                    interfaces_list = [node for node in pre_node if "Interfaces" not in node]
                    if len(interfaces_list) > 0: raise Exception("流程异常，接口模块必须位于循环模块前面！")
                    if len(
                            [inter for inter in interfaces_list if
                             inter["Interfaces"].find("-") < 0]) > 0: raise Exception(
                        "流程异常，接口模块中接口编号必须是一个范围；例:1-10")
                    for index, res in enumerate(results):
                        if "Circulate" in res:
                            new_results.pop(-1)
                            new_results.append(dict(res, **results[index - 1]))
                        else:
                            new_results.append(res)
                    st.session_state.update({"start_stream": True})
                    st.session_state.update({"case_stream": new_results})
                except Exception as e:
                    st.exception(e)
    except Exception as e:
        st.exception(e)


def on_select_box_change():
    st.session_state.update({"case_change": True})


def case3():
    try:
        report_path = os.path.join(record_and_replay_path, "reports")
        files = os.listdir(report_path)
        files.sort(key=lambda x: str(x).replace("CaseReport", "").replace(".html", ""), reverse=True)
        if len(files) > 10:
            st.warning(f"历史文件过多，请注意及时清理哦！路径：{report_path}")
        for file in files:
            file_path = os.path.join("auto_http", "reports", file)
            text = img_to_bytes(file_path)
            st.markdown(
                f'''<a href="data:application/octet-stream;base64,{text}" download="{os.path.basename(file_path)}" target="_self">点击下载 {file}</a>''',
                unsafe_allow_html=True)
    except Exception as e:
        st.exception(e)


if __name__ == '__main__':
    main()
