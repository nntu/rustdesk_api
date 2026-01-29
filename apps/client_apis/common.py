import json
import logging
import time
import traceback
from functools import wraps

from django.http import HttpRequest, JsonResponse
from django.http.response import HttpResponseRedirectBase, HttpResponse
from django.template.response import TemplateResponse, SimpleTemplateResponse

from apps.db.service import TokenService, PeerInfoService, LoginClientService
from common.utils import get_randem_md5

logger = logging.getLogger('request_debug_log')


def check_login(func):
    """
    Decorator kiểm tra người dùng đã đăng nhập

    :param func: Hàm được decorator
    :return: Hàm sau khi bọc
    """

    @wraps(func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        headers = request.headers
        if 'Authorization' not in headers:
            return JsonResponse({'error': 'Invalid token'}, status=401)
        token_service = TokenService(request=request)
        token = token_service.authorization
        user_info = token_service.user_info
        body = token_service.request_body
        uuid = token_service.get_cur_uuid_by_token(token)

        system_info = PeerInfoService()
        client_info = system_info.get_peer_info_by_uuid(uuid)
        if not client_info:
            logger.warning('check_login: no client_info for uuid=%s', uuid)
        peer_id = client_info.peer_id if client_info else (body.get('id') if isinstance(body, dict) else None)
        username = user_info.username if hasattr(user_info, 'username') else (user_info or '')
        if not token_service.check_token(token, timeout=3600):
            # Ghi thông tin đăng nhập ở server
            LoginClientService().update_logout_status(
                uuid=uuid,
                username=username,
                peer_id=peer_id,
            )
            return JsonResponse({'error': 'Invalid token'}, status=401)
        token_service.update_token(token)
        return func(request, *args, **kwargs)

    return wrapper


def request_debug_log(func):
    """
    Decorator ghi log request

    :param func: Hàm được decorator
    :return: Hàm sau khi bọc
    """

    @wraps(func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        __uuid = get_randem_md5()
        request_log = {
            'method': request.method,
            'path': request.path,
            'headers': dict(request.headers),
            'client_ip': getattr(request, 'client_ip', request.META.get('CLIENT_IP') or request.META.get('REMOTE_ADDR'))
        }
        token_service = TokenService(request=request)
        # Ghi tham số query
        try:
            if token_service.request_query:
                request_log['request_query'] = token_service.request_query
        except Exception:
            pass

        # Ghi request body theo Content-Type
        try:
            content_type = getattr(request, 'content_type', None) or request.headers.get('Content-Type')
        except Exception:
            content_type = None
        if content_type:
            request_log['content_type'] = content_type

        # multipart/form-data: form và file
        if content_type and 'multipart/form-data' in content_type:
            try:
                # Trường form (có thể nhiều giá trị)
                form_data = {}
                for key, values in request.POST.lists():
                    form_data[key] = values if len(values) > 1 else (values[0] if values else None)
                if form_data:
                    request_log['form'] = form_data
            except Exception:
                pass
            try:
                # Metadata file, chỉ ghi thông tin cần thiết
                if request.FILES:
                    files_info = {}
                    for key, files in request.FILES.lists():
                        meta_list = []
                        for f in files:
                            meta_list.append({
                                'filename': getattr(f, 'name', None),
                                'size': getattr(f, 'size', None),
                                'content_type': getattr(f, 'content_type', None),
                            })
                        files_info[key] = meta_list
                    request_log['files'] = files_info
            except Exception:
                pass
            # Hạn chế đọc request.body, chỉ ghi độ dài
            try:
                content_length = request.META.get('CONTENT_LENGTH')
                if content_length:
                    request_log['content_length'] = int(content_length)
            except Exception:
                pass

        # application/x-www-form-urlencoded: form thường
        elif content_type and 'application/x-www-form-urlencoded' in content_type:
            try:
                form_data = {}
                for key, values in request.POST.lists():
                    form_data[key] = values if len(values) > 1 else (values[0] if values else None)
                if form_data:
                    request_log['form'] = form_data
            except Exception:
                pass

        # application/json: body JSON
        elif content_type and 'application/json' in content_type:
            try:
                if request.body:
                    encoding = getattr(request, 'encoding', None) or 'utf-8'
                    request_log['request_body'] = json.loads(request.body.decode(encoding))
                    request_log['content_length'] = len(request.body)
            except Exception:
                # Fallback sang đoạn text
                try:
                    encoding = getattr(request, 'encoding', None) or 'utf-8'
                    request_log['request_text'] = request.body.decode(encoding, errors='ignore')[:2048]
                    request_log['content_length'] = len(request.body)
                except Exception:
                    pass

        # Loại khác hoặc không có Content-Type: ghi đoạn text/độ dài
        else:
            try:
                if request.body:
                    encoding = getattr(request, 'encoding', None) or 'utf-8'
                    snippet = request.body.decode(encoding, errors='ignore')
                    request_log['request_text_snippet'] = snippet[:1024]
                    request_log['content_length'] = len(request.body)
            except Exception:
                pass

        logger.debug(f'[{__uuid}]request: {json.dumps(request_log, ensure_ascii=False, default=str)}')

        start = time.time()
        try:
            response = func(request, *args, **kwargs)
        except Exception:
            logger.error(f'[{__uuid}]error: {traceback.format_exc()}')
            raise
        if response is None:
            response = HttpResponse(status=200)
        response_data = {
            'status_code': response.status_code,
        }
        # Thông tin Content-Type
        try:
            content_type = response.headers.get('Content-Type') if hasattr(response, 'headers') else response.get(
                'Content-Type')
        except Exception:
            content_type = None
        if content_type:
            response_data['content_type'] = content_type

        # Response template: ghi tên template và context
        if isinstance(response, (TemplateResponse, SimpleTemplateResponse)):
            template_name = getattr(response, 'template_name', None)
            response_data['template'] = template_name if isinstance(template_name, (str, list, tuple)) else str(
                template_name)
            response_data['template_context'] = getattr(response, 'context_data', None)

        # Response redirect: ghi URL
        elif isinstance(response, HttpResponseRedirectBase):
            redirect_url = None
            if hasattr(response, 'headers'):
                redirect_url = response.headers.get('Location')
            if not redirect_url:
                redirect_url = getattr(response, 'url', None)
            response_data['redirect_url'] = redirect_url

        # Response streaming (kể cả file): không đọc nội dung, tránh tiêu hao iterator
        elif getattr(response, 'streaming', False):
            response_data['streaming'] = True
            if hasattr(response, 'headers'):
                response_data['content_length'] = int(response.headers.get('Content-Length'))
                disposition = response.headers.get('Content-Disposition')
                if disposition:
                    response_data['content_disposition'] = disposition

        # Response JSON
        elif (content_type and 'application/json' in content_type) or isinstance(response, JsonResponse):
            try:
                if response.content:
                    charset = getattr(response, 'charset', 'utf-8') or 'utf-8'
                    response_data['response_body'] = json.loads(response.content.decode(charset))
            except Exception:
                # Fallback ghi đoạn text, tránh lỗi log
                try:
                    charset = getattr(response, 'charset', 'utf-8') or 'utf-8'
                    response_data['response_text'] = response.content.decode(charset, errors='ignore')[:2048]
                except Exception:
                    pass

        # Loại khác: template HTML hoặc đoạn text (giới hạn độ dài)
        else:
            try:
                # Với response HTML template, chỉ ghi tên template và context
                if content_type and 'text/html' in content_type:
                    template_name = getattr(response, 'template_name', None)
                    context_data = getattr(response, 'context_data', None)
                    response_data['template'] = template_name if isinstance(template_name, (str, list, tuple)) else (
                        str(template_name) if template_name is not None else None)
                    response_data['template_context'] = context_data
                # Loại khác, ghi đoạn text
                elif response.content:
                    charset = getattr(response, 'charset', 'utf-8') or 'utf-8'
                    snippet = response.content.decode(charset, errors='ignore')
                    response_data['response_text_snippet'] = snippet[:1024]
            except Exception:
                pass

        response_log = json.dumps(response_data, ensure_ascii=False, default=str)
        logger.debug(f'[{__uuid}]response: {response_log}, use_time: {round(time.time() - start, 4)} s')
        return response

    return wrapper


def debug_response_None(func):
    @wraps(func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        # return func(request, *args, **kwargs)
        return HttpResponse(status=200)

    return wrapper
