# -*- coding: utf-8 -*-
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_v1_5
import sys
import json
import base64
import time
import string
import random
import urllib.parse
import hashlib


def mock_trace():
    """生成随机追踪码"""
    return random.choice(string.ascii_uppercase).replace("X", "Z") + \
        "-"+"".join(random.choice(string.ascii_letters + string.digits) for i in range(8)) + \
        "-"+"".join(random.choice(string.digits) for i in range(4)) + \
        "-"+"".join(random.choice(string.ascii_letters) for i in range(4)) + \
        "-"+"".join(random.choice(string.ascii_letters + string.digits) for i in range(11)) + \
        "-"+"".join(str(int(round(time.time() * 1000))))

def encrypt_password(pk, data, header):
    # 生成时间戳
    content = ""
    sign = b''
    timestamp = int(time.time()) * 1000
    data = json.loads(data)
    data["timestamp"] = timestamp
    # header参数
    new_header = json.loads(header)
    new_header["timestamp"] = timestamp
    new_header["trace"] = mock_trace()

    # 对入参进行排序
    new_data = dict(sorted(data.items()))
    for key, value in new_data.items():
        if isinstance(value, str) and value != "":
            content += key + "=" + str(value) + "&"
        if isinstance(value, int) and not isinstance(value, bool):
            content += key + "=" + str(value) + "&"
        if isinstance(value, float):
            content += key + "=" + str(value) + "&"
    content = content[:len(content)-1]
    content = "timestamp=" + str(timestamp) + "&" + content
    signature = hashlib.md5(content.encode(encoding='UTF-8')).hexdigest().upper()
    new_data["signature"] = signature
    # new_data_1 = json.dumps(new_data)
    new_data_2 = urllib.parse.quote(json.dumps(new_data))
    rsa_key = RSA.import_key(base64.b64decode(pk))  # 导入读取到的公钥
    cipher = PKCS1_v1_5.new(rsa_key)  # 生成对象
    n_n = len(new_data_2) // 100
    for i in range(n_n+1):
        if i == n_n:
            data_len = len(new_data_2) - i * 100
        else:
            data_len = 100
        part_data = new_data_2[0 + i*100: i*100 + data_len]
        encrypted_password = base64.b64encode(cipher.encrypt(part_data.encode(encoding="utf-8")))
        sign += bytes(",", 'utf-8') + encrypted_password
    json_data = {"data": sign[1:].decode()}
    print(json.dumps({"request_body": json_data, "request_headers": new_header}))
    return timestamp, json_data


if __name__ == '__main__':
    encrypt_password(sys.argv[1], sys.argv[2], sys.argv[3])
