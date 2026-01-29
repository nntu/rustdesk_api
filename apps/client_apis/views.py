import json
import logging
import os
import traceback
from datetime import timedelta

from django.conf import settings
from django.http import HttpRequest, JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.client_apis.common import check_login, request_debug_log, debug_response_None
from apps.db.models import PeerInfo, OidcAuth
from apps.db.service import (
    HeartBeatService,
    PeerInfoService,
    TokenService,
    UserService,
    LoginClientService,
)
from common.utils import get_local_time, str2bool, get_randem_md5

logger = logging.getLogger(__name__)

OIDC_TIMEOUT_SECONDS = 180


@request_debug_log
@require_http_methods(["GET"])
def time_test(request: HttpRequest):
    """
    Kiểm tra lưu thời gian có dùng giờ server

    :param request: Đối tượng HTTP request
    :return: JSON chứa thời gian hiện tại và múi giờ
    """
    now = timezone.now()
    local_time = timezone.localtime(now)

    return JsonResponse({
        'utc_time': now.isoformat(),
        'local_time': local_time.isoformat(),
        'timezone': str(local_time.tzinfo)
    })


@request_debug_log
@require_http_methods(["POST"])
def heartbeat(request: HttpRequest):
    try:
        request_data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)
    uuid = request_data.get('uuid')
    peer_id = request_data.get('id')
    modified_at = request_data.get('modified_at', get_local_time())
    ver = request_data.get('ver')
    conns = request_data.get('conns') or []

    HeartBeatService().update(
        uuid=uuid,
        peer_id=peer_id,
        modified_at=modified_at,
        ver=ver,
    )

    peer_info = None
    if uuid:
        peer_info = PeerInfoService().get_peer_info_by_uuid(uuid)
    if not peer_info and peer_id:
        peer_info = PeerInfoService().get_peer_info_by_peer_id(peer_id)

    need_sysinfo = False
    if not peer_info:
        need_sysinfo = True
    elif ver and str(peer_info.version) != str(ver):
        need_sysinfo = True

    response_data = {
        'modified_at': int(get_local_time().timestamp()),
        'disconnect': [],
        'strategy': {},
    }
    if conns is not None:
        response_data['disconnect'] = []
    if need_sysinfo:
        response_data['sysinfo'] = True

    return JsonResponse(response_data)


@request_debug_log
@require_http_methods(["POST"])
def sysinfo(request: HttpRequest):
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)
    uuid = body.get('uuid')

    # Cập nhật thông tin thiết bị trước
    PeerInfoService().update(
        uuid=uuid,
        peer_id=body.get('id'),
        cpu=body.get('cpu'),
        device_name=body.get('hostname'),
        memory=body.get('memory'),
        os=body.get('os'),
        username=body.get('username') or body.get('hostname'),
        version=body.get('version'),
    )

    # Nếu thiết bị đã từng đăng nhập thì cập nhật token
    # Vấn đề: chưa kiểm tra hạn token; server dừng vài giờ rồi chạy lại vẫn refresh token, tạm thời giữ vậy
    TokenService(request=request).update_token_by_uuid(uuid)

    return HttpResponse("SYSINFO_UPDATED", status=200)


@request_debug_log
@require_http_methods(["POST"])
def login(request: HttpRequest):
    """
    Xử lý yêu cầu đăng nhập
    :param request: Đối tượng HTTP request
    :return: JSON response
    """
    token_service = TokenService(request=request)
    body = token_service.request_body

    username = body.get('username')
    password = body.get('password')
    uuid = body.get('uuid')
    device_info = body.get('deviceInfo', {})
    platform = device_info.get('os')  # Hệ điều hành thiết bị
    client_type = device_info.get('type')
    client_name = device_info.get('name')

    safe_body = dict(body)
    if 'password' in safe_body:
        safe_body['password'] = '***'
    logger.info(
        'login request: username="%s", uuid="%s", peer_id="%s", body=%s',
        username,
        uuid,
        body.get('id'),
        safe_body,
    )

    user = UserService().get_user_by_name(username=username)
    if not user or not user.check_password(password):
        logger.warning('login failed: username="%s"', username)
        return JsonResponse({'error': 'Tên đăng nhập hoặc mật khẩu không đúng'})

    token = token_service.create_token(username, uuid)

    # Ghi thông tin đăng nhập ở server
    LoginClientService().update_login_status(
        uuid=uuid,
        username=user,
        peer_id=body.get('id'),
        client_name=client_name,
        platform=platform,
        client_type=client_type,
    )
    #
    # LogService().create_log(
    #     username=username,
    #     uuid=uuid,
    #     log_type='login',
    #     log_message=f'Người dùng {username} đăng nhập'
    # )

    response_payload = {
        'access_token': token,
        'type': 'access_token',
        'user': {
            'name': username,
        }
    }
    logger.info(
        'login response: username="%s", token_len=%s',
        username,
        len(token) if token else 0,
    )
    return JsonResponse(response_payload)


@request_debug_log
@require_http_methods(["GET", "POST"])
def login_options(request: HttpRequest):
    """
    Trả về cấu hình RustDesk server cho client.
    Client cần thông tin này để kết nối đến ID/Relay server.
    """
    response_payload = {
        'id_server': getattr(settings, 'RUSTDESK_ID_SERVER', ''),
        'relay_server': getattr(settings, 'RUSTDESK_RELAY_SERVER', ''),
        'api_server': getattr(settings, 'RUSTDESK_API_SERVER', ''),
        'key': getattr(settings, 'RUSTDESK_KEY', ''),
    }
    logger.info('login_options response: %s', response_payload)
    return JsonResponse(response_payload)


@request_debug_log
@require_http_methods(["POST"])
@check_login
def logout(request: HttpRequest):
    token_service = TokenService(request=request)
    token = token_service.authorization
    user_info = token_service.user_info
    body = token_service.request_body

    uuid = body.get('uuid')

    token_service.delete_token(token)

    # Cập nhật trạng thái đăng xuất
    LoginClientService().update_logout_status(
        uuid=uuid,
        username=user_info,
        peer_id=body.get('id'),
    )
    #
    # LogService().create_log(
    #     username=user_info,
    #     uuid=uuid,
    #     log_type='logout',
    #     log_message=f'Người dùng {user_info} đăng xuất'
    # )
    return JsonResponse({'code': 1})


@request_debug_log
@require_http_methods(["POST"])
@check_login
def current_user(request: HttpRequest):
    """
    Lấy thông tin người dùng hiện tại
    :param request:
    :return:
    """
    token_service = TokenService(request=request)
    token = token_service.authorization
    user_info = token_service.user_info

    return JsonResponse(
        {
            'name': user_info.username,
            'access_token': token,
            'type': 'access_token',
        }
    )


@request_debug_log
@require_http_methods(["GET"])
@check_login
def users(request: HttpRequest):
    """
    Lấy thông tin tất cả người dùng
    :param request:
    :return:
    """
    page = int(request.GET.get('current', 1))
    page_size = int(request.GET.get('pageSize', 10))
    status = str2bool(request.GET.get('status') or True)
    token_service = TokenService(request=request)
    user_info = token_service.user_info
    if user_info.is_superuser:
        result = UserService().get_list_by_status(is_active=status, page=page, page_size=page_size)['results']
    else:
        result = [user_info]

    user_list = [
        {
            "name": user.username,
            "email": user.email,
            "note": "",
            "is_admin": user.is_superuser,
            "status": user.is_active,
            "info": {}
        } for user in result
    ]

    return JsonResponse(
        {
            'total': len(user_list),
            'data': user_list
        }
    )


@request_debug_log
@require_http_methods(["GET"])
@check_login
def peers(request: HttpRequest):
    """
    Hiển thị thiết bị người dùng hiện tại có thể thấy
    Nếu là admin thì thấy tất cả (kể cả thiết bị chưa đăng nhập)
    Nếu là user thì mặc định chỉ thấy thiết bị mình đăng nhập
    :param request:
    :return:
    """
    # TODO: cần hiển thị theo người dùng, hiện chỉ hiển thị user đăng nhập

    token_service = TokenService(request=request)
    user_info = token_service.user_info
    # uuid = token_service.get_cur_uuid_by_token(token)

    client_list = PeerInfoService().get_list()
    data = []
    for client in client_list:
        # if client.uuid == uuid:
        #     continue
        data.append(
            {
                "id": client.peer_id,
                "info": {
                    "device_name": client.device_name,
                    "os": client.os,
                    "username": client.username,
                },
                "status": 1,
                "user_name": user_info.username,
            }
        )
    result = {
        'total': len(client_list),
        'data': data
    }
    return JsonResponse(result)


@request_debug_log
@require_http_methods(["GET"])
@debug_response_None  # Chính thức có phân quyền nhóm thiết bị, tạm trả None để tránh lỗi
@check_login
def device_group_accessible(request):
    """
    Admin lấy toàn bộ thiết bị trên server
    :param request:
    :return:
    """
    token_service = TokenService(request=request)
    user_info = token_service.user_info

    client_list = PeerInfoService().get_list()
    data = []
    for client in client_list:
        client = client if isinstance(client, PeerInfo) else client.uuid
        # if client.uuid == uuid:
        #     continue
        data.append(
            {
                "id": client.peer_id,
                "info": {
                    "device_name": client.device_name,
                    "os": client.os,
                    "username": client.username,
                },
                "status": 1,
                "user_name": user_info.username,
            }
        )
    result = {
        'total': len(client_list),
        'data': data
    }
    return JsonResponse(result)


@request_debug_log
@require_http_methods(["POST"])
def oidc_auth(request: HttpRequest):
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    op = body.get('op') or ''
    peer_id = body.get('id') or ''
    uuid = body.get('uuid') or ''
    device_info = body.get('deviceInfo') or {}

    if not (op and peer_id and uuid):
        return JsonResponse({'error': 'Missing required fields'}, status=400)

    code = get_randem_md5()
    expires_at = timezone.now() + timedelta(seconds=OIDC_TIMEOUT_SECONDS)

    OidcAuth.objects.create(
        code=code,
        op=op,
        peer_id=peer_id,
        uuid=uuid,
        device_info=json.dumps(device_info, ensure_ascii=False),
        expires_at=expires_at,
    )

    url = request.build_absolute_uri(f"/api/oidc/authorize?code={code}")
    return JsonResponse({'code': code, 'url': url})


@request_debug_log
@require_http_methods(["GET", "POST"])
def oidc_authorize(request: HttpRequest):
    code = request.GET.get('code') or ''
    if not code:
        return HttpResponse("Missing code", status=400)

    auth = OidcAuth.objects.filter(code=code).first()
    if not auth:
        return HttpResponse("Invalid code", status=404)

    if auth.expires_at < timezone.now():
        if auth.status != 'expired':
            auth.status = 'expired'
            auth.save(update_fields=['status'])
        return HttpResponse("Code expired", status=400)

    if request.method == "GET":
        html = f"""
        <html>
            <head><title>OIDC Login</title></head>
            <body>
                <h3>Đăng nhập để xác thực thiết bị</h3>
                <form method="post">
                    <input type="hidden" name="code" value="{code}" />
                    <div>
                        <label>Tên đăng nhập</label>
                        <input type="text" name="username" required />
                    </div>
                    <div>
                        <label>Mật khẩu</label>
                        <input type="password" name="password" required />
                    </div>
                    <button type="submit">Đăng nhập</button>
                </form>
            </body>
        </html>
        """
        return HttpResponse(html)

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    if not username or not password:
        return HttpResponse("Thiếu tên đăng nhập hoặc mật khẩu", status=400)

    try:
        user = UserService().get_user_by_name(username=username)
        assert user and user.check_password(password)
    except AssertionError:
        logger.error(traceback.format_exc())
        return HttpResponse("Tên đăng nhập hoặc mật khẩu không đúng", status=401)

    token = TokenService(request=request).create_token(username, auth.uuid, client_type=3)

    device_info = {}
    if auth.device_info:
        try:
            device_info = json.loads(auth.device_info)
        except Exception:
            device_info = {}

    platform = str(device_info.get('os') or 'api').lower()
    if platform not in LoginClientService().platform:
        platform = 'api'
    client_type = device_info.get('type') or 'api'
    client_name = device_info.get('name') or ''

    LoginClientService().update_login_status(
        username=user,
        uuid=auth.uuid,
        peer_id=auth.peer_id,
        client_name=client_name,
        platform=platform,
        client_type=client_type,
    )

    auth.status = 'approved'
    auth.user_id = user
    auth.access_token = token
    auth.save(update_fields=['status', 'user_id', 'access_token'])

    return HttpResponse("Xác thực thành công. Bạn có thể quay lại ứng dụng.")


@request_debug_log
@require_http_methods(["GET"])
def oidc_auth_query(request: HttpRequest):
    code = request.GET.get('code') or ''
    peer_id = request.GET.get('id') or ''
    uuid = request.GET.get('uuid') or ''

    if not code:
        return JsonResponse({'error': 'Missing code'}, status=400)

    auth = OidcAuth.objects.filter(code=code).first()
    if not auth or (peer_id and auth.peer_id != peer_id) or (uuid and auth.uuid != uuid):
        return JsonResponse({'error': 'No authed oidc is found'})

    if auth.expires_at < timezone.now():
        if auth.status != 'expired':
            auth.status = 'expired'
            auth.save(update_fields=['status'])
        return JsonResponse({'error': 'OIDC code expired'}, status=400)

    if auth.status != 'approved' or not auth.access_token:
        return JsonResponse({'error': 'No authed oidc is found'})

    return JsonResponse({
        'access_token': auth.access_token,
        'type': 'access_token',
        'user': {
            'name': auth.user_id.username if auth.user_id else '',
        }
    })


@request_debug_log
@require_http_methods(["POST"])
def record(request: HttpRequest):
    action_type = request.GET.get('type')
    filename = request.GET.get('file')
    offset = request.GET.get('offset')
    length = request.GET.get('length')

    if not action_type or not filename:
        return JsonResponse({'error': 'Missing type or file'}, status=400)

    safe_name = os.path.basename(os.path.normpath(filename))
    if not safe_name:
        return JsonResponse({'error': 'Invalid file name'}, status=400)

    records_root = getattr(settings, 'RECORDS_ROOT', None)
    if not records_root:
        return JsonResponse({'error': 'Server record storage not configured'}, status=500)

    os.makedirs(records_root, exist_ok=True)
    file_path = os.path.join(records_root, safe_name)

    if action_type == 'new':
        with open(file_path, 'wb') as f:
            f.write(b'')
        return HttpResponse(status=200)

    if action_type == 'remove':
        if os.path.exists(file_path):
            os.remove(file_path)
        return HttpResponse(status=200)

    if action_type in ('part', 'tail'):
        if offset is None or length is None:
            return JsonResponse({'error': 'Missing offset or length'}, status=400)
        try:
            offset_val = int(offset)
            length_val = int(length)
        except ValueError:
            return JsonResponse({'error': 'Invalid offset or length'}, status=400)

        data = request.body or b''
        if length_val != len(data):
            return JsonResponse({'error': 'Content length mismatch'}, status=400)

        mode = 'r+b' if os.path.exists(file_path) else 'wb'
        with open(file_path, mode) as f:
            f.seek(offset_val)
            f.write(data)
        return HttpResponse(status=200)

    return JsonResponse({'error': 'Invalid type'}, status=400)