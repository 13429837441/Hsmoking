# -*- coding: utf-8 -*-

expr_1 = """
import json

count = 10
for index in range(count):
    print(json.dumps(index))
"""

expr_2 = """
import json

count = 20
for index in range(count):
    print(json.dumps(index))
"""

expr_3 = """
def test(abc):
    return abc
a = test(1)
print(a)
"""