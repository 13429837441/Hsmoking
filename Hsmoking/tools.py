#!/usr/bin/python
# -*- coding: utf-8 -*-
from dateutil.parser import parse
import csv
import os


class Tool(object):
    def __init__(self):
        pass

    @staticmethod
    def read_file(path, sep):
        try:
            files = os.listdir(path)
            case_list = []
            for filename in files:
                if not os.path.isdir(filename):
                    case = []
                    case_time, case_type = filename.split(sep)
                    case_style_time = str(parse(case_time))
                    case.append(case_style_time)
                    case.append(filename)
                    case_count = len(open(os.path.join(path, filename)).readlines())
                    if case_type.find(".csv") >= 0:
                        case_count -= 1
                    case.append(case_count)
                    case_list.append(case)
            return case_list
        except Exception as e:
            # print(e)
            return []

    @staticmethod
    def read_case(case_path):
        case_data = list()
        csv.field_size_limit(500 * 1024 * 1024)
        csv_read = csv.reader(open(case_path))
        for index, item in enumerate(csv_read):
            if index != 0:
                case_data.append(item)
        return case_data


# if __name__ == "__main__":
#     tl = Tool()
#     info = tl.read_case("D:\\IMRMToolsLibrary\\Hsmoking\\auto_http\\case\\20230716171918_case.csv")
#     print(info)
