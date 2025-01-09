"""吉客云推送服务"""
import json
import hashlib
import logging
from datetime import datetime
from django.conf import settings
from ..jky_config import JKY_CONFIG
from .top import api

# 创建logger
logger = logging.getLogger('logistics.jky')

class JiKeYunService:
    """吉客云推送服务"""

    def __init__(self):
        self.appkey = JKY_CONFIG['appkey']
        self.secret = JKY_CONFIG['secret']
        self.url = JKY_CONFIG['url']

    def push_package(self, package):
        """推送包裹信息到吉客云"""
        try:
            logger.info(f"开始推送包裹信息到吉客云 - 包裹ID: {package.id}, 运单号: {package.tracking_no}")
            logger.info(f"包裹当前信息 - 物流商: {package.carrier_name}, 物流服务: {package.service_name}")
            
            # 准备请求参数
            request_data = {
                'request': {
                    'deliveryOrder': {
                        'orderCode': package.order.platform_order_number,  # 平台订单号
                        'warehouseCode': '0015',  # 仓库代码
                        'carrierCode': 'ZTO',  # 固定使用中通快递
                        'trackingNumber': package.tracking_no,  # 运单号
                        'packageInfo': {
                            'length': float(package.length) if package.length else 1,
                            'width': float(package.width) if package.width else 1,
                            'height': float(package.height) if package.height else 1,
                            'weight': float(package.weight) if package.weight else 1,
                            'volume': float(package.volume) if package.volume else 1,
                        }
                    }
                }
            }

            # 创建TOP API请求
            req = api.QimenDeliveryorderBatchcreateRequest(self.url)
            req.set_app_info(api.appinfo(self.appkey, self.secret))
            
            # 设置请求数据
            req.request = json.dumps(request_data)
            
            logger.debug(f"请求参数: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
            print(f"请求参数: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
            
            # 发送请求
            logger.info(f"发送请求到: {self.url}")
            try:
                response = req.getResponse()
                logger.debug(f"API响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
                print(f"API响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
                
                if response.get('code') == '0':
                    logger.info(f"推送成功 - 包裹ID: {package.id}")
                    return True, '推送成功', json.dumps(request_data, ensure_ascii=False, indent=2)
                else:
                    error_msg = response.get('message', '推送失败')
                    logger.error(f"推送失败 - 包裹ID: {package.id}, 错误信息: {error_msg}")
                    return False, f"推送失败: {error_msg}", json.dumps(request_data, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                logger.error(f"请求异常: {str(e)}")
                return False, f"请求异常: {str(e)}", json.dumps(request_data, ensure_ascii=False, indent=2)

        except Exception as e:
            error_msg = f"推送异常: {str(e)}"
            logger.error(f"未知异常 - 包裹ID: {package.id}, 错误: {str(e)}")
            return False, error_msg, json.dumps(request_data, ensure_ascii=False, indent=2) 