"""用例编排层。

每个 service 对应一个或一组用例。只 import domain + ports,通过构造器
接收 Port 实现。这样测试时直接传 mock 实现即可。
"""
