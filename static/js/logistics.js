// 编辑物流服务
function editService(serviceId) {
    // 获取服务信息
    fetch(`/api/logistics/services/${serviceId}/`)
        .then(response => response.json())
        .then(data => {
            // 填充表单
            document.getElementById('edit-service-id').value = data.id;
            document.getElementById('edit-service-name').value = data.service_name;
            document.getElementById('edit-service-code').value = data.service_code;
            document.getElementById('edit-service-type').value = data.service_type;
            
            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('modal-edit-service'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('获取服务信息失败');
        });
}

// 更新物流服务
document.getElementById('form-edit-service')?.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const serviceId = document.getElementById('edit-service-id').value;
    const formData = new FormData(this);
    
    fetch(`/api/logistics/services/${serviceId}/`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            service_name: formData.get('service_name'),
            service_code: formData.get('service_code'),
            service_type: formData.get('service_type')
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 关闭模态框并刷新页面
            bootstrap.Modal.getInstance(document.getElementById('modal-edit-service')).hide();
            window.location.reload();
        } else {
            alert(data.message || '更新失败');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('更新失败');
    });
});

// 获取CSRF Token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
} 