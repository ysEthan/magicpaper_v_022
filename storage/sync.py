import json
import requests
import math
import time
import hashlib
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction, models
from .models import Warehouse, StockIn, Inventory, StockOut
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
            "start_time":"2025-01-01 00:00:00",
            # "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
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
                items = result_data.get('data', [])
                
                if not items:
                    logger.info("没有数据需要同步")
                    return {
                        'items': [],
                        'total': 0,
                        'current_page': page,
                        'max_page': page
                    }
                
                # 计算实际的记录总数
                total_records = len(items)
                logger.info(f"获取数据成功: 总数={total_records}")
                
                return {
                    'items': items,
                    'total': total_records,
                    'current_page': result_data.get('currentPage', page),
                    'max_page': math.ceil(total_records / result_data.get('pageSize', 50))
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
        
        # 定义允许处理的仓库ID列表
        ALLOWED_WAREHOUSE_IDS = [8, 9, 10]
        
        # 获取或创建系统操作员用户
        system_operator, _ = User.objects.get_or_create(
            username='system_operator',
            defaults={
                'first_name': '系统',
                'last_name': '操作员',
                'is_staff': True
            }
        )
        
        # 定义特殊时间
        SPECIAL_DATETIME = datetime(2024, 12, 31, 23, 59, 59)
        
        for item in items:
            try:
                # 检查仓库ID是否在允许列表中
                warehouse_id = item.get('warehouseId')
                if warehouse_id not in ALLOWED_WAREHOUSE_IDS:
                    logger.info(f"仓库ID {warehouse_id} 不在允许处理的列表中，跳过")
                    skipped_count += 1
                    continue
                
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
                if StockIn.objects.filter(stock_in_code__startswith=stock_in_code).exists():
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
                
                # 判断是否使用特殊时间
                use_special_time = item.get('srcOrderType') == 2
                stock_in_time = SPECIAL_DATETIME if use_special_time else datetime.strptime(item['checkTime'], '%Y-%m-%d %H:%M:%S')
                
                # 创建入库单及其明细
                for detail in details:
                    try:
                        # 检查SKU是否存在
                        try:
                            sku = SKU.objects.get(sku_code=detail['specNo'])
                        except SKU.DoesNotExist:
                            logger.warning(f"SKU不存在，跳过: {detail['specNo']}")
                            continue
                        
                        # 检查库存记录是否已存在
                        batch_code = f"{stock_in_code}-{detail['specNo']}"
                        inventory, created = Inventory.objects.get_or_create(
                            batch_code=batch_code,
                            defaults={
                                'warehouse': warehouse,
                                'sku': sku,
                                'quantity': detail['num'],
                                'created_at': SPECIAL_DATETIME if use_special_time else timezone.now()
                            }
                        )
                        
                        if not created:
                            logger.info(f"库存记录已存在，跳过: {batch_code}")
                            continue
                        
                        # 获取入库成本
                        unit_cost = float(detail.get('costPrice', 0))
                        if unit_cost <= 0:
                            # 如果没有成本价，尝试从采购单价获取
                            unit_cost = float(detail.get('purchasePrice', 0))
                        
                        # 创建入库单
                        stock_in = StockIn.objects.create(
                            stock_in_code=batch_code,
                            warehouse=warehouse,
                            sku=sku,
                            inventory=inventory,
                            stock_in_type='purchase' if item['srcOrderType'] == 1 else 'other',
                            quantity=detail['num'],
                            unit_cost=unit_cost,
                            source_order=item.get('srcOrderNo', ''),
                            operator=operator,
                            stock_in_time=stock_in_time,
                            created_at=SPECIAL_DATETIME if use_special_time else timezone.now(),
                            remark=f"操作人: {operator_name}, 供应商: {item.get('providerName', '')}, 原因: {item.get('reason', '')}"
                        )
                        
                        updated_count += 1
                        logger.info(f"成功创建入库记录: {stock_in.stock_in_code}, 入库成本: {unit_cost}, 入库时间: {stock_in_time}")
                        
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
        total_skipped = 0
        
        while True:
            # 获取当前页数据
            stock_in_data = sync_stock_in_data(page)
            
            # 更新到数据库
            updated_count, skipped_count = update_stock_in_data(stock_in_data)
            total_updated += updated_count
            total_skipped += skipped_count
            
            # 检查是否还有下一页
            if page >= stock_in_data['max_page']:
                break
            
            # 继续下一页
            page += 1
            time.sleep(10)  # 避免请求过快
        
        logger.info(f"同步完成，共更新 {total_updated} 条记录，跳过 {total_skipped} 条")
        return True, f"入库单同步完成，共更新 {total_updated} 条记录，跳过 {total_skipped} 条"
        
    except Exception as e:
        logger.error(f"同步过程中断: {str(e)}")
        return False, f"同步失败: {str(e)}"





def sync_stock_out_data(page=1):
    """同步出库单数据"""
    try:
        logger.info(f"开始同步第 {page} 页出库单数据")
        
        # 设置时间范围为最近30天
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        body = {
            # "start_time":"2025-01-01 00:00:00",   
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": 1,  # 1表示已完成
            "pageNo": page,
            "pageSize": 100
        }
        
        body_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        logger.info(f"请求参数: {body_str}")
        
        params, headers = generate_sign(body_str)
        url = "https://openapi.qizhishangke.com/api/openservices/stock/v1/getStockOutOrderDetails"
        
        # 添加重试机制
        for attempt in range(3):
            try:
                response = requests.post(url, params=params, headers=headers, data=body_str.encode('utf-8'))
                response.raise_for_status()
                data = response.json()
                
                if not isinstance(data, dict):
                    raise ValueError(f"API返回的数据格式不正确: {data}")
                
                # 检查API响应状态
                if data.get('code') != 200 or not data.get('ok'):
                    raise ValueError(f"API返回错误: {data.get('msg')}")
                
                # 获取实际的数据部分
                result_data = data.get('data', {})
                items = result_data.get('data', [])
                
                if not items:
                    logger.info("没有数据需要同步")
                    return {
                        'items': [],
                        'total': 0,
                        'current_page': page,
                        'max_page': page
                    }
                
                total_records = result_data.get('total', 0)
                page_size = result_data.get('pageSize', 100)
                max_page = math.ceil(total_records / page_size)
                
                logger.info(f"获取数据成功: 总数={total_records}, 当前页={page}, 最大页={max_page}")
                
                return {
                    'items': items,
                    'total': total_records,
                    'current_page': result_data.get('currentPage', page),
                    'max_page': max_page
                }
                
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    time.sleep(15)
                    continue
                raise Exception(f"API请求失败: {str(e)}")
            except Exception as e:
                raise Exception(f"处理响应失败: {str(e)}")
        
    except Exception as e:
        logger.error(f"同步出库单数据失败: {str(e)}")
        raise

@transaction.atomic
def update_stock_out_data(stock_out_data):
    """更新出库单数据到数据库"""
    try:
        items = stock_out_data.get('items', [])
        logger.info(f"开始更新出库单数据: {len(items)} 条记录")
        
        updated_count = 0
        skipped_count = 0
        
        # 定义允许处理的仓库ID列表
        ALLOWED_WAREHOUSE_IDS = [8, 9, 10]
        
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
            # 为每个订单创建独立的事务
            with transaction.atomic():
                stock_out_no = None  # 初始化变量
                try:
                    # 检查仓库ID是否在允许列表中
                    warehouse_id = item.get('warehouseId')
                    if warehouse_id not in ALLOWED_WAREHOUSE_IDS:
                        logger.info(f"仓库ID {warehouse_id} 不在允许处理的列表中，跳过")
                        skipped_count += 1
                        continue
                    
                    # 检查是否有发货时间
                    if not item.get('consignTime'):
                        logger.warning("发货时间为空，跳过")
                        skipped_count += 1
                        continue

                    # 获取或创建仓库
                    warehouse, _ = Warehouse.objects.get_or_create(
                        warehouse_code=item['warehouseNo'],
                        defaults={
                            'warehouse_name': item['warehouseName'],
                            'status': True
                        }
                    )
                    
                    # 检查出库单是否已处理
                    stock_out_no = item.get('stockoutNo')  # 修改字段名
                    if not stock_out_no:
                        logger.warning("出库单号为空，跳过")
                        skipped_count += 1
                        continue

                    if StockOut.objects.filter(stock_out_code=stock_out_no).exists():  # 直接使用stockoutNo
                        logger.info(f"出库单已处理，跳过: {stock_out_no}")
                        skipped_count += 1
                        continue
                    
                    # 处理出库单明细
                    details = item.get('stockOutOrderDetailsVOList', [])
                    if not details:
                        logger.warning(f"出库单无明细，跳过: {stock_out_no}")
                        skipped_count += 1
                        continue
                    
                    # 获取出库时间
                    stock_out_time = datetime.strptime(item['consignTime'], '%Y-%m-%d %H:%M:%S')    
                    
                    for detail in details:
                        try:
                            # 获取SKU
                            sku_code = detail.get('specNo')
                            if not sku_code:
                                logger.warning(f"SKU编码为空，跳过: {stock_out_no}")
                                continue
                                
                            try:
                                sku = SKU.objects.get(sku_code=sku_code)
                            except SKU.DoesNotExist:
                                logger.warning(f"SKU不存在，跳过: {sku_code}")
                                continue
                            
                            # 获取出库数量
                            quantity = int(detail.get('num', 0))
                            if quantity <= 0:
                                logger.warning(f"出库数量无效，跳过: {stock_out_no}, SKU: {sku_code}")
                                continue
                            
                            # 查找可用库存（按FIFO原则）
                            available_inventory = (
                                Inventory.objects
                                .select_for_update()  # 添加行锁
                                .filter(warehouse=warehouse, sku=sku, quantity__gt=0)
                                .order_by('created_at')
                                .first()
                            )
                            
                            if not available_inventory:
                                logger.warning(f"无可用库存，跳过: {stock_out_no}, SKU: {sku_code}")
                                continue
                            
                            # 检查库存是否足够
                            if available_inventory.quantity < quantity:
                                logger.warning(f"库存不足，跳过: {stock_out_no}, SKU: {sku_code}")
                                continue
                            
                            # 创建出库记录
                            stock_out = StockOut.objects.create(
                                stock_out_code=f"{stock_out_no}-{sku_code}",  # 直接使用stockoutNo
                                warehouse=warehouse,
                                sku=sku,
                                inventory=available_inventory,
                                stock_out_type='sales',
                                quantity=quantity,
                                related_order=item.get('srcOrderNo', ''),
                                operator=system_operator,
                                stock_out_time=stock_out_time,
                                remark=f"操作人: {item.get('operatorName', '')}, 原因: {item.get('reason', '')}, 物流单号: {item.get('logisticsNo', '')}"
                            )
                            
                            # 扣减库存
                            available_inventory.quantity -= quantity
                            available_inventory.save()
                            
                            updated_count += 1
                            logger.info(f"成功创建出库记录: {stock_out.stock_out_code}")
                            
                        except Exception as e:
                            logger.error(f"处理出库单明细失败: {stock_out_no}, SKU: {sku_code}, 错误: {str(e)}")
                            raise
                    
                except Exception as e:
                    error_msg = f"处理出库单失败: {stock_out_no if stock_out_no else '未知'}, 错误: {str(e)}"
                    logger.error(error_msg)
                    # 不再抛出异常，让其他订单继续处理
                    continue
        
        logger.info(f"同步完成: 更新 {updated_count} 条，跳过 {skipped_count} 条")
        return updated_count, skipped_count
        
    except Exception as e:
        logger.error(f"更新出库单数据失败: {str(e)}")
        raise

def sync_all_stock_outs():
    """同步所有出库单数据"""
    try:
        page = 1
        total_updated = 0
        total_skipped = 0
        
        while True:
            # 获取当前页数据
            stock_out_data = sync_stock_out_data(page)
            
            # 更新到数据库
            updated_count, skipped_count = update_stock_out_data(stock_out_data)
            total_updated += updated_count
            total_skipped += skipped_count
            
            # 检查是否还有下一页
            if page >= stock_out_data['max_page']:
                break
            
            # 继续下一页
            page += 1
            time.sleep(10)  # 避免请求过快
        
        logger.info(f"同步完成，共更新 {total_updated} 条记录，跳过 {total_skipped} 条")
        return True, f"出库单同步完成，共更新 {total_updated} 条记录，跳过 {total_skipped} 条"
        
    except Exception as e:
        logger.error(f"同步过程中断: {str(e)}")
        return False, f"同步失败: {str(e)}" 