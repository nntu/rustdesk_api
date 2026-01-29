import uuid

from django.core.management.base import BaseCommand

from apps.db.service import UserService, GroupService, TokenService, PersonalService
from common.error import UserNotFoundError
from common.utils import str2bool


class Command(BaseCommand):
    help = 'Thao tác quản trị viên'

    user_service = UserService()
    group_service = GroupService()

    def add_arguments(self, parser):
        """添加命令行参数。

        :param parser: 参数解析器对象
        """
        parser.add_argument(
            '--init',
            action='store_true',
            help='Khởi tạo tài khoản quản trị',
        )

        parser.add_argument(
            '--user',
            type=str,
            help='Chỉ định tên người dùng',
        )

        parser.add_argument(
            '--passwd',
            type=str,
            help='Chỉ định mật khẩu người dùng',
        )

        parser.add_argument(
            '--group',
            type=str,
            help='Chỉ định nhóm người dùng',
        )

        parser.add_argument(
            '--personal',
            type=str,
            help='Tạo một danh bạ',
        )

        parser.add_argument(
            '--is-admin',
            type=str,
            help='Là quản trị viên',
        )

    def handle(self, *args, **options):
        """处理命令逻辑。

        :param options: 命令行选项字典
        """

        if options.get('init'):
            pwd = uuid.uuid1().hex[-8:]
            if not self.user_service.get_user_by_name('admin'):
                self.user_service.create_user(
                    username='admin',
                    password=pwd,
                    email='',
                    is_superuser=True,
                    is_staff=True
                )
                print(f'Khởi tạo tài khoản quản trị thành công, mật khẩu: {pwd}')
            else:
                print('Tài khoản quản trị đã tồn tại')

        elif options.get('user'):
            username = options.get('user')
            password = options.get('passwd')
            is_admin = str2bool(options.get('is_admin') or False)

            try:
                if password:
                    user = self.user_service.set_password(password=password, username=username)
                    TokenService().delete_token_by_user(user.username)
                    print(f'Người dùng {username} đã tồn tại, đã cập nhật mật khẩu {password}')
                if is_admin:
                    user = self.user_service.get_user_by_name(username)
                    if not user:
                        raise UserNotFoundError
                    user.is_staff = True
                    user.save()
                    print(f'Người dùng {username} đã tồn tại, đã cập nhật thành quản trị viên')
            except (ValueError, UserNotFoundError):
                if self.user_service.db.objects.count() == 0:
                    is_admin = True
                    print('Do danh sách người dùng trống, khởi tạo người dùng này làm quản trị viên')
                self.user_service.create_user(
                    username=username,
                    password=password,
                    email='',
                    is_superuser=False,
                    is_staff=is_admin
                )
                print(f'Tạo người dùng {username} thành công, mật khẩu {password}')

        elif options.get('group') and options.get('user'):
            group_name = options.get('group')
            user_name = options.get('user')
            self.group_service.add_user_to_group(user_name, group_name=group_name)
        elif options.get('group'):
            group_name = options.get('group')
            self.group_service.create_group(group_name)
        elif personal := options.get('personal'):
            user = self.get_admin_user
            try:
                PersonalService().create_personal(personal_name=personal, create_user=user, personal_type='public')
            except Exception as e:
                print(f'Danh bạ đã tồn tại: {personal}')
        else:
            print('Tham số không hợp lệ')

    @property
    def get_admin_user(self):
        return self.user_service.get_user_by_name('admin')
