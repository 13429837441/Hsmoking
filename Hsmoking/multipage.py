#!/usr/bin/python
# -*- coding: utf-8 -*-
import streamlit as st
"""
    :TODO: streamlit多页面方法重新。
    BY JACK
"""


class MultiApp(object):
    def __init__(self):
        self.apps = []
        self.app_dict = {}

    def add_app(self, title, func):
        if title not in self.apps:
            self.apps.append(title)
            self.app_dict[title] = func

    def run(self, label: str):
        title = st.sidebar.selectbox(
            label,
            self.apps,
            format_func=lambda title: str(title))
        self.app_dict[title]()
