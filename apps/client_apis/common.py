from django.http import HttpRequest, JsonResponse

from apps.db.service import TokenService


def check_login(func):
    """
    检查用户是否已登录的装饰器

    :param func: 被装饰的函数
    :return: 装饰后的函数
    """
    def wrapper(request: HttpRequest, *args, **kwargs):
        headers = request.headers
        if 'Authorization' not in headers:
            return JsonResponse({'error': '未登录'}, status=401)
        token = headers['Authorization'][7:]
        token_service = TokenService()
        if not token_service.check_token(token, timeout=3600):
            return JsonResponse({'error': '登录已过期'}, status=401)
        token_service.update_token(token)
        return func(request, *args, **kwargs)
    return wrapper
