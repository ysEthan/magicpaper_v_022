"""TOP API基础类"""
import json
import hashlib
import time
import requests
from urllib.parse import urlencode

class BaseRequest:
    def __init__(self, url):
        self.url = url
        self.app_key = None
        self.app_secret = None
        self.request = None

    def set_app_info(self, app_info):
        self.app_key = app_info.app_key
        self.app_secret = app_info.app_secret

    def _generate_sign(self, params):
        """生成签名"""
        # 按字典序排序参数
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        # 拼接参数
        sign_str = ''
        for k, v in sorted_params:
            if k != 'sign' and v:
                sign_str += f"{k}{v}"
        # 加密
        sign_str = self.app_secret + sign_str + self.app_secret
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()

    def getResponse(self):
        """发送请求并获取响应"""
        # 准备参数
        params = {
            'app_key': self.app_key,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'format': 'json',
            'v': '2.0',
            'sign_method': 'md5',
            'data': self.request
        }
        
        # 生成签名
        params['sign'] = self._generate_sign(params)
        
        # 发送请求
        response = requests.post(self.url, data=params)
        return response.json()

class QimenDeliveryorderBatchcreateRequest(BaseRequest):
    """奇门订单创建请求"""
    pass

def appinfo(app_key, app_secret):
    """创建应用信息对象"""
    class AppInfo:
        def __init__(self, key, secret):
            self.app_key = key
            self.app_secret = secret
    return AppInfo(app_key, app_secret) 