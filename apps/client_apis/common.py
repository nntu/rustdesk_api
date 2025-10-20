from django.http import HttpRequest, JsonResponse

from apps.db.service import TokenService, LoginClientService, SystemInfoService


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
        token_service = TokenService()
        token, user_info = token_service.get_user_token(request)
        uuid = token_service.get_cur_uuid_by_token(token)

        system_info = SystemInfoService()
        client_info = system_info.get_client_info_by_uuid(uuid)
        if not token_service.check_token(token, timeout=3600):
            # Server端记录登录信息
            LoginClientService().update_logout_status(
                uuid=uuid,
                username=user_info.username,
                client_id=client_info.client_id,
            )
            return JsonResponse({'error': '登录已过期'}, status=401)
        token_service.update_token(token)
        return func(request, *args, **kwargs)
    return wrapper
