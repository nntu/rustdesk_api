import ast
import json
import logging
from datetime import timedelta
from typing import TypeVar

from django.contrib.auth.models import User, Group
from django.db import models
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest

from apps.db.models import (
    HeartBeat,
    PeerInfo,
    Token,
    LoginClient,
    Tag,
    Log,
    AutidConnLog,
    AuditFileLog,
    UserPrefile,
    Personal,
    Alias,
    ClientTags,
    SharePersonal,
)
from common.error import UserNotFoundError
from common.utils import get_local_time, get_randem_md5

logger = logging.getLogger(__name__)

# Định nghĩa biến kiểu generic cho các model
ModelType = TypeVar("ModelType", bound=models.Model)


class BaseService:
    """
    Lớp cơ sở dịch vụ dữ liệu

    :param db: Model cần thao tác
    """

    db: models.Model = None

    @staticmethod
    def get_user_info(username):
        if isinstance(username, str):
            username = UserService().get_user_by_name(username)
        return username

    @staticmethod
    def get_peer_by_uuid(uuid):
        if isinstance(uuid, str):
            uuid = PeerInfoService().get_peer_info_by_uuid(uuid)
        return uuid

    @staticmethod
    def get_peer_by_peer_id(peer_id):
        if isinstance(peer_id, str):
            peer_id = PeerInfoService().get_peer_info_by_peer_id(peer_id)
        return peer_id


class UserService(BaseService):
    db = User

    def get(self, email) -> User | None:
        try:
            return self.db.objects.get(email=email)
        except self.db.DoesNotExist:
            return None

    def get_users(self, *users, is_active=True):
        _filter = {
            'username__in': [*users],
            'is_active': is_active
        }
        if is_active is None:  # Admin truy vấn: None => lấy toàn bộ
            _filter.pop('is_active')
        return self.db.objects.filter(**_filter).all()

    def create_user(
            self,
            username,
            password,
            email="",
            is_superuser=False,
            is_staff=False,
            is_active=True,
            group: str | Group = None,
    ) -> User:
        user = self.db.objects.create_user(
            username=username,
            email=email,
            is_superuser=is_superuser,
            is_staff=is_staff,
            is_active=is_active,
        )
        user.set_password(password)
        user.save()
        logger.info(f"Tạo người dùng: {user}")

        # Thêm người dùng vào nhóm (đảm bảo đúng thứ tự tham số)
        group_service = GroupService()
        group_service.add_user_to_group(user, group_name=group)

        # Tạo một sổ địa chỉ cá nhân
        PersonalService().create_self_personal(user)

        return user

    def set_user_config(self, username, config_key, config_value):
        qs = self.db.objects.filter(username=username).first()
        qs.user_config.config_name = config_key
        qs.user_config.config_value = config_value
        qs.save()

    def get_user_config(self, username, config_key=None):
        qs = self.db.objects.filter(username=username).first()
        if not qs:
            return None
        return qs.user_config.objects.filter(config_name=config_key)

    def get_user_all_config(self, username):
        qs = self.db.objects.filter(username=username).first()
        if not qs:
            return None
        return qs.user_config.objects.all()

    def get_user_by_email(self, email) -> User:
        return self.db.objects.filter(email=email).first()

    def get_user_by_name(self, username) -> User:
        if isinstance(username, User):
            return username
        return self.db.objects.filter(username=username).first()

    def set_password(self, password, email=None, username=None):
        if username is not None:
            user = self.get_user_by_name(username)
        elif email is not None:
            user = self.get_user_by_email(email)
        else:
            raise ValueError("Either username or email must be provided.")
        if not user:
            raise UserNotFoundError(email or username)
        user.set_password(password)
        user.save()
        logger.info(f"Thiết lập mật khẩu người dùng: {user}")
        return user

    def delete_user(self, *usernames):
        self.db.objects.filter(username__in=[*usernames]).update(is_active=False)
        logger.info(f"Xóa người dùng: {usernames}")

    def __get_list(self, **kwargs):
        """
        Phương thức phân trang dùng chung

        :param filters: Dict điều kiện truy vấn
        :param ordering: Danh sách trường sắp xếp
        :param page: Trang hiện tại
        :param page_size: Số bản ghi mỗi trang
        :return: Dict chứa thông tin phân trang
        """
        page = int(kwargs.pop("page", 1))
        page_size = int(kwargs.pop("page_size", 10))

        filters = kwargs.pop("filters", {})
        is_active = kwargs.pop("is_active", True)
        if is_active is not None:
            filters.update(is_active=is_active)
        queryset = self.db.objects.filter(**filters)

        if ordering := kwargs.pop("ordering", []):
            queryset = queryset.order_by(*ordering)

        total = queryset.count()
        results = queryset[(page - 1) * page_size: page * page_size]

        return {
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    def get_list_by_status(self, is_active, page=1, page_size=10):
        return self.__get_list(is_active=is_active, page=page, page_size=page_size)

    def get_user_by_id(self, user_id) -> User:
        return self.db.objects.filter(id=user_id).first()


class GroupService(BaseService):
    db = Group

    def __init__(self):
        self.default_group_name = "Default"

    def get_group_by_name(self, name) -> Group:
        if isinstance(name, str):
            return self.db.objects.filter(name=name).first()
        return name

    def get_group_by_id(self, id) -> Group:
        if isinstance(id, str):
            return self.db.objects.filter(id=id).first()
        return id

    def create_group(self, name, permissions=None) -> Group:
        if permissions is None:
            permissions = []
        group = self.db.objects.create(name=name)
        group.permissions.add(*permissions)
        logger.info(f"Tạo nhóm người dùng: {group}")
        return group

    def default_group(self):
        """
        Tạo nhóm người dùng mặc định
        :return:
        """
        group = self.get_group_by_name(self.default_group_name)
        if not group:
            group = self.create_group(name=self.default_group_name)
        return group

    def add_user_to_group(self, *username: User | str, group_name: Group | str = None):
        """
        Gán nhóm cho người dùng (batch hiệu quả).

        Truy vấn một lần `UserPrefile` hiện có, tách bản ghi cần update/tạo mới,
        dùng `bulk_update` và `bulk_create` để giảm số câu lệnh SQL, đảm bảo
        “mỗi người dùng chỉ thuộc một nhóm”.

        :param username: User object hoặc tên người dùng (hỗ trợ nhiều giá trị)
        :param group_name: Nhóm đích hoặc tên nhóm; rỗng thì dùng nhóm mặc định
        :returns: None
        """
        group_name = group_name or self.default_group_name
        group = self.get_group_by_name(group_name)
        if not group:
            group = self.default_group()

        user_service = UserService()
        user_objs: list[User] = []
        for item in username:
            if isinstance(item, User):
                user_objs.append(item)
            elif isinstance(item, str):
                if u := user_service.get_user_by_name(item):
                    user_objs.append(u)
            else:
                continue

        if not user_objs:
            return

        user_ids = [u.id for u in user_objs]

        with transaction.atomic():
            # Đọc một lần các Profile đã có
            existing_profiles = UserPrefile.objects.filter(user_id__in=user_ids)
            user_id_to_profile = {p.user_id: p for p in existing_profiles}

            to_update: list[UserPrefile] = []
            to_create: list[UserPrefile] = []

            for u in user_objs:
                if u.id in user_id_to_profile:
                    profile = user_id_to_profile[u.id]
                    if profile.group_id != group.id:
                        profile.group = group
                        to_update.append(profile)
                else:
                    to_create.append(UserPrefile(user=u, group=group))

            if to_update:
                UserPrefile.objects.bulk_update(to_update, ["group"])
                # logger.info(f"Cập nhật nhóm người dùng: {to_update}")
            if to_create:
                UserPrefile.objects.bulk_create(to_create)
                # logger.info(f"Tạo nhóm người dùng: {to_create}")


class PeerInfoService(BaseService):
    db = PeerInfo

    def get_peer_info_by_uuid(self, uuid):
        return self.db.objects.filter(uuid=uuid).first()

    def get_peer_info_by_peer_id(self, peer_id):
        return self.db.objects.filter(peer_id=peer_id).first()

    def update(self, uuid: str, **kwargs):
        """
        Tạo hoặc cập nhật thông tin hệ thống

        :param uuid: Mã định danh thiết bị
        :param kwargs: Các trường thông tin hệ thống
        :return: Tuple (created, object)
        """
        kwargs["uuid"] = uuid
        peer_id = kwargs.get("peer_id")

        if not self.db.objects.filter(Q(uuid=uuid) | Q(peer_id=peer_id)).update(**kwargs):
            self.db.objects.create(**kwargs)

        logger.info(f"Cập nhật thông tin thiết bị: {kwargs}")

    def get_list(self):
        return self.db.objects.all()

    def get_peers(self, *peers):
        return self.db.objects.filter(peer_id__in=peers).all()


class HeartBeatService(BaseService):
    db = HeartBeat

    def update(self, uuid, **kwargs):
        """
        Cập nhật hoặc tạo bản ghi heartbeat

        :param uuid: UUID thiết bị
        :param kwargs: Trường cần cập nhật, ví dụ peer_id, ver...
        :returns:
        """
        kwargs["modified_at"] = get_local_time()
        kwargs["timestamp"] = get_local_time()
        kwargs["uuid"] = uuid
        peer_id = kwargs.get("peer_id")

        if not self.db.objects.filter(Q(uuid=uuid) | Q(peer_id=peer_id)).update(**kwargs):
            self.db.objects.create(**kwargs)
        logger.info(f"Cập nhật heartbeat: {kwargs}")

    def is_alive(self, uuid, timeout=60):
        client = self.db.objects.filter(uuid=uuid).first()
        if client and get_local_time() - client.modified_at < timeout:
            return True
        return False


class LoginClientService(BaseService):
    """
    Dịch vụ client đăng nhập

    Xử lý logic liên quan đến client đăng nhập
    """

    db = LoginClient

    @property
    def platform(self):
        return {
            'windows': 1,
            'macos': 2,
            'linux': 3,
            'android': 4,
            'ios': 5,
            'web': 6,
            'api': 7,
        }

    @staticmethod
    def client_type(client_type: str):
        _type = 1 if client_type.lower() == 'web' else 2
        return _type

    def update_login_status(self, username, uuid, platform, client_name, client_type='api', peer_id=None):
        user_qs = self.get_user_info(username)
        if not self.db.objects.filter(user_id=user_qs.id, uuid=uuid).update(
                user_id=user_qs,
                uuid=uuid,
                peer_id=peer_id,
                login_status=True,
                client_type=self.client_type(client_type),
                platform=self.platform[platform],
                client_name=client_name,
        ):
            self.db.objects.create(
                user_id=user_qs,
                uuid=uuid,
                peer_id=peer_id,
                login_status=True,
                client_type=client_type,
                platform=platform,
                client_name=client_name,
            )

        logger.info(f"Cập nhật trạng thái đăng nhập: {username} - {uuid}")

    def update_logout_status(self, username, uuid, peer_id=None):
        user_qs = self.get_user_info(username)
        if not user_qs or not uuid:
            logger.warning(
                "Cập nhật trạng thái đăng xuất thất bại: user=%s uuid=%s peer_id=%s",
                username,
                uuid,
                peer_id,
            )
            return

        update_fields = {
            "user_id": user_qs,
            "uuid": uuid,
            "login_status": False,
        }
        if peer_id:
            update_fields["peer_id"] = peer_id

        updated = self.db.objects.filter(user_id=user_qs.id, uuid=uuid).update(**update_fields)
        if not updated:
            login_qs = self.db.objects.filter(
                user_id=user_qs,
                uuid=uuid,
                login_status=True
            ).first()
            if not login_qs:
                logger.warning(
                    "Cập nhật trạng thái đăng xuất thất bại: không tìm thấy bản ghi đăng nhập user=%s uuid=%s",
                    username,
                    uuid,
                )
                return

            resolved_peer_id = peer_id or login_qs.peer_id
            if not resolved_peer_id:
                logger.warning(
                    "Cập nhật trạng thái đăng xuất thất bại: thiếu peer_id user=%s uuid=%s",
                    username,
                    uuid,
                )
                return

            self.db.objects.create(
                user_id=user_qs,
                uuid=uuid,
                peer_id=resolved_peer_id,
                login_status=False,
                client_type=login_qs.client_type,
                platform=login_qs.platform,
                client_name=login_qs.client_name,
            )

        logger.info(f"Cập nhật trạng thái đăng xuất: {username} - {uuid}")

    def get_login_client_list(self, username):
        return self.db.objects.filter(user_id=self.get_user_info(username).id).all()


class TokenService(BaseService):
    """
    Dịch vụ token

    Xử lý logic liên quan đến token
    """

    db = Token

    def __init__(self, request: HttpRequest | None = None):
        self.request = request

    def create_token(self, username, uuid, client_type=3):
        """
        Tạo token

        :param username: Tên người dùng
        :param uuid: UUID thiết bị
        :param client_type: Loại client (1, 'web'), (2, 'client'), (3, 'api')
        :return: Token
        """
        assert client_type in [1, 2, 3]
        user_qs = self.get_user_info(username)
        token = f"{get_randem_md5()}_{username}"

        if qs := self.db.objects.filter(user_id=user_qs.id, uuid=uuid, client_type=client_type).first():
            qs.token = token
            qs.created_at = get_local_time()
            qs.last_used_at = get_local_time()
            qs.save()
            logger.info(f"Cập nhật token: user: {username} uuid: {uuid} token: {token}")
        else:
            self.db.objects.create(
                user_id=user_qs,
                uuid=uuid,
                token=token,
                client_type=client_type,
                created_at=get_local_time(),
                last_used_at=get_local_time(),
            )
            logger.info(f"Tạo token: user: {username} uuid: {uuid} token: {token}")
        return token

    def check_token(self, token, timeout=3600):
        if _token := self.db.objects.filter(token=token).first():
            return _token.last_used_at > get_local_time() - timedelta(seconds=timeout)
        self.db.objects.filter(token=token).delete()
        return False

    def update_token(self, token):
        if _token := self.db.objects.filter(token=token).first():
            _token.last_used_at = get_local_time()
            _token.save()
            return True
        return False

    def update_token_by_uuid(self, uuid):
        if _token := self.db.objects.filter(uuid=uuid).first():
            _token.last_used_at = get_local_time()
            _token.save()
            logger.info(f"Cập nhật token theo uuid: {uuid} - {_token.token}")
            return True
        return False

    def delete_token(self, token):
        res = self.db.objects.filter(token=token).delete()
        logger.info(f"Xóa token: {token}")
        return res

    def delete_token_by_uuid(self, uuid):
        res = self.db.objects.filter(uuid=uuid).delete()
        logger.info(f"Xóa token theo uuid: {uuid}")
        return res

    def delete_token_by_user(self, username: User | str):
        user = self.get_user_info(username)
        res = self.db.objects.filter(user_id=user.id).delete()
        logger.info(f"Xóa token theo tên người dùng: {username}")
        return res

    @property
    def authorization(self) -> str | None:
        if self.request:
            return self.request.headers.get("Authorization")[7:]
        return None

    @property
    def user_info(self) -> User | None:
        if self.request:
            auth = self.authorization
            username = auth.split("_")[-1]
            return UserService().get_user_by_name(username)
        return None

    @property
    def client_type(self):
        if self.request:
            auth = self.authorization
            username = auth.split("_")[-2]
            return UserService().get_user_by_name(username)
        return None

    @property
    def request_body(self) -> dict | list:
        if self.request:
            if body := self.request.body:
                return json.loads(body)
        return {}

    @property
    def request_query(self):
        if self.request:
            if params := self.request.GET:
                return params.dict()
        return {}

    def get_cur_uuid_by_token(self, token) -> str | None:
        if peer := self.db.objects.filter(token=token).first():
            return peer.uuid
        return None


class TagService:
    """
    Dịch vụ nhãn (tag)

    Xử lý logic liên quan đến nhãn (tag)
    """

    db_tag = Tag
    db_client = PeerInfo
    db_client_tags = ClientTags

    def __init__(self, guid, user: User | str):
        self.guid = guid
        self.user = UserService().get_user_info(user)

    def get_tags_by_name(self, *tag_name):
        res = self.db_tag.objects.filter(tag__in=tag_name, guid=self.guid).all()
        logger.debug(f"Lấy nhãn người dùng: {self.guid} - {tag_name} - {res}")
        return res

    def get_tags_by_id(self, *tag_id):
        return self.db_tag.objects.filter(id__in=tag_id, guid=self.guid).all()

    def create_tag(self, tag, color):
        res = self.db_tag.objects.create(tag=tag, color=color, guid=self.guid)
        logger.info(f"Tạo nhãn: {self.guid} - {tag} - {color}")
        return res

    def delete_tag(self, *tag):
        """
        Xóa nhãn chỉ định và gỡ khỏi bảng quan hệ (bulk update một lần).

        :param str tag: Một hoặc nhiều tên nhãn cần xóa
        """
        tags_to_delete = {str(t) for t in tag if t is not None}
        if not tags_to_delete:
            return

        # Duyệt một lần để tạo danh sách update, sau đó bulk_update một lần
        changed_instances = []
        for inst in self.db_client_tags.objects.filter(guid=self.guid).all():
            current_tags = self._parse_tags(inst.tags)
            if not current_tags:
                continue
            new_tags = [t for t in current_tags if t not in tags_to_delete]
            if new_tags != current_tags:
                # Ghi lại theo định dạng JSON
                inst.tags = json.dumps(new_tags)
                changed_instances.append(inst)

        if changed_instances:
            self.db_client_tags.objects.bulk_update(changed_instances, ["tags"])

        # Xóa nhãn
        self.db_tag.objects.filter(tag__in=tags_to_delete, guid=self.guid).delete()
        logger.info(f"Xóa nhãn: {self.guid} - {tags_to_delete}")

    def update_tag(self, tag, color=None, new_tag=None):
        data = {}
        if color:
            data["color"] = color
        if new_tag:
            data["tag"] = new_tag
        res = self.db_tag.objects.filter(tag=tag, guid=self.guid).update(**data)
        logger.info(f"Cập nhật nhãn: {self.guid} - {data}")
        return res

    def get_all_tags(self):
        """
        Lấy tất cả nhãn liên kết với người dùng hiện tại

        :return: QuerySet of Tag objects associated with the current user
        """
        return self.db_tag.objects.filter(guid=self.guid).all()

    def set_user_tag_by_peer_id(self, peer_id, tags):
        """
        Gán nhãn cho thiết bị (ghi đè).

        :param peer_id: peer_id thiết bị
        :param tags: Danh sách nhãn
        :returns: Bản ghi được cập nhật hoặc tạo mới
        """
        tag_list = []
        for tag in self.get_tags_by_name(*list(tags)):
            tag_list.append(tag.id)

        # if qs := self.db_client_tags.objects.filter(peer_id=peer_id, guid=self.guid).first():
        if qs := self.user.user_tags.filter(peer_id=peer_id, guid=self.guid).first():
            qs.tags = str(tag_list if tag_list else [])
            return qs.save()

        kwargs = {
            "peer_id": peer_id,
            "tags": str(tag_list),
            "guid": self.guid,
        }
        res = self.user.user_tags.create(**kwargs)
        logger.info(f"Gán nhãn: {self.guid} - {peer_id} - {tag_list if tag_list else []}")
        return res

    def del_tag_by_peer_id(self, *peer_id):
        """
        Xóa bản ghi nhãn của thiết bị chỉ định.

        :param peer_id: Một hoặc nhiều peer_id thiết bị
        :returns: Kết quả xóa (rows_deleted, details)
        """
        res = self.user.user_tags.filter(peer_id__in=peer_id, guid=self.guid).delete()
        logger.info(f"Xóa nhãn: {self.guid} - {peer_id}")
        return res

    def get_tags_by_peer_id(self, peer_id) -> list[str]:
        """
        Lấy danh sách nhãn của một thiết bị.

        :param peer_id: peer_id thiết bị
        :returns: Danh sách nhãn; không có thì trả về []
        """
        row = self.user.user_tags.filter(peer_id=peer_id, guid=self.guid).values("tags").first()
        if not row:
            return []
        return self._parse_tags(row.get("tags"))

    def get_tags_map(self, peer_ids: list[str]) -> dict[str, list[str]]:
        """
        Lấy map nhãn cho nhiều thiết bị, tránh truy vấn N+1.

        :param peer_ids: Danh sách `peer_id` thiết bị
        :returns: Map {peer_id: [tag, ...]}
        """
        if not peer_ids:
            return {}
        rows = self.db_client_tags.objects.filter(guid=self.guid, peer_id__in=peer_ids).values("peer_id", "tags")
        logger.debug(f"Lấy nhãn theo batch: {self.guid} peers: {peer_ids} result: {rows}")
        result: dict[str, list[str]] = {}
        for row in rows:
            tags = eval(row.get("tags") or '[]')
            tags_qs = self.get_tags_by_id(*tags)
            logger.debug(f"Nhãn: {self.guid} peers: {row['peer_id']} tags: {tags} result: {tags_qs}")
            if not tags_qs:
                continue
            result[row["peer_id"]] = [str(tag.tag) for tag in tags_qs]
        logger.debug(f"Kết quả lấy nhãn batch: guid: {self.guid} peers: {peer_ids} result: {result}")
        return result

    @staticmethod
    def _parse_tags(raw) -> list[str]:
        """
        Phân tích trường nhãn lưu trong DB.

        Hỗ trợ chuỗi list đã serialize và chuỗi JSON.

        :param raw: Giá trị lưu gốc (chuỗi hoặc list)
        :returns: Danh sách nhãn
        """
        if raw is None:
            return []
        if isinstance(raw, list):
            return [str(x) for x in raw]
        s = str(raw).strip()
        if not s:
            return []
        # Ưu tiên thử JSON
        try:
            val = json.loads(s)
            if isinstance(val, list):
                return [str(x) for x in val]
        except Exception:
            pass
        # Fallback sang literal_eval an toàn
        try:
            val = ast.literal_eval(s)
            if isinstance(val, list):
                return [str(x) for x in val]
        except Exception:
            pass
        return []


class LogService(BaseService):
    """
    Dịch vụ log

    Xử lý logic liên quan đến log
    """

    db = Log

    def create_log(self, username, uuid, log_type, log_level="info", log_message=""):
        """
        Tạo bản ghi log

        :param username: Tên người dùng
        :param uuid: UUID thiết bị
        :param log_type: Loại log
        :param log_level: Mức log
        :param log_message: Nội dung log
        :return: Bản ghi log mới
        """
        log = self.db.objects.create(
            user_id=self.get_user_info(username).id,
            uuid=uuid,
            log_level=log_level,
            operation_type=log_type,  # Map theo nhu cầu thực tế
            operation_object="log",  # Đối tượng thao tác theo nhu cầu
            operation_result="success",  # Giả định tạo log luôn thành công
            operation_detail=log_message,
            operation_time=get_local_time(),
        )
        logger.info(
            f'Tạo log: user="{username}", UUID="{uuid}", loại="{log_type}", mức="{log_level}", nội dung="{log_message}"'
        )
        return log


class AuditConnService(BaseService):
    """
    Dịch vụ audit kết nối

    Xử lý logic liên quan đến audit kết nối
    """

    db = AutidConnLog

    def get(self, conn_id, action="new") -> AutidConnLog:
        return self.db.objects.filter(conn_id=conn_id, action=action).first()

    def log(
            self,
            conn_id,
            action,
            controlled_uuid,
            source_ip,
            session_id,
            controller_peer_id=None,
            type_=0,
            username=None
    ):
        """
        Ghi log
        :param username:
        :param type_:
        :param controller_peer_id:
        :param conn_id:
        :param action:
        :param controlled_uuid:
        :param source_ip:
        :param session_id:
        :return:
        """
        if username:
            user_info = self.get_user_info(username)
            user_id = user_info.id if user_info else ''
        else:
            user_id = ''
        if action:
            if action == "new":
                self.db.objects.create(
                    conn_id=conn_id,
                    action=action,
                    controlled_uuid=controlled_uuid,
                    initiating_ip=source_ip,
                    session_id=session_id,
                )
            else:
                connect_log = self.db.objects.filter(
                    conn_id=conn_id,
                    action="new",
                ).first()
                self.db.objects.create(
                    conn_id=conn_id,
                    action=action,
                    controlled_uuid=controlled_uuid,
                    controller_uuid=connect_log.controller_uuid,
                    initiating_ip=connect_log.initiating_ip,
                    session_id=session_id,
                    user_id=connect_log.user_id,
                    type=connect_log.type,
                )
        else:
            self.db.objects.filter(conn_id=conn_id).update(
                session_id=session_id,
                controller_uuid=self.get_peer_by_peer_id(controller_peer_id).uuid,
                user_id=user_id,
                type=type_,
            )
        logger.info(
            f'Audit kết nối: conn_id="{conn_id}", action="{action}", controlled_uuid="{controlled_uuid}", source_ip="{source_ip}", session_id="{session_id}"'
        )


class AuditFileLogService(BaseService):
    """
    Dịch vụ audit file

    Xử lý logic liên quan đến audit file
    """
    db = AuditFileLog

    @property
    def conn_service(self):
        return AuditConnService()

    @property
    def conn_id(self):
        qs = self.conn_service.db.objects.first()
        if qs.type == 1:
            return qs.conn_id
        return None

    def log(
            self,
            source_id,
            target_id,
            target_uuid,
            target_ip,
            operation_type,
            is_file,
            remote_path,
            file_info,
            user_id,
            file_num,
    ):
        res = self.db.objects.create(
            conn_id=self.conn_id,
            source_id=source_id,
            target_id=target_id,
            target_uuid=target_uuid,
            target_ip=target_ip,
            operation_type=operation_type,
            is_file=is_file,
            remote_path=remote_path,
            file_info=file_info,
            user_id=user_id,
            file_num=file_num,
        )
        logger.info(
            f'Audit file: source_id="{source_id}", target_id="{target_id}", target_uuid="{target_uuid}", operation_type="{operation_type}", is_file="{is_file}", remote_path="{remote_path}", user_id="{user_id}", file_num="{file_num}"'
        )
        return res


class PersonalService(BaseService):
    db = Personal

    def create_personal(self, personal_name, create_user, personal_type="public"):
        qs = self.get_user_info(create_user)
        personal = self.db.objects.create(
            personal_name=personal_name,
            create_user_id=qs,
            personal_type=personal_type,
        )
        personal.personal_user.create(user=create_user)
        logger.info(
            f'Tạo sổ địa chỉ: name: {personal_name}, create_user: {create_user}, type: {personal_type}, guid: {personal.guid}'
        )
        return personal

    def create_self_personal(self, username):
        qs = self.get_user_info(username)
        personal = self.create_personal(
            personal_name=f'{username}_personal',
            create_user=qs,
            personal_type="private"
        )
        return personal

    def get_personal(self, guid):
        return self.db.objects.filter(guid=guid).first()

    def get_all_personal(self):
        return self.db.objects.all()

    def get_peers_by_personal(self, guid):
        personal = self.get_personal(guid=guid)
        if personal:
            return personal.personal_peer.all()
        return []

    def delete_personal(self, guid):
        personal = self.get_personal(guid=guid)
        if personal and personal.personal_type != "private":
            logger.info(f'Xóa sổ địa chỉ: {personal.personal_name} - {personal.personal_name}')
            return personal.delete()
        logger.info(f'Không có thông tin sổ địa chỉ: {guid}')
        return None

    def add_personal_to_user(self, guid, username):
        user_qs = self.get_user_info(username)
        res = self.get_personal(guid=guid).personal_user.create(user_id=user_qs)
        logger.info(f'Chia sẻ sổ địa chỉ cho người dùng: {guid} - {username}')
        return res

    def del_personal_to_user(self, guid, username):
        user_qs = self.get_user_info(username)
        res = (
            self.get_personal(guid=guid)
            .personal_user.filter(user_id=user_qs)
            .delete()
        )
        logger.info(f'Hủy chia sẻ sổ địa chỉ: guid={guid}, username={username}')
        return res

    def add_peer_to_personal(self, guid, peer_id):
        peer = PeerInfoService().get_peer_info_by_peer_id(peer_id)
        return self.get_personal(guid=guid).personal_peer.create(peer=peer)

    def del_peer_to_personal(self, guid, peer_id: list | str, user):
        if isinstance(peer_id, str):
            peer_id = [peer_id]
        peers = PeerInfoService().get_peers(*peer_id)

        # Xóa alias
        alias_service = AliasService()
        alias_service.delete_alias(*peers, guid=guid)

        # Xóa tag
        tag_service = TagService(guid=guid, user=user)
        tag_service.del_tag_by_peer_id(*peer_id)
        res = self.get_personal(guid=guid).personal_peer.filter(peer__in=peers).delete()
        logger.info(f'Gỡ thiết bị khỏi sổ địa chỉ: guid={guid}, peer_ids={peer_id}')
        return res


class AliasService(BaseService):
    db = Alias

    def set_alias(self, peer_id, alias, guid):
        """
        Đặt hoặc cập nhật alias của thiết bị trong sổ địa chỉ.

        :param str peer_id: `peer_id` của thiết bị
        :param str alias: Alias cần đặt
        :param str guid: GUID sổ địa chỉ
        :returns: None
        """
        # Lưu ý: `peer_id` và `guid` là ForeignKey.
        # Nếu gán trực tiếp chuỗi sẽ bị coi là đối tượng liên kết,
        # cần dùng cột `<field>_id` để ghi giá trị gốc.
        kwargs = {
            "peer_id_id": peer_id,
            "guid_id": guid,
            "alias": alias,
        }
        updated = self.db.objects.filter(peer_id_id=peer_id, guid_id=guid).update(**kwargs)
        if not updated:
            self.db.objects.create(**kwargs)
        logger.info(f'Đặt alias: peer_id="{peer_id}", alias="{alias}", guid="{guid}"')

    def get_alias(self, guid):
        return self.db.objects.filter(guid=guid).all()

    def get_alias_map(self, guid: str, peer_ids: list[str]) -> dict[str, str]:
        """
        Lấy map alias cho nhiều thiết bị trong sổ địa chỉ.

        :param guid: GUID sổ địa chỉ
        :param peer_ids: Danh sách `peer_id` thiết bị
        :returns: Map {peer_id: alias}; thiết bị chưa có alias sẽ không xuất hiện
        """
        if not peer_ids:
            return {}
        rows = self.db.objects.filter(guid=guid, peer_id__in=peer_ids).values("peer_id", "alias")
        return {row["peer_id"]: row["alias"] for row in rows}

    def delete_alias(self, *peer_ids, guid):
        return self.db.objects.filter(guid=guid, peer_id__in=peer_ids).delete()


class SharePersonalService(BaseService):
    db = SharePersonal

    def __init__(self, count_user: User):
        self.user = count_user

    def share_to_user(self, guid, username):
        user = PersonalService().get_user_info(username)
        return self.db.objects.create(
            guid=guid,
            to_share_id=user.id,
            to_share_type=1,
            from_share_id=self.user.id,
            from_share_type=1,
        )

    def share_to_group(self, guid, group_name):
        group = GroupService().get_group_by_name(group_name)
        return self.db.objects.create(
            guid=guid,
            to_share_id=group.id,
            to_share_type=2,
            from_share_id=self.user.id,
            from_share_type=1,
        )

    def get_user_personals(self):
        profile = getattr(self.user, "userprofile", None)
        if not profile:
            group = GroupService().default_group()
            profile, _ = UserPrefile.objects.get_or_create(
                user=self.user,
                defaults={"group": group},
            )
            if profile.group_id is None:
                profile.group = group
                profile.save(update_fields=["group"])
        group_id = profile.group_id
        personal_ids = self.db.objects.filter(
            to_share_id__in=(self.user.id, group_id),
            to_share_type__in=(1, 2),
        ).values_list("guid", flat=True)

        return PersonalService.db.objects.filter(guid__in=personal_ids).all()


class UserConfig(BaseService):
    def __init__(self, user: User | str):
        self.user = self.get_user_info(user)

    def get_config(self):
        return self.user.user_config.objects.all()

    def set_language(self, language):
        self.user.user_config.objects.update_or_create(
            user=self.user,
            defaults={
                "config_name": 'language',
                "config_value": language
            }
        )

    def get_language(self):
        if qs := self.user.user_config.objects.filter(config_name='language').first():
            return qs.config_value
        return None
