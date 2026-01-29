from django.contrib.auth.models import User, Group, AbstractUser
from django.db import models

from common.utils import get_uuid


# Create your models here.

class HeartBeat(models.Model):
    """
    心跳测试模型
    """
    peer_id = models.CharField(max_length=255, verbose_name='ID máy khách', unique=True)
    modified_at = models.DateTimeField(verbose_name='Thời gian sửa đổi')
    uuid = models.CharField(max_length=255, verbose_name='UUID thiết bị', unique=True)
    timestamp = models.DateTimeField(verbose_name='Thời gian ghi')
    ver = models.CharField(max_length=255, default='', null=True, verbose_name='Phiên bản')

    class Meta:
        verbose_name = 'Kiểm tra nhịp tim'
        verbose_name_plural = verbose_name
        ordering = ['-modified_at']
        db_table = 'heartbeat'
        unique_together = [['uuid', 'peer_id']]


class PeerInfo(models.Model):
    """
    客户端上报的客户端信息模型
    """
    peer_id = models.CharField(max_length=255, verbose_name='ID máy khách', unique=True)
    cpu = models.TextField(verbose_name='Thông tin CPU')
    device_name = models.CharField(max_length=255, verbose_name='Tên máy chủ')
    memory = models.CharField(max_length=50, verbose_name='Bộ nhớ')
    os = models.TextField(verbose_name='Hệ điều hành')
    username = models.CharField(max_length=255, verbose_name='Tên người dùng', default='None')
    uuid = models.CharField(max_length=255, unique=True, verbose_name='UUID thiết bị')
    # uuid = models.ForeignKey(HeartBeat, to_field='uuid', on_delete=models.CASCADE, verbose_name='设备UUID')
    version = models.CharField(max_length=50, verbose_name='Phiên bản máy khách')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian ghi')

    class Meta:
        verbose_name = 'Thông tin máy khách báo cáo'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        db_table = 'peer_info'
        unique_together = [['uuid', 'peer_id']]

    def __str__(self):
        return f'{self.device_name}-({self.uuid})'


class Personal(models.Model):
    """
    地址簿
    """
    guid = models.CharField(max_length=50, verbose_name='GUID', default=get_uuid, unique=True)
    personal_name = models.CharField(max_length=50, verbose_name='Tên danh bạ')
    create_user_id = models.ForeignKey(User, to_field='id', on_delete=models.CASCADE,
                                       related_name='personal_create_user')
    personal_type = models.CharField(verbose_name='Loại danh bạ', default='public',
                                     choices=[('public', 'Công khai'), ('private', 'Riêng tư')])
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')

    class Meta:
        verbose_name = 'Danh bạ'
        verbose_name_plural = 'Danh bạ'
        ordering = ['-created_at']
        db_table = 'personal'
        unique_together = [['personal_name', 'create_user_id']]


class Tag(models.Model):
    """
    标签模型
    """
    # id = models.AutoField(primary_key=True)
    tag = models.CharField(max_length=255, verbose_name='Tên thẻ')
    color = models.CharField(max_length=50, verbose_name='Màu thẻ')
    guid = models.CharField(max_length=50, verbose_name='GUID')

    class Meta:
        verbose_name = 'Thẻ'
        db_table = 'tag'
        unique_together = [['tag', 'guid']]

    def __str__(self):
        return f'{self._meta.db_table}--{self.tag, self.color, self.guid}'


class ClientTags(models.Model):
    """
    标签模型
    """
    user_id = models.ForeignKey(User, to_field='id', on_delete=models.CASCADE, verbose_name='Tên người dùng',
                                related_name='user_tags')
    peer_id = models.CharField(max_length=255, verbose_name='ID thiết bị')
    tags = models.CharField(max_length=255, verbose_name='Tên thẻ')
    guid = models.CharField(max_length=50, verbose_name='GUID')

    class Meta:
        verbose_name = 'Thẻ'
        db_table = 'client_tags'
        unique_together = [['peer_id', 'guid']]

    def __str__(self):
        return f'{self._meta.db_table}--{self.user_id, self.peer_id, self.tags, self.guid}'


class Token(models.Model):
    """
    令牌模型
    """
    user_id = models.ForeignKey(User, to_field='id', on_delete=models.CASCADE, verbose_name='Tên người dùng')
    # user_id = models.ForeignKey(User, to_field='id', on_delete=models.CASCADE, verbose_name='用户名')
    # uuid = models.ForeignKey(PeerInfo, to_field='uuid', on_delete=models.CASCADE, verbose_name='设备UUID')
    uuid = models.CharField(max_length=255, verbose_name='UUID thiết bị')
    token = models.CharField(max_length=255, verbose_name='Mã thông báo')
    client_type = models.CharField(max_length=255, verbose_name='Loại máy khách',
                                   choices=[(1, 'web'), (2, 'client'), (3, 'api')], default='client')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')
    last_used_at = models.DateTimeField(auto_now=True, verbose_name='Thời gian sử dụng cuối')

    class Meta:
        verbose_name = 'Mã thông báo (Token)'
        verbose_name_plural = 'Mã thông báo (Token)'
        ordering = ['-created_at']
        db_table = 'token'
        unique_together = [['user_id', 'uuid']]

    def __str__(self):
        return f'{self.user_id} ({self.uuid}-{self.token})'


class LoginClient(models.Model):
    """
    登录客户端模型
    """
    user_id = models.ForeignKey(User, to_field='id', on_delete=models.CASCADE, verbose_name='Tên người dùng')
    peer_id = models.CharField(max_length=255, verbose_name='ID máy khách')
    # uuid = models.ForeignKey(PeerInfo, to_field='uuid', on_delete=models.CASCADE, verbose_name='设备UUID')
    uuid = models.CharField(max_length=255, verbose_name='UUID thiết bị')
    client_type = models.CharField(max_length=255, verbose_name='Loại máy khách',
                                   choices=[(1, 'web'), (2, 'client')], default=2)
    platform = models.CharField(max_length=255, verbose_name='Nền tảng',
                                choices=[(1, 'Windows'), (2, 'MacOS'), (3, 'Linux'), (4, 'Android'), (5, 'iOS'),
                                         (6, 'Web')],
                                null=True)
    client_name = models.CharField(max_length=255, verbose_name='Tên máy khách', default='', blank=True)
    login_status = models.BooleanField(default=True, verbose_name='Trạng thái đăng nhập')

    class Meta:
        verbose_name = 'Máy khách đăng nhập'
        verbose_name_plural = 'Máy khách đăng nhập'
        ordering = ['-user_id']
        db_table = 'login_client'


class Log(models.Model):
    """
    日志模型
    """
    user_id = models.ForeignKey(User, to_field='id', on_delete=models.CASCADE, verbose_name='Tên người dùng', null=True,
                                default='')
    uuid = models.ForeignKey(PeerInfo, to_field='uuid', on_delete=models.CASCADE, verbose_name='UUID thiết bị')
    log_level = models.CharField(max_length=50, verbose_name='Loại nhật ký',
                                 choices=[('info', 'Thông tin'), ('warning', 'Cảnh báo'), ('error', 'Lỗi')])
    operation_type = models.CharField(max_length=50, verbose_name='Loại thao tác',
                                      choices=[('add', 'Thêm'), ('delete', 'Xóa'), ('update', 'Cập nhật'),
                                               ('query', 'Truy vấn'), ('other', 'Khác')])
    operation_object = models.CharField(max_length=50, verbose_name='Đối tượng thao tác',
                                        choices=[('tag', 'Thẻ'), ('client', 'Thiết bị'), ('user', 'Người dùng'),
                                                 ('token', 'Mã thông báo'), ('login_client', 'Máy khách đăng nhập'),
                                                 ('login_log', 'Nhật ký đăng nhập'), ('log', 'Nhật ký'),
                                                 ('tag_to_client', 'Quan hệ thẻ và thiết bị'), ('user_to_tag', 'Quan hệ người dùng và thẻ'),
                                                 ('system_info', 'Thông tin hệ thống'), ('heart_beat', 'Gói nhịp tim'),
                                                 ('config', 'Cấu hình'), ('file', 'Tệp tin'),
                                                 ('file_to_client', 'Quan hệ tệp tin và thiết bị'),
                                                 ('file_to_tag', 'Quan hệ tệp tin và thẻ'), ('file_to_user', 'Quan hệ tệp tin và người dùng'),
                                                 ('file_to_file', 'Quan hệ tệp tin và tệp tin')])
    operation_result = models.CharField(max_length=50, verbose_name='Kết quả thao tác',
                                        choices=[('success', 'Thành công'), ('fail', 'Thất bại')])
    operation_detail = models.TextField(verbose_name='Chi tiết thao tác', null=True, default='')
    operation_time = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian thao tác')

    class Meta:
        verbose_name = 'Nhật ký'
        verbose_name_plural = 'Nhật ký'
        ordering = ['-operation_time']
        db_table = 'log'


class AutidConnLog(models.Model):
    """
    审计日志模型
    """
    action = models.CharField(max_length=50, verbose_name='Loại thao tác')
    conn_id = models.IntegerField(verbose_name='ID kết nối')
    initiating_ip = models.CharField(max_length=50, verbose_name='IP khởi tạo')
    session_id = models.CharField(max_length=50, verbose_name='ID phiên', null=True)
    controller_uuid = models.CharField(max_length=255, verbose_name='UUID thiết bị điều khiển', null=True)
    controlled_uuid = models.CharField(max_length=255, verbose_name='UUID thiết bị bị điều khiển')
    type = models.IntegerField(verbose_name='Loại', default=0,
                               choices=[(0, 'connect'), (1, 'file_transfer'), (2, 'tcp_tunnel'), (3, 'camera')])
    user_id = models.CharField(max_length=50, verbose_name='Người dùng khởi tạo kết nối', null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')

    class Meta:
        verbose_name = 'Nhật ký kiểm toán'
        verbose_name_plural = 'Nhật ký kiểm toán'
        ordering = ['-created_at']
        db_table = 'audit_log'

    def __str__(self):
        return f'{self.action} {self.conn_id} {self.initiating_ip} {self.session_id} {self.controller_uuid} {self.controlled_uuid} {self.type} {self.user_id} {self.created_at}'


class AuditFileLog(models.Model):
    """
    审计文件模型
    """
    conn_id = models.IntegerField(verbose_name='ID kết nối', null=True)
    source_id = models.CharField(max_length=255, verbose_name='ID thiết bị điều khiển')
    target_id = models.CharField(max_length=255, verbose_name='ID thiết bị bị điều khiển')
    target_uuid = models.CharField(max_length=255, verbose_name='UUID thiết bị bị điều khiển')
    target_ip = models.CharField(max_length=255, verbose_name='IP thiết bị bị điều khiển')
    operation_type = models.IntegerField(verbose_name='Loại thao tác', default=1, choices=[(1, 'upload'), (0, 'download')])
    is_file = models.BooleanField(verbose_name='Là tệp tin')
    remote_path = models.CharField(verbose_name='Đường dẫn từ xa', null=True)
    file_info = models.TextField(verbose_name='Thông tin tệp tin', null=True)
    user_id = models.CharField(max_length=50, verbose_name='Người dùng thao tác', null=True)
    file_num = models.IntegerField(verbose_name='Số lượng tệp tin', null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')

    class Meta:
        verbose_name = 'Tệp tin kiểm toán'
        verbose_name_plural = 'Tệp tin kiểm toán'
        ordering = ['-created_at']
        db_table = 'audit_file'


class UserPrefile(models.Model):
    """
    用户配置模型
    """
    user = models.OneToOneField(User, to_field='id', on_delete=models.CASCADE, related_name='userprofile')
    group = models.ForeignKey(Group, to_field='id', on_delete=models.CASCADE, related_name='userprofile_group')

    class Meta:
        verbose_name = 'Hồ sơ người dùng'
        verbose_name_plural = 'Hồ sơ người dùng'
        db_table = 'user_profile'

    def __str__(self):
        return f'{self.user.username} {self.group.name if self.group else "None"}'


class UserPersonal(models.Model):
    """
    用户与个人地址簿关系模型
    """
    user = models.ForeignKey(User, to_field='id', on_delete=models.CASCADE, related_name='user_personal')
    personal = models.ForeignKey(Personal, to_field='id', on_delete=models.CASCADE, related_name='personal_user')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')

    class Meta:
        verbose_name = 'Quan hệ người dùng và danh bạ cá nhân'
        verbose_name_plural = 'Quan hệ người dùng và danh bạ cá nhân'
        ordering = ['-created_at']
        db_table = 'user_personal'


class PeerPersonal(models.Model):
    """
    设备与个人地址簿关系模型
    """
    peer = models.ForeignKey(PeerInfo, to_field='id', on_delete=models.CASCADE, related_name='peer_personal')
    personal = models.ForeignKey(Personal, to_field='guid', on_delete=models.CASCADE, related_name='personal_peer')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')

    class Meta:
        verbose_name = 'Mô hình quan hệ thiết bị và danh bạ cá nhân'
        verbose_name_plural = 'Mô hình quan hệ thiết bị và danh bạ cá nhân'
        ordering = ['-created_at']
        db_table = 'peer_personal'


class SharePersonal(models.Model):
    """
    分享地址簿记录
    """
    guid = models.CharField(max_length=50, verbose_name='guid')
    to_share_id = models.CharField(max_length=50, verbose_name='ID người được chia sẻ (Người dùng hoặc Nhóm)')
    from_share_id = models.CharField(max_length=50, verbose_name='ID người chia sẻ (Người dùng hoặc Nhóm)')
    to_share_type = models.IntegerField(verbose_name='Loại người được chia sẻ (1: Người dùng, 2: Nhóm)',
                                        choices=[(1, 'Người dùng'), (2, 'Nhóm người dùng')])
    from_share_type = models.IntegerField(verbose_name='Loại người chia sẻ (1: Người dùng, 2: Nhóm)',
                                          choices=[(1, 'Người dùng'), (2, 'Nhóm người dùng')])
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')

    class Meta:
        verbose_name = 'Ghi chép chia sẻ danh bạ'
        verbose_name_plural = 'Ghi chép chia sẻ danh bạ'
        ordering = ['-created_at']
        db_table = 'share_personal'
        unique_together = [['guid', 'to_share_id']]  # 限定一个地址簿只能分享给同一个人一次


class Alias(models.Model):
    """
    别名模型
    """
    alias = models.CharField(max_length=50, verbose_name='Tên gợi nhớ')
    peer_id = models.ForeignKey(PeerInfo, to_field='peer_id', on_delete=models.CASCADE,
                                related_name='alias_peer_id')
    guid = models.ForeignKey(Personal, to_field='guid', on_delete=models.CASCADE, related_name='alias_guid')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')

    class Meta:
        verbose_name = 'Tên gợi nhớ'
        verbose_name_plural = 'Tên gợi nhớ'
        ordering = ['-created_at']
        db_table = 'alias'
        unique_together = [['alias', 'peer_id', 'guid']]  # alias在guid中只能对一个设备进行设置


class UserConfig(models.Model):
    """
    用户配置模型
    """
    user_id = models.OneToOneField(User, to_field='id', on_delete=models.CASCADE, related_name='user_config')
    config_name = models.CharField(max_length=50, verbose_name='Tên cấu hình')
    config_value = models.TextField(verbose_name='Giá trị cấu hình')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')

    class Meta:
        verbose_name = 'Cấu hình người dùng'
        verbose_name_plural = 'Cấu hình người dùng'
        ordering = ['-created_at']
        db_table = 'user_config'
        unique_together = [['user_id', 'config_name']]