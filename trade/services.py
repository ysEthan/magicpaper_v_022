import time
import hashlib
import json
import math
import requests
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Order, Shop, Cart
from gallery.models import SKU
from storage.models import Warehouse
from logistics.models import Service, Package, Tracking

# 获取logger实例
logger = logging.getLogger(__name__)

class WDTOrderSync:
    """旺店通订单同步服务"""
    
    # 包裹状态映射
    PACKAGE_STATUS_MAP = {
        'unpaid': '0',    # 待发货
        'pending': '0',    # 待发货
        'picking': '1',    # 待揽收
        'shipped': '2',    # 转运中
        'delivered': '3',  # 已签收
        'cancelled': '4',  # 已取消
    }
    
    def __init__(self):
        self.base_url = "https://openapi.qizhishangke.com/api/openservices/trade/v1"
        self.app_name = "mathmagic"
        self.app_key = "82be0592545283da00744b489f758f99"
        self.sid = "mathmagic"
        self._default_service = None

    def _get_default_service(self):
        """获取默认物流服务"""
        if not self._default_service:
            # 尝试获取第一个可用的物流服务
            self._default_service = Service.objects.first()
            if not self._default_service:
                # 如果没有物流服务，记录错误
                logger.error("No logistics service available in the system")
        return self._default_service

    def _get_service_by_name(self, service_name):
        """根据物流服务名称获取服务对象"""
        if not service_name:
            return None
        
        try:
            # 尝试根据服务名称查找服务
            service = Service.objects.filter(service_name__icontains=service_name).first()
            if service:
                return service
            else:
                logger.warning(f"找不到匹配的物流服务: {service_name}")
                return None
        except Exception as e:
            logger.error(f"查找物流服务失败: {str(e)}")
            return None

    def generate_sign(self, body):
        """生成API签名"""
        headers = {
            'Content-Type': 'application/json'
        }

        timestamp = str(int(time.time()))
        sign_str = "{appKey}appName{appName}body{body}sid{sid}timestamp{timestamp}{appKey}".format(
            appKey=self.app_key,
            appName=self.app_name,
            body=body,
            sid=self.sid,
            timestamp=timestamp
        )
        sign = hashlib.md5(sign_str.encode()).hexdigest()
        
        params = {
            "appName": self.app_name,
            "sid": self.sid,
            "sign": sign,
            "timestamp": timestamp,
        }
        return params, headers

    def get_trade_list(self, start_date='2025-01-01 00:00:00', end_date=None, page=1):
        """获取订单列表"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        body = {
            "createTimeBegin": start_date,
            "createTimeEnd": end_date,
            "tradeStatusCode": 0,
            "pageNo": page,
            "pageSize": 100
        }
        print(body) 
        body_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        params, headers = self.generate_sign(body_str)
        
        url = f"{self.base_url}/getSalesTradeList"
        response = requests.post(url, params=params, headers=headers, data=body_str)
        
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.text}")
            
        response_data = response.json()
        if response_data['code'] != 200:
            raise Exception(f"API返回错误: {response_data['msg']}")
            
        return response_data

    def get_trade_detail(self, trade_id):
        """获取订单明细"""
        body = {
            "tradeIds": [str(trade_id)]
        }
        body_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        params, headers = self.generate_sign(body_str)
        
        url = f"{self.base_url}/getSalesTradeOrderList"
        response = requests.post(url, params=params, headers=headers, data=body_str)
        
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.text}")
            
        response_data = response.json()
        if response_data['code'] != 200:
            raise Exception(f"API返回错误: {response_data['message']}")
            
        return response_data['data']

    def _get_order_status(self, status_desc):
        """转换订单状态"""
        status_map = {
            '待付款': 'unpaid',
            '待发货': 'pending',
            '配货中': 'picking',
            '已发货': 'shipped',
            '已签收': 'delivered',
            '已取消': 'cancelled'
        }
        logger.info(f"收到订单状态: {status_desc}, 映射为: {status_map.get(status_desc, 'pending')}")
        return status_map.get(status_desc, 'pending')

    def sync_orders(self):
        """同步订单数据"""
        result = {
            'total': 0,
            'created': 0,  # 新建订单数
            'updated': 0,  # 更新订单数
            'failed': 0,
            'errors': []
        }

        try:
            # 获取默认管理员（使用ID为1的用户）
            User = get_user_model()
            try:
                default_manager = User.objects.get(id=1)
            except User.DoesNotExist:
                raise Exception("系统中没有可用的管理员用户")

            # 获取订单列表
            response = self.get_trade_list()
            if not response.get('data'):
                logger.error("API返回数据格式错误")
                raise Exception("API返回数据格式错误")

            orders_data = response['data'].get('data', [])
            total_orders = response['data'].get('total', 0)
            current_page = response['data'].get('currentPage', 1)
            page_size = response['data'].get('pageSize', 100)

            result['total'] = len(orders_data)
            logger.info(f"开始同步订单，当前页：{current_page}，本页数据：{result['total']}，总订单数：{total_orders}")

            for index, order_data in enumerate(orders_data, 1):
                try:
                    # 检查订单是否已存在
                    order_number = order_data.get('tradeNo')
                    if not order_number:
                        logger.error("订单数据缺少订单号")
                        continue
                    logger.info(f"处理订单 [{index}/{len(orders_data)}]: {order_number}================================================================================")
                    logger.info(f"订单状态描述: {order_data.get('tradeStatusDesc')}")
                    order = Order.objects.filter(order_number=order_number).first()
                    
                    if order:
                        logger.info(f"订单 {order_number} 已存在，执行更新操作")
                        # 更新已存在的订单
                        new_status = self._get_order_status(order_data.get('tradeStatusDesc', '待处理'))
                        logger.info(f"订单 {order_number} 状态更新: {order.status} -> {new_status}")
                        order.status = new_status
                        order.payment_status = order_data.get('tradeStatusDesc') not in ['待付款', '已取消']
                        order.total_amount = float(order_data.get('receivable', 0))
                        
                        # 更新币种信息
                        currency = order_data.get('currencyCode')
                        if currency and currency in dict(Order.CURRENCY_CHOICES):
                            order.currency = currency
                        
                        # 更新地址信息
                        order.shipping_address = order_data.get('receiverAddress', '')
                        order.shipping_contact = order_data.get('receiverName', '')
                        order.shipping_phone = order_data.get('receiverMobile') or order_data.get('receiverTelno', '')
                        order.postal_code = order_data.get('receiverZip', '')
                        order.country = order_data.get('country', '')
                        order.state = order_data.get('receiverProvince', '')
                        order.city = order_data.get('receiverCity', '')
                        order.district = order_data.get('receiverDistrict', '')
                        
                        # 更新备注信息
                        order.system_remark = order_data.get('erpRemark', '').strip()
                        order.cs_remark = order_data.get('csRemark', '').strip()
                        order.buyer_remark = order_data.get('buyerMessage', '').strip()
                        
                        # 如果订单已支付但支付时间为空，更新支付时间
                        if order.payment_status and not order.payment_time and order_data.get('created'):
                            order.payment_time = datetime.strptime(order_data['created'], '%Y-%m-%dT%H:%M:%S')
                        
                        order.save()

                        # 更新包裹状态
                        try:
                            package = Package.objects.get(order=order)
                            # 获取物流服务和仓库
                            logistics_text = order_data.get('logisticsText', '')
                            service = self._get_service_by_name(logistics_text)
                            warehouse = self._get_warehouse_by_code(order_data.get('warehouseNo'))
                            
                            # 更新包裹信息，但不更新状态
                            package.tracking_no = order_data.get('logisticsNo', '')
                            if service:  # 只在找到服务时更新
                                package.service = service
                            if warehouse:  # 只在找到仓库时更新
                                package.warehouse = warehouse
                            
                            package.save()
                            logger.info(f"包裹信息已更新: {order_number}, 物流单号: {package.tracking_no}, 物流服务: {service or '未找到'}, 仓库: {warehouse or '未找到'}")
                            
                            # 如果有发货时间，创建发货轨迹记录，包裹状态会随轨迹记录更新
                            delivery_time = order_data.get('deliveryTime')
                            if delivery_time and not Tracking.objects.filter(package=package, status=1).exists():
                                delivery_time = datetime.strptime(delivery_time, '%Y-%m-%dT%H:%M:%S')
                                self._create_tracking_record(
                                    package=package,
                                    status=1,  # 待揽收
                                    description="包裹已发货，等待揽收",
                                    tracking_time=delivery_time
                                )
                                # 更新包裹状态为待揽收
                                package.pkg_status_code = '1'
                                package.save()
                                logger.info(f"包裹状态已更新为待揽收: {order_number}")
                                
                        except Package.DoesNotExist:
                            logger.warning(f"订单 {order_number} 没有关联的包裹，尝试创建新包裹")
                            try:
                                # 获取物流服务
                                service = self._get_service_by_name(order_data.get('logisticsText'))
                                if not service:
                                    logger.info(f"订单 {order_number} 没有物流服务信息，跳过包裹创建")
                                    continue

                                # 获取仓库
                                warehouse = self._get_warehouse_by_code(order_data.get('warehouseNo'))
                                if not warehouse:
                                    logger.error(f"订单 {order_number} 找不到对应的仓库，跳过包裹创建")
                                    continue

                                # 获取订单明细
                                details = self.get_trade_detail(order_data['tradeId'])
                                items_data = []
                                
                                # 准备包裹商品数据
                                for item in details:
                                    try:
                                        sku = SKU.objects.get(sku_code=item['skuNo'])
                                        items_data.append({
                                            'sku_code': sku.sku_code,
                                            'sku_name': sku.sku_name,
                                            'quantity': int(item.get('num', 0))
                                        })
                                    except SKU.DoesNotExist:
                                        logger.error(f"找不到SKU: {item['skuNo']}, 订单号: {order_number}")
                                        continue

                                # 创建包裹，初始状态为待发货
                                package = Package(
                                    order=order,
                                    warehouse=warehouse,
                                    service=service,
                                    tracking_no=order_data.get('logisticsNo', ''),
                                    pkg_status_code='0',  # 初始状态为待发货
                                    items=items_data
                                )
                                package.save()
                                
                                # 创建包裹创建轨迹记录，使用订单创建时间
                                self._create_tracking_record(
                                    package=package,
                                    status=0,  # 待发货
                                    description="包裹已创建",
                                    tracking_time=order.order_place_time or timezone.now()  # 使用订单创建时间，如果为空则使用当前时间
                                )
                                
                                # 如果有发货时间，创建发货轨迹记录并更新包裹状态
                                delivery_time = order_data.get('deliveryTime')
                                if delivery_time:
                                    delivery_time = datetime.strptime(delivery_time, '%Y-%m-%dT%H:%M:%S')
                                    self._create_tracking_record(
                                        package=package,
                                        status=1,  # 待揽收
                                        description="包裹已发货，等待揽收",
                                        tracking_time=delivery_time
                                    )
                                    # 更新包裹状态为待揽收
                                    package.pkg_status_code = '1'
                                    package.save()
                                    logger.info(f"包裹状态已更新为待揽收: {order_number}")
                                
                                # 更新订单的package_id字段
                                order.package_id = str(package.id)
                                order.save()
                                
                                logger.info(f"创建包裹成功，包裹ID: {package.id}, 物流单号: {package.tracking_no}, 物流服务: {service}, 仓库: {warehouse}")

                                result['created'] += 1
                                logger.info(f"订单 {order_number} 及其包裹创建成功")
                            except Exception as e:
                                logger.error(f"为已存在订单创建包裹失败: {str(e)}")
                        except Exception as e:
                            logger.error(f"更新包裹状态失败: {order_number}, 错误: {str(e)}")

                        result['updated'] += 1
                        logger.info(f"订单 {order_number} 更新成功")
                        continue

                    logger.info(f"订单 {order_number} 不存在，开始创建新订单")

                    # 检查仓库信息
                    warehouse = self._get_warehouse_by_code(order_data.get('warehouseNo'))
                    if not warehouse:
                        logger.warning(f"订单 {order_number} 找不到对应的仓库信息(warehouseNo: {order_data.get('warehouseNo')})")

                    # 获取或创建店铺
                    shop_code = order_data.get('shopNo')
                    shop_name = order_data.get('shopText')
                    
                    if not shop_code or not shop_name:
                        logger.error(f"订单 {order_number} 缺少店铺信息")
                        raise Exception("订单缺少店铺信息")

                    shop, created = Shop.objects.get_or_create(
                        shop_code=shop_code,
                        defaults={
                            'name': shop_name,
                            'platform': 'platform' if order_data.get('tradeType') != '线下' else 'offline',
                            'status': 1,
                            'manager': default_manager
                        }
                    )
                    if created:
                        logger.info(f"已创建新店铺: {shop_name} ({shop_code})")
                    elif shop.name != shop_name:
                        # 如果店铺名称有变化，更新店铺名称
                        shop.name = shop_name
                        shop.save()
                        logger.info(f"已更新店铺名称: {shop_name} ({shop_code})")

                    with transaction.atomic():
                        # 创建订单
                        order = Order(
                            order_number=order_number,
                            platform_order_number=order_data.get('srcTids', ''),
                            order_type=self._get_order_type(order_data),
                            shop=shop,
                            status=self._get_order_status(order_data.get('tradeStatusDesc', '待处理')),
                            shipping_contact=order_data.get('receiverName', ''),
                            shipping_phone=order_data.get('receiverMobile') or order_data.get('receiverTelno', ''),
                            shipping_address=order_data.get('receiverAddress', ''),
                            postal_code=order_data.get('receiverZip', ''),
                            country=order_data.get('country', ''),
                            state=order_data.get('receiverProvince', ''),
                            city=order_data.get('receiverCity', ''),
                            district=order_data.get('receiverDistrict', ''),
                            payment_status=order_data.get('tradeStatusDesc') not in ['待付款', '已取消'],
                            payment_time=datetime.strptime(order_data['created'], '%Y-%m-%dT%H:%M:%S') if order_data.get('created') else None,
                            order_place_time=datetime.strptime(order_data['created'], '%Y-%m-%dT%H:%M:%S') if order_data.get('created') else None,
                            system_remark=order_data.get('erpRemark', '').strip(),
                            cs_remark=order_data.get('csRemark', '').strip(),
                            buyer_remark=order_data.get('buyerMessage', '').strip(),
                            total_amount=float(order_data.get('receivable', 0)),
                            currency=order_data.get('currencyCode') if order_data.get('currencyCode') in dict(Order.CURRENCY_CHOICES) else None
                        )
                        order.save()
                        logger.info(f"订单基本信息创建成功: {order_number}")

                        # 获取订单明细
                        details = self.get_trade_detail(order_data['tradeId'])
                        items_data = []
                        logger.info(f"获取到订单 {order_number} 的商品明细，共 {len(details)} 个商品")

                        # 创建订单商品
                        for item in details:
                            try:
                                sku = SKU.objects.get(sku_code=item['skuNo'])
                                logger.info(f"找到SKU: {item['skuNo']}")
                            except SKU.DoesNotExist:
                                logger.error(f"找不到SKU: {item['skuNo']}, 订单号: {order_number}")
                                continue

                            cart = Cart(
                                order=order,
                                sku=sku,
                                quantity=int(item.get('num', 0)),
                                unit_price=float(item.get('skuPrice', 0) or item.get('latestPurchasePrice', 0)),
                                total_price=float(item.get('skuPrice', 0) or item.get('latestPurchasePrice', 0)) * int(item.get('num', 0))
                            )
                            cart.save()
                            logger.info(f"创建订单商品: {sku.sku_code}, 数量: {cart.quantity}")

                            # 添加到包裹商品列表
                            items_data.append({
                                'sku_code': sku.sku_code,
                                'sku_name': sku.sku_name,
                                'quantity': int(item.get('num', 0))
                            })

                        # 只有在有仓库信息时才创建包裹
                        if warehouse:
                            # 获取物流服务
                            service = self._get_service_by_name(order_data.get('logisticsText'))
                            if service:
                                # 创建包裹
                                package = Package(
                                    order=order,
                                    warehouse=warehouse,
                                    service=service,
                                    tracking_no=order_data.get('logisticsNo', ''),
                                    pkg_status_code=self.PACKAGE_STATUS_MAP.get(order.status, '0'),
                                    items=items_data
                                )
                                package.save()
                                
                                # 创建包裹创建轨迹记录
                                self._create_tracking_record(
                                    package=package,
                                    status=0,  # 待发货
                                    description="包裹已创建"
                                )
                                
                                # 如果有发货时间，创建发货轨迹记录
                                delivery_time = order_data.get('deliveryTime')
                                if delivery_time:
                                    delivery_time = datetime.strptime(delivery_time, '%Y-%m-%dT%H:%M:%S')
                                    self._create_tracking_record(
                                        package=package,
                                        status=1,  # 待揽收
                                        description="包裹已发货，等待揽收",
                                        tracking_time=delivery_time
                                    )
                                
                                # 更新订单的package_id字段
                                order.package_id = str(package.id)
                                order.save()
                                
                                logger.info(f"创建包裹成功，包裹ID: {package.id}, 物流单号: {package.tracking_no}, 物流服务: {service}, 仓库: {warehouse}")
                            else:
                                logger.warning(f"订单 {order_number} 没有物流服务信息，跳过包裹创建")
                        else:
                            logger.info(f"订单 {order_number} 没有仓库信息，跳过包裹创建")

                        result['created'] += 1
                        logger.info(f"订单 {order_number} 创建成功" + (" 并创建包裹" if warehouse else "，未创建包裹"))

                except Exception as e:
                    result['failed'] += 1
                    error_msg = f"订单 {order_data.get('tradeNo')} 同步失败: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)

            logger.info(f"订单同步完成，总计: {result['total']}, 新建: {result['created']}, 更新: {result['updated']}, 失败: {result['failed']}")
            return result

        except Exception as e:
            logger.error(f"同步订单数据失败: {str(e)}")
            raise

    def _get_order_type(self, order_data):
        """根据订单数据判断订单类型"""
        if '达人样品' in (order_data.get('erpRemark') or ''):
            return 'influencer'
        if order_data.get('tradeType') == '线下':
            return 'offline'
        return 'platform' 

    def _get_warehouse_by_code(self, warehouse_code):
        """根据仓库编号获取仓库对象"""
        if not warehouse_code:
            logger.warning("API返回的仓库编号为空")
            return None
        
        try:
            # 尝试将仓库编号转换为整数ID
            warehouse_id = int(warehouse_code)
            warehouse = Warehouse.objects.filter(id=warehouse_id).first()
            if warehouse:
                return warehouse
            
            logger.error(f"找不到匹配的仓库ID: {warehouse_id}")
            return None
        except (ValueError, TypeError):
            logger.error(f"无效的仓库ID格式: {warehouse_code}")
            return None
        except Exception as e:
            logger.error(f"查找仓库失败: {str(e)}")
            return None 

    def _create_tracking_record(self, package, status, description, tracking_time=None):
        """创建包裹轨迹记录"""
        try:
            if not tracking_time:
                tracking_time = timezone.now()
            
            Tracking.objects.create(
                package=package,
                status=status,
                location=package.warehouse.warehouse_name if package.warehouse else '',
                description=description,
                tracking_time=tracking_time
            )
            logger.info(f"创建包裹轨迹记录成功: {package.tracking_no}, 状态: {status}")
        except Exception as e:
            logger.error(f"创建包裹轨迹记录失败: {str(e)}") 

    def create_order(self, order_data):
        """创建订单到旺店通系统"""
        try:
            # 获取第一个订单的数据（因为order_data是一个列表）
            order = order_data[0]
            
            # 计算商品总金额
            total_amount = sum(item['price'] * item['actualNum'] for item in order['goods'])
            
            # 修改仓库名称、备注、币种和支付金额
            order['baseInfo']['warehouseName'] = "丰宝云仓-番禺"
            order['baseInfo']['erpRemark'] = "线下订单"
            order['baseInfo']['currencyCode'] = "CNY"
            order['baseInfo']['paid'] = total_amount
            
            # 设置收件人国家
            order['receiverInfo']['receiverCountryName'] = "中国"
            
            # 构建API请求数据
            body = {
                "baseInfo": order['baseInfo'],
                "goods": order['goods'],
                "receiverInfo": order['receiverInfo']
            }
            
            body_str = json.dumps([body], ensure_ascii=False, separators=(",", ":"))
            params, headers = self.generate_sign(body_str)
            
            url = f"{self.base_url}/create/trade"
            response = requests.post(url, params=params, headers=headers, data=body_str)
            
            if response.status_code != 200:
                raise Exception(f"API请求失败: {response.text}")
            
            response_data = response.json()
            
            # 检查是否有导入错误
            if response_data.get('data', {}).get('errorImportData'):
                error_data = response_data['data']['errorImportData'][0]
                raise Exception(f"订单导入失败: {error_data.get('message')} (错误代码: {error_data.get('code')})")
            
            # 检查是否有成功创建的订单
            success_trades = response_data.get('data', {}).get('successCreateTrades', [])
            if not success_trades:
                raise Exception("订单创建失败：未返回成功创建的订单信息")
            
            # 返回成功响应
            return {
                'success': True,
                'code': 0,
                'message': '订单创建成功',
                'data': success_trades[0]  # 返回第一个成功创建的订单信息
            }
        
        except Exception as e:
            logger.error(f"创建订单失败: {str(e)}")
            return {
                'success': False,
                'code': -1,
                'message': str(e)
            } 