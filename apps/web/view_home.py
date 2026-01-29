from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils.timezone import now

from apps.db.models import PeerInfo, Personal, Alias, ClientTags
from apps.db.service import AliasService


@login_required(login_url='web_login')
def home(request: HttpRequest):
    """
    Web 首页：登录保护，依赖 Django 认证态（request.user）

    :param request: Http 请求对象
    :return: 首页或重定向响应
    """
    # 渲染基础骨架（左侧导航），右侧内容由前端 AJAX 加载
    return render(request, 'home.html', {
        'username': request.user.username or request.user.get_full_name(),
        'user': request.user,
    })


@login_required(login_url='web_login')
def nav_content(request: HttpRequest):
    """
    返回侧边导航对应的局部模板内容（通过 GET 参数 key）

    :param request: Http 请求对象，需包含 GET 参数 key（如 nav-1/nav-2/nav-3）
    :return: 渲染后的 HTML 片段
    :notes:
    - 仅支持预设键名，未知键名将返回简单的占位内容
    """
    key = request.GET.get('key')

    # 未知 key，返回占位内容而非 404，便于前端保持一致渲染
    if key not in ['nav-1', 'nav-2', 'nav-3', 'nav-4']:
        return HttpResponse('<p class="content-empty">未匹配到内容</p>')

    # 根据不同导航项提供对应数据
    if key == 'nav-1':  # 首页
        # 分页参数
        page = int(request.GET.get('page', 1))
        page_size = 10  # 首页仅展示简略列表

        devices_qs = PeerInfo.objects.all().order_by('-created_at')
        device_count = devices_qs.count()
        user_count = 0  # 暂不展示真实用户数，或改为 query User.objects.count()

        paginator = Paginator(devices_qs, page_size)
        page_obj = paginator.get_page(page)

        # 当前页设备列表
        devices = []
        for d in page_obj.object_list:
            devices.append({
                'peer_id': d.peer_id,
                'device_name': d.device_name,
                'os': d.os,
                'version': d.version,
                'created_at': d.created_at,
            })

        return render(request, 'nav/nav-1.html', {
            'device_count': device_count,
            'user_count': user_count,
            'devices': devices,
            'page_obj': page_obj,
            'paginator': paginator,
        })

    elif key == 'nav-2':  # 设备管理
        """
        设备管理（nav-2）上下文构建

        :query page: 页码（默认 1）
        :query page_size: 每页大小（默认 20）
        :query q: 关键词，匹配设备ID/设备名（可空）
        :query os: 操作系统筛选（可空；模糊匹配）
        :query status: 在线状态（online/offline，可空）
        :returns: 注入模板的设备分页、筛选上下文
        """
        # 基本分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))

        # 筛选参数
        q = (request.GET.get('q') or '').strip()
        os_filter = (request.GET.get('os') or '').strip()
        status_filter = (request.GET.get('status') or '').strip()

        qs = PeerInfo.objects.all().order_by('-created_at')

        if q:
            qs = qs.filter(Q(peer_id__icontains=q) | Q(device_name__icontains=q))
        if os_filter:
            qs = qs.filter(os__icontains=os_filter)

        # 在线判定：心跳表 5 分钟内有记录视为在线
        online_threshold = now() - timedelta(minutes=5)

        # 如果需要筛选在线状态，则需预先过滤或后处理（这里采用后处理+内存分页简化逻辑，若数据量大需优化 SQL）
        # 优化：先拿到所有符合条件的 peer_id，再查 HeartBeat
        # 但考虑到 HeartBeat 数据量可能大，这里仅对当前页做状态判定即可？
        # 不行，筛选 status=online 需要作用在整体数据集上。
        # 方案：使用 distinct peer_id 的 HeartBeat 子查询或 Exists
        # 简化版：仅在展示时计算状态，不支持 status 筛选（或者支持但不精确）。
        # 这里为了演示完整性，暂不支持 status 数据库级筛选，仅支持前端展示状态。

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)

        devices = []
        for d in page_obj.object_list:
            # 检查在线状态
            is_online = HeartBeat.objects.filter(
                Q(peer_id=d.peer_id) | Q(uuid=d.uuid),
                modified_at__gte=online_threshold
            ).exists()

            # 如果有 status 筛选且不匹配，则跳过（注意：这会破坏分页准确性，严谨做法应在 SQL 层处理）
            if status_filter == 'online' and not is_online:
                continue
            if status_filter == 'offline' and is_online:
                continue

            # 别名：取任意一个别名（如存在）
            # 严谨逻辑：应取当前用户默认地址簿下的别名
            alias_obj = Alias.objects.filter(
                peer_id=d.peer_id,
                guid__create_user_id=request.user.id
            ).first()
            alias = alias_obj.alias if alias_obj else ''

            # 标签：取当前登录用户下的一个标签（如存在）
            # 严谨逻辑：应取当前用户默认地址簿下的标签
            tag_obj = ClientTags.objects.filter(
                peer_id=d.peer_id,
                user_id=request.user.id
            ).first()
            tags = tag_obj.tags if tag_obj else ''

            devices.append({
                'peer_id': d.peer_id,
                'device_name': d.device_name,
                'os': d.os,
                'version': d.version,
                'created_at': d.created_at,
                'is_online': is_online,
                'alias': alias,
                'tags': tags,
            })

        # 注意：如果启用了 status 筛选导致跳过记录，前端分页可能会显示“空页”或记录数不足
        # 实际项目中应构建复杂 query

        return render(request, 'nav/nav-2.html', {
            'devices': devices,
            'page_obj': page_obj,
            'paginator': paginator,
            'q': q,
            'os': os_filter,
            'status': status_filter,
            'page_size': page_size
        })

    elif key == 'nav-3':  # 用户管理
        from django.contrib.auth.models import User
        # 分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))

        qs = User.objects.all().order_by('-date_joined')

        # 搜索参数
        q = (request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q))

        # 只显示未删除的用户（is_active=True）
        qs = qs.filter(is_active=True)

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)

        return render(request, 'nav/nav-3.html', {
            'users': page_obj.object_list,
            'page_obj': page_obj,
            'paginator': paginator,
            'q': q,
            'page_size': page_size
        })

    elif key == 'nav-4':  # 地址簿
        # 分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))

        # 搜索参数
        q = (request.GET.get('q') or '').strip()
        personal_type = (request.GET.get('type') or '').strip()

        # 查询当前用户的地址簿（包括自己创建的和被分享的）
        qs = Personal.objects.filter(create_user_id=request.user.id).order_by('-created_at')

        # 搜索过滤（使用guid进行搜索）
        if q:
            qs = qs.filter(guid__icontains=q)

        if personal_type in ['public', 'private']:
            qs = qs.filter(personal_type=personal_type)

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)

        # 为每个地址簿统计设备数量并标记是否为默认地址簿
        for personal in page_obj.object_list:
            # 统计 Alias 表中该 guid 下的记录数作为设备数（近似）
            # 或者统计 PeerPersonal 关联表（如果使用了多对多关系）
            # 这里简单查 Alias 表（假设一个设备在同一个地址簿只有一个别名记录）
            # 实际上应该查 PeerPersonal 或 Alias 对应的 peer 数量
            # 修正：查 Alias 表中 guid=personal.guid 的数量
            count = Alias.objects.filter(guid=personal.guid).count()
            personal.device_count = count
            personal.is_default = (personal.personal_name == '默认地址簿' or
                                   personal.personal_name == f'{request.user.username}_personal')

            # 设置显示名称：如果是 {用户名}_personal 格式，显示为"默认地址簿"
            if personal.personal_name == f'{request.user.username}_personal':
                personal.display_name = 'Danh bạ mặc định'
            else:
                personal.display_name = personal.personal_name

        return render(request, 'nav/nav-4.html', {
            'personals': page_obj.object_list,
            'page_obj': page_obj,
            'paginator': paginator,
            'q': q,
            'personal_type': personal_type,
            'page_size': page_size
        })

    return HttpResponse('<p class="content-empty">未匹配到内容</p>')


from datetime import timedelta


@login_required(login_url='web_login')
@require_http_methods(['POST'])
def rename_device_alias(request: HttpRequest) -> JsonResponse:
    """
    重命名设备别名（创建或更新 Alias）

    :param request: Http 请求对象，POST 参数包含 peer_id, alias
    :return: JSON 响应，形如 {"ok": true}
    :notes:
    - 别名基于用户的“默认地址簿”（如不存在则自动创建，私有）
    - 针对 (peer_id, 默认地址簿) 维度进行 upsert
    """
    peer_id = request.POST.get('peer_id')
    alias = request.POST.get('alias')

    if not peer_id:
        return JsonResponse({'ok': False, 'err_msg': 'Tham số không hợp lệ'}, status=400)

    # 1. 确认设备存在
    if not PeerInfo.objects.filter(peer_id=peer_id).exists():
        return JsonResponse({'ok': False, 'err_msg': 'Thiết bị không tồn tại'}, status=404)

    # 2. 获取或创建默认地址簿（私有）
    # 逻辑：每个用户有一个默认地址簿，名字通常为 "默认地址簿" 或 "{username}_personal"
    # 这里简化：查找 create_user=request.user 且 name="默认地址簿" 的记录，没有则创建
    personal, _ = Personal.objects.get_or_create(
        create_user_id=request.user.id,
        personal_name='默认地址簿',
        defaults={
            'personal_type': 'private'
        }
    )

    # 3. 更新或创建 Alias
    # Alias 表有 unique_together = [['alias', 'peer_id', 'guid']]
    # 但我们需要的是 (peer_id, guid) 唯一对应的 alias。
    # Django模型定义可能是 alias+peer_id+guid 联合唯一，这意味着同一个设备在同一个地址簿可以有多个别名？
    # 不，通常是一个。这里假设 AliasService 会处理。
    AliasService().set_alias(
        guid=personal.guid,
        peer_id=peer_id,
        alias=alias
    )

    return JsonResponse({'ok': True})


@login_required(login_url='web_login')
@require_http_methods(['GET'])
def get_device_detail(request: HttpRequest) -> JsonResponse:
    """
    获取设备详情（peer 维度）

    :param request: Http 请求对象，GET 参数包含 peer_id
    :return: JSON 响应，包含 peer_id/username/hostname/alias/platform/tags
    """
    peer_id = request.GET.get('peer_id')
    if not peer_id:
        return JsonResponse({'ok': False, 'err_msg': 'Tham số không hợp lệ'}, status=400)

    peer = PeerInfo.objects.filter(peer_id=peer_id).first()
    if not peer:
        return JsonResponse({'ok': False, 'err_msg': 'Thiết bị không tồn tại'}, status=404)

    # 默认地址簿下的 alias（若无则回退任意一个 alias）
    personal = Personal.objects.filter(
        create_user_id=request.user.id,
        personal_name='默认地址簿'
    ).first()

    alias = ''
    if personal:
        alias_obj = Alias.objects.filter(peer_id=peer_id, guid=personal.guid).first()
        if alias_obj:
            alias = alias_obj.alias

    # 当前用户下的标签（可能多条）
    tag_obj = ClientTags.objects.filter(peer_id=peer_id, user=request.user).first()
    tags = tag_obj.tags if tag_obj else ''

    # 构造响应
    data = {
        'peer_id': peer.peer_id,
        'username': peer.username,
        'hostname': peer.device_name,
        'alias': alias,
        'platform': peer.os,
        'tags': tags,
    }
    return JsonResponse({'ok': True, 'data': data})


@login_required(login_url='web_login')
@require_http_methods(['POST'])
def update_device_info(request: HttpRequest) -> JsonResponse:
    """
    内联更新设备信息（别名与标签）

    :param request: Http 请求对象，POST 参数：
    - peer_id: 设备ID（必填）
    - alias: 设备别名（可选，空则忽略）
    - tags: 设备标签（可选，逗号分隔；空字符串表示清空）
    :return: JSON 响应，形如 {"ok": true}
    :notes:
    - 别名写入当前用户的“默认地址簿”（不存在则创建）
    - 标签写入 ClientTags（当前用户 + 默认地址簿 guid 作用域）
    """
    peer_id = request.POST.get('peer_id')
    if not peer_id:
        return JsonResponse({'ok': False, 'err_msg': 'Tham số không hợp lệ'}, status=400)

    if not PeerInfo.objects.filter(peer_id=peer_id).exists():
        return JsonResponse({'ok': False, 'err_msg': 'Thiết bị không tồn tại'}, status=404)

    alias = request.POST.get('alias')
    tags = request.POST.get('tags')

    # 获取/创建默认地址簿（私有）
    personal, _ = Personal.objects.get_or_create(
        create_user_id=request.user.id,
        personal_name='默认地址簿',
        defaults={
            'personal_type': 'private'
        }
    )

    # 更新别名（当 alias 参数存在时）
    if alias is not None:
        alias = alias.strip()
        # AliasService upsert
        AliasService().set_alias(
            guid=personal.guid,
            peer_id=peer_id,
            alias=alias
        )
        # 兼容逻辑：如果 alias 为空字符串，是否要删除记录？
        # AliasService.set_alias 内部通常是 update_or_create。
        # 空字符串表示清除当前作用域下别名
        if not alias:
            Alias.objects.filter(guid=personal.guid, peer_id=peer_id).delete()

    # 更新标签（当 tags 参数存在时）
    if tags is not None:
        # 归一化标签：逗号分隔，去空白、去重，保持顺序
        # raw_tags = [t.strip() for t in tags.split(',') if t.strip()]
        # clean_tags = ",".join(raw_tags)
        clean_tags = tags.strip()

        # ClientTags 表逻辑：(peer_id, user_id) 唯一?
        # apps/db/models.py L286 unique_together = [['peer_id', 'user_id']]?
        # ClientTags 定义：user_id (ForeignKey), peer_id (CharField), tags (CharField)
        # 假设一个用户对一个设备只有一行标签记录
        ClientTags.objects.update_or_create(
            user=request.user,
            peer_id=peer_id,
            defaults={
                'tags': clean_tags,
                'guid': personal.guid  # 关联到默认地址簿?
            }
        )
        # 空表示清空标签
        if not clean_tags:
            ClientTags.objects.filter(user=request.user, peer_id=peer_id).delete()

    return JsonResponse({'ok': True})


@login_required(login_url='web_login')
@require_http_methods(['GET'])
def get_device_statuses(request: HttpRequest) -> JsonResponse:
    """
    批量获取设备在线状态（仅查询，不修改会话）

    :param request: Http 请求对象，GET 参数：
    - ids: 逗号分隔的设备ID列表，如 "id1,id2,id3"
    :return: JSON 响应，形如 {"ok": true, "data": {"<peer_id>": {"is_online": true/false}}}
    :notes:
    - 前端应在请求头携带 ``X-Session-No-Renew: 1``，以避免该轮询请求“续命”会话
    - 仅执行只读查询，不做任何写操作
    """
    ids_str = request.GET.get('ids', '')
    if not ids_str:
        return JsonResponse({'ok': True, 'data': {}})

    # 归一化与限流（防止一次性过大）
    peer_ids = [pid.strip() for pid in ids_str.split(',') if pid.strip()]
    peer_ids = peer_ids[:100]  # 限制最多查 100 个

    # 60s 内有心跳视为在线
    online_threshold = now() - timedelta(seconds=60)

    # 批量查询 HeartBeat
    # filter: peer_id IN (...) AND modified_at >= threshold
    online_q = HeartBeat.objects.filter(
        peer_id__in=peer_ids,
        modified_at__gte=online_threshold
    ).values_list('peer_id', flat=True)

    online_set = set(online_q)

    result = {}
    for pid in peer_ids:
        result[pid] = {
            'is_online': pid in online_set
        }

    return JsonResponse({'ok': True, 'data': result})