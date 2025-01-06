from django.core.management.base import BaseCommand
from gallery.sync import ProductSync
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = '从旺店通同步商品数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=85,
            help='同步最近几天的数据'
        )
        parser.add_argument(
            '--clean-images',
            action='store_true',
            help='是否清理旧图片'
        )

    def handle(self, *args, **options):
        try:
            days = options['days']
            start_time = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            sync = ProductSync()
            count = sync.sync_products(start_time, end_time)
            self.stdout.write(self.style.SUCCESS(f'成功同步 {count} 个商品'))

            if options['clean_images']:
                sync.clean_old_images()
                self.stdout.write(self.style.SUCCESS('清理旧图片完成'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'同步失败: {str(e)}')) 