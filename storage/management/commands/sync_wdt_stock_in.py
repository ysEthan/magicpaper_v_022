from django.core.management.base import BaseCommand
from django.utils import timezone
from storage.services import WDTStockInSyncService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '从旺店通同步入库单数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='同步最近几天的数据'
        )

    def handle(self, *args, **options):
        try:
            days = options['days']
            end_time = timezone.now()
            start_time = end_time - timezone.timedelta(days=days)
            
            self.stdout.write(f"开始同步入库单数据，时间范围：{start_time} 至 {end_time}")
            
            service = WDTStockInSyncService()
            service.sync_stock_in_records(
                start_time=start_time.strftime('%Y-%m-%d %H:%M:%S'),
                end_time=end_time.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            self.stdout.write(self.style.SUCCESS('入库单数据同步完成！'))
            
        except Exception as e:
            logger.error(f"同步入库单数据失败: {str(e)}")
            self.stdout.write(self.style.ERROR(f'同步失败: {str(e)}')) 