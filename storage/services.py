from datetime import datetime, timedelta
from django.conf import settings
from django.db import transaction
from gallery.models import SKU
from .models import Warehouse, StockIn, Inventory
import requests
import json
import logging

logger = logging.getLogger(__name__)

class WDTStockInSyncService:
    """旺店通入库单同步服务"""
    
    def __init__(self):
        self.base_url = settings.WDT_API_URL
        self.sid = settings.WDT_SID
        self.appkey = settings.WDT_APPKEY
    
    def _call_api(self, api_name, params):
        """调用旺店通API"""
        url = f"{self.base_url}/{api_name}"
        
        # 添加公共参数
        params.update({
            'sid': self.sid,
            'appkey': self.appkey,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
        
        try:
            response = requests.post(url, json=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') != 0:
                logger.error(f"WDT API Error: {result.get('message')}")
                return None
                
            return result.get('data')
            
        except Exception as e:
            logger.error(f"Error calling WDT API: {str(e)}")
            return None
    
    def sync_stock_in_records(self, start_time=None, end_time=None):
        """同步入库单记录"""
        if not start_time:
            # 默认同步最近24小时的数据
            start_time = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        if not end_time:
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        params = {
            'start_time': start_time,
            'end_time': end_time,
            'page_no': 1,
            'page_size': 100,
        }
        
        while True:
            # 调用入库单查询接口
            data = self._call_api('api/stock-in/list', params)
            if not data:
                break
                
            records = data.get('records', [])
            if not records:
                break
                
            # 处理每条入库记录
            for record in records:
                self._process_stock_in_record(record)
            
            # 检查是否还有下一页
            total_page = data.get('total_page', 1)
            if params['page_no'] >= total_page:
                break
            
            params['page_no'] += 1
    
    @transaction.atomic
    def _process_stock_in_record(self, record):
        """处理单条入库记录"""
        try:
            # 获取或创建SKU
            sku_code = record.get('spec_code')
            sku = SKU.objects.filter(sku_code=sku_code).first()
            if not sku:
                logger.warning(f"SKU not found: {sku_code}")
                return
            
            # 获取仓库
            warehouse_code = record.get('warehouse_no')
            try:
                warehouse = Warehouse.objects.get(id=int(warehouse_code))
            except (ValueError, TypeError, Warehouse.DoesNotExist):
                logger.warning(f"找不到仓库，跳过记录: warehouse_code={warehouse_code}")
                return
            
            # 创建入库单
            stock_in_code = record.get('stock_in_no')
            if StockIn.objects.filter(stock_in_code=stock_in_code).exists():
                logger.info(f"Stock in record already exists: {stock_in_code}")
                return
                
            quantity = float(record.get('num', 0))
            stock_in = StockIn.objects.create(
                stock_in_code=stock_in_code,
                warehouse=warehouse,
                sku=sku,
                stock_in_type='PURCHASE',  # 根据实际情况设置
                quantity=quantity,
                source_order=record.get('order_no'),
                stock_in_time=datetime.strptime(record.get('created_time'), '%Y-%m-%d %H:%M:%S'),
                remark=f"从旺店通同步: {record.get('remark', '')}"
            )
            
            # 更新或创建库存记录
            inventory, created = Inventory.objects.get_or_create(
                warehouse=warehouse,
                sku=sku,
                batch_code=stock_in_code,
                defaults={'quantity': quantity}
            )
            
            if not created:
                inventory.quantity += quantity
                inventory.save()
            
            # 关联入库单和库存记录
            stock_in.inventory = inventory
            stock_in.save()
            
            logger.info(f"Successfully processed stock in record: {stock_in_code}")
            
        except Exception as e:
            logger.error(f"Error processing stock in record: {str(e)}")
            raise 