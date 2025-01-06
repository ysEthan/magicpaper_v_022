import json
import requests
import math
import time
import hashlib
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from .models import Warehouse, StockIn, Inventory
from gallery.models import SKU
from django.contrib.auth.models import User

# 配置日志
logger = logging.getLogger(__name__)

def generate_sign(body):
    """生成API签名"""
    try:
        app_name = "mathmagic"
        app_key = "82be0592545283da00744b489f758f99"
        sid = "mathmagic"
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        timestamp = str(int(time.time()))
        sign_str = f"{app_key}appName{app_name}body{body}sid{sid}timestamp{timestamp}{app_key}"
        sign = hashlib.md5(sign_str.encode()).hexdigest()
        
        params = {
            "appName": app_name,
            "sid": sid,
            "sign": sign,
            "timestamp": timestamp,
        }
        logger.info(f"生成签名成功: params={params}")
        return params, headers
    except Exception as e:
        logger.error(f"生成签名失败: {str(e)}")
        raise

def sync_stock_in_data(page=1):
    """同步入库单数据"""
    try:
        logger.info(f"开始同步第 {page} 页数据")
        
        # 设置时间范围为最近30天
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)
        
        body = {
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": 1,  # 状态为1表示已完成
            "pageNo": page,
            "pageSize": 50
        }
        
        body_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        logger.info(f"请求参数: {body_str}")
        
        params, headers = generate_sign(body_str)
        url = "https://openapi.qizhishangke.com/api/openservices/stock/v1/getStockInOrderDetails"
        
        # 添加重试机制
        for attempt in range(3):
            try:
                response = requests.post(url, params=params, headers=headers, data=body_str.encode('utf-8'))
                response.raise_for_status()
                data = response.json()
                print(data)
                if not isinstance(data, dict):
                    raise ValueError(f"API返回的数据格式不正确: {data}")
                
                # 检查API响应状态
                if data.get('code') != 200 or not data.get('ok'):
                    raise ValueError(f"API返回错误: {data.get('msg')}")
                
                # 获取实际的数据部分
                result_data = data.get('data', {})
                if not result_data or not result_data.get('data'):
                    logger.info("没有数据需要同步")
                    return {
                        'items': [],
                        'total': 0,
                        'current_page': page,
                        'max_page': page
                    }
                
                logger.info(f"获取数据成功: 总数={result_data.get('total', 0)}")
                return {
                    'items': result_data.get('data', []),
                    'total': result_data.get('total', 0),
                    'current_page': result_data.get('currentPage', page),
                    'max_page': math.ceil(result_data.get('total', 0) / result_data.get('pageSize', 50))
                }
                
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    time.sleep(15)
                    continue
                raise Exception(f"API请求失败: {str(e)}")
            except Exception as e:
                raise Exception(f"处理响应失败: {str(e)}")
        
    except Exception as e:
        logger.error(f"同步数据失败: {str(e)}")
        raise

@transaction.atomic
def update_stock_in_data(stock_in_data):
    """更新入库单数据到数据库"""
    try:
        items = stock_in_data.get('items', [])
        logger.info(f"开始更新入库单数据: {len(items)} 条记录")
        
        updated_count = 0
        skipped_count = 0
        
        # 获取或创建系统操作员用户
        system_operator, _ = User.objects.get_or_create(
            username='system_operator',
            defaults={
                'first_name': '系统',
                'last_name': '操作员',
                'is_staff': True
            }
        )
        
        for item in items:
            try:
                # 获取或创建仓库
                warehouse, _ = Warehouse.objects.get_or_create(
                    warehouse_code=item['warehouseNo'],
                    defaults={
                        'warehouse_name': item['warehouseName'],
                        'status': True
                    }
                )
                
                # 检查入库单是否已存在
                stock_in_code = item['stockinNo']
                if StockIn.objects.filter(stock_in_code=stock_in_code).exists():
                    logger.info(f"入库单已存在，跳过: {stock_in_code}")
                    skipped_count += 1
                    continue
                
                # 处理入库单明细
                details = item.get('stockInOrderDetailsVOList', [])
                if not details:
                    logger.warning(f"入库单无明细，跳过: {stock_in_code}")
                    skipped_count += 1
                    continue
                
                # 获取操作员信息
                operator_name = item.get('operatorName', '系统操作员')
                operator = system_operator  # 默认使用系统操作员
                
                # 创建入库单及其明细
                for detail in details:
                    try:
                        # 检查SKU是否存在
                        try:
                            sku = SKU.objects.get(sku_code=detail['specNo'])
                        except SKU.DoesNotExist:
                            logger.warning(f"SKU不存在，跳过: {detail['specNo']}")
                            continue
                        
                        # 创建库存记录
                        inventory = Inventory.objects.create(
                            warehouse=warehouse,
                            sku=sku,
                            batch_code=f"{stock_in_code}-{detail['specNo']}",
                            quantity=detail['num']
                        )
                        
                        # 创建入库单
                        stock_in = StockIn.objects.create(
                            stock_in_code=f"{stock_in_code}-{detail['specNo']}",
                            warehouse=warehouse,
                            sku=sku,
                            inventory=inventory,
                            stock_in_type='purchase' if item['srcOrderType'] == 1 else 'other',
                            quantity=detail['num'],
                            source_order=item.get('srcOrderNo', ''),
                            operator=operator,  # 设置操作员
                            stock_in_time=datetime.strptime(item['checkTime'], '%Y-%m-%d %H:%M:%S'),
                            remark=f"操作人: {operator_name}, 供应商: {item.get('providerName', '')}, 原因: {item.get('reason', '')}"
                        )
                        
                        updated_count += 1
                        logger.info(f"成功创建入库记录: {stock_in.stock_in_code}")
                        
                    except Exception as e:
                        logger.error(f"处理入库单明细失败: {stock_in_code}, {detail.get('specNo')}, 错误: {str(e)}")
                        raise  # 抛出异常以触发事务回滚
                
            except Exception as e:
                logger.error(f"处理入库单失败: {item.get('stockinNo')}, 错误: {str(e)}")
                raise  # 抛出异常以触发事务回滚
        
        logger.info(f"同步完成: 更新 {updated_count} 条，跳过 {skipped_count} 条")
        return updated_count, skipped_count
        
    except Exception as e:
        logger.error(f"更新入库单数据失败: {str(e)}")
        raise

def sync_all_stock_in():
    """同步所有入库单数据"""
    try:
        page = 1
        total_updated = 0
        
        while True:
            # 获取当前页数据
            stock_in_data = sync_stock_in_data(page)
            
            # 更新到数据库
            update_stock_in_data(stock_in_data)
            total_updated += len(stock_in_data['items'])
            
            # 检查是否还有下一页
            if page >= stock_in_data['max_page']:
                break
            
            # 继续下一页
            page += 1
            time.sleep(10)  # 避免请求过快
        
        logger.info(f"同步完成，共更新 {total_updated} 条记录")
        return True, f"入库单同步完成，共更新 {total_updated} 条记录"
        
    except Exception as e:
        logger.error(f"同步过程中断: {str(e)}")
        return False, f"同步失败: {str(e)}" 