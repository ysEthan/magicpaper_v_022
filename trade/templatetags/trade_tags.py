from django import template
import re

register = template.Library()

@register.filter
def split_address(address):
    """只显示国家、省、市信息"""
    if not address:
        return ''
    
    # 移除括号内容
    address = re.sub(r'\([^)]*\)', '', address)
    
    # 分割地址
    parts = address.split()
    if len(parts) >= 3:
        return ' '.join(parts[:3])
    return address 