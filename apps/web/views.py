import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from apps.client_apis.common import request_debug_log
from apps.db.service import UserService

# Create your views here.
logger = logging.getLogger(__name__)


@request_debug_log
def index(request):
    # cookies = request.COOKIES
    # print(cookies)
    # print(dict(cookies))
    # for key, value in cookies.items():
    #     print(f"{key}: {value}")
    # return JsonResponse({'message': 'Web正在开发中'})
    return render(request, 'login.html')


@request_debug_log
def login(request: HttpRequest):
    """
    处理登录请求：校验用户名与密码，成功则跳转首页，失败则回到登录页并提示错误。

    :param request: Http 请求对象
    :type request: HttpRequest
    :return: 登录页面或首页的响应
    :rtype: HttpResponse
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        logger.info(f'username: {username}, password: {password}')
        try:
            user = UserService().get_user_info(username=username)
            if not (user and user.check_password(password)):
                raise ValueError('invalid credentials')
            request.session['user'] = user.username
        except Exception:
            # logger.error(traceback.format_exc())
            messages.error(request, '用户名或密码错误')
            return render(request, 'login.html')
        logger.info(f'username: {username}')
        return redirect('web_home')
    else:
        return render(request, 'login.html')


@request_debug_log
def home(request):
    return render(request, 'home.html')


@request_debug_log
def logout(request):
    return redirect('web_login')
