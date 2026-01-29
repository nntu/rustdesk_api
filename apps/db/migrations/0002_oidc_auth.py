from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OidcAuth',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=64, unique=True, verbose_name='Mã xác thực')),
                ('op', models.CharField(max_length=255, verbose_name='Nhà cung cấp OIDC')),
                ('peer_id', models.CharField(max_length=255, verbose_name='ID máy khách')),
                ('uuid', models.CharField(max_length=255, verbose_name='UUID thiết bị')),
                ('device_info', models.TextField(default='', null=True, verbose_name='Thông tin thiết bị')),
                ('status', models.CharField(
                    choices=[('pending', 'Đang chờ'), ('approved', 'Đã xác thực'), ('expired', 'Hết hạn')],
                    default='pending',
                    max_length=20,
                    verbose_name='Trạng thái',
                )),
                ('access_token', models.CharField(blank=True, max_length=255, null=True, verbose_name='Mã thông báo')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')),
                ('expires_at', models.DateTimeField(verbose_name='Thời gian hết hạn')),
                ('user_id', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Tên người dùng',
                )),
            ],
            options={
                'verbose_name': 'OIDC xác thực',
                'verbose_name_plural': 'OIDC xác thực',
                'db_table': 'oidc_auth',
                'ordering': ['-created_at'],
            },
        ),
    ]
