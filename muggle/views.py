from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('page:index')
            else:
                messages.error(request, "用户名或密码无效")
    else:
        form = AuthenticationForm()
    return render(request, 'muggle/sign-in.html', {'form': form})

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('page:index')
    else:
        form = UserCreationForm()
    return render(request, 'muggle/sign-up.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "您已成功退出登录")
    return redirect('muggle:login')

def password_reset_view(request):
    return render(request, 'muggle/forgot-password.html')

def home_view(request):
    return render(request, 'muggle/home.html')

@login_required
def user_profile(request):
    """用户个人信息页面"""
    return render(request, 'muggle/user_profile.html', {
        'user': request.user,
        'page_title': '个人信息'
    })

@login_required
def change_password(request):
    """修改密码"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, '密码修改成功！请重新登录。')
            return redirect('muggle:login')
    else:
        form = PasswordChangeForm(request.user)
    
    # 添加表单样式
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control'
    
    return render(request, 'muggle/change_password.html', {
        'form': form,
        'page_title': '修改密码'
    })
