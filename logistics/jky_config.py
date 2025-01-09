"""吉客云ERP配置"""

# 吉客云API配置
JKY_CONFIG = {
    'appkey': '30145708',  # 吉客云WMS appkey
    'url': 'https://qimen.api.taobao.com/router/qimen/service',  # API地址
    'secret': 'c6a0e1c6a9ef44a0a80eb834bd89e78d',  # 请替换为实际的secret
}

# 物流商编码映射
CARRIER_CODE_MAP = {
    'ZTO': 'zhongtong',  # 中通快递
    'STO': 'shentong',   # 申通快递
    'SF': 'shunfeng',    # 顺丰速运
} 