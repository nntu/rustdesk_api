<div align="center">

# RustDesk API Server

[English](./README_EN.md) | [中文](./README.md) | Tiếng Việt

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Django Version](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

Một máy chủ API RustDesk đầy đủ tính năng cung cấp xác thực máy khách, quản lý thiết bị, quản lý sổ địa chỉ, nhật ký kiểm toán và hơn thế nữa.

</div>

---

## 📖 Mục lục

- [Tính năng](#tính-năng)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Bắt đầu nhanh](#bắt-đầu-nhanh)
    - [Yêu cầu](#yêu-cầu)
    - [Triển khai Docker (Khuyên dùng)](#triển-khai-docker-khuyên-dùng)
    - [Triển khai thủ công](#triển-khai-thủ-công)
- [Cấu hình](#cấu-hình)
- [Tài liệu API](#tài-liệu-api)
    - [API máy khách](#api-máy-khách)
    - [API quản lý Web](#api-quản-lý-web)
- [Mô hình cơ sở dữ liệu](#mô-hình-cơ-sở-dữ-liệu)
- [Hướng dẫn phát triển](#hướng-dẫn-phát-triển)
- [Câu hỏi thường gặp](#câu-hỏi-thường-gặp)
- [Đóng góp](#đóng-góp)
- [Giấy phép](#giấy-phép)

## ✨ Tính năng

### Tính năng cốt lõi

- 🔐 **Hệ thống xác thực người dùng** - Hỗ trợ đăng ký người dùng, đăng nhập, quản lý mã thông báo (token)
- 💓 **Phát hiện nhịp tim** - Giám sát thời gian thực trạng thái trực tuyến của máy khách
- 📊 **Thu thập thông tin hệ thống** - Tự động thu thập và lưu trữ thông tin hệ thống máy khách
- 🏷️ **Quản lý thẻ thiết bị** - Hỗ trợ nhóm thiết bị và quản lý thẻ
- 📒 **Quản lý sổ địa chỉ** - Hỗ trợ sổ địa chỉ cá nhân và chia sẻ
- 📝 **Nhật ký kiểm toán** - Ghi lại nhật ký kết nối và chuyển tập tin
- 🌐 **Hỗ trợ đa ngôn ngữ** - Hỗ trợ giao diện tiếng Trung và tiếng Anh
- 🎨 **Giao diện quản trị Web** - Cung cấp trang quản trị web thân thiện

### Tính năng kỹ thuật

- 🚀 **Hiệu suất cao** - Dựa trên Django + Gunicorn, hỗ trợ đa tiến trình và đa luồng
- 🐳 **Triển khai container** - Hỗ trợ Docker đầy đủ
- 💾 **Hỗ trợ đa cơ sở dữ liệu** - Hỗ trợ SQLite, MySQL, PostgreSQL
- 🔧 **Cấu hình linh hoạt** - Cấu hình dễ dàng thông qua biến môi trường
- 📱 **Đa nền tảng** - Hỗ trợ Windows, macOS, Linux

## 🏗️ Kiến trúc hệ thống

```
rustdesk_api/
├── apps/
│   ├── client_apis/      # Giao diện API máy khách
│   │   ├── views.py      # Các view API cốt lõi
│   │   ├── view_ab.py    # API sổ địa chỉ
│   │   └── view_audit.py # API nhật ký kiểm toán
│   ├── web/              # Giao diện quản trị Web
│   │   ├── view_auth.py  # View xác thực
│   │   ├── view_home.py  # View trang chủ
│   │   ├── view_user.py  # Quản lý người dùng
│   │   └── view_personal.py # Quản lý sổ địa chỉ
│   ├── db/               # Mô hình và dịch vụ cơ sở dữ liệu
│   │   ├── models.py     # Định nghĩa mô hình dữ liệu
│   │   └── service.py    # Lớp dịch vụ cơ sở dữ liệu
│   ├── commands/         # Lệnh quản lý
│   └── common/           # Middleware chung
├── common/               # Tiện ích chung
│   ├── db_config.py      # Cấu hình cơ sở dữ liệu
│   ├── env.py            # Quản lý biến môi trường
│   ├── logging_config.py # Cấu hình ghi nhật ký
│   └── utils.py          # Hàm tiện ích
├── static/               # Tập tin tĩnh
├── templates/            # Tập tin mẫu
└── rustdesk_api/         # Cấu hình dự án Django
```

## 🚀 Bắt đầu nhanh

### Yêu cầu

- Python 3.13+
- Docker & Docker Compose (để triển khai container)
- SQLite / MySQL / PostgreSQL (cơ sở dữ liệu)

### Triển khai Docker (Khuyên dùng)

1. **Sao chép dự án**

```bash
git clone https://github.com/yourusername/rustdesk_api.git
cd rustdesk_api
```

2. **Khởi động dịch vụ**

```bash
docker-compose up -d
```

3. **Truy cập dịch vụ**

- Dịch vụ API: `http://localhost:21114`
- Quản trị Web: `http://localhost:21114/web/`

Dịch vụ sẽ tự động hoàn tất di chuyển và khởi tạo cơ sở dữ liệu.

### Triển khai thủ công

1. **Sao chép dự án**

```bash
git clone https://github.com/yourusername/rustdesk_api.git
cd rustdesk_api
```

2. **Tạo môi trường ảo**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. **Cài đặt các phụ thuộc**

```bash
pip install -r requirements.txt
```

4. **Cấu hình biến môi trường**

```bash
# Tạo tập tin .env hoặc thiết lập biến môi trường
export DATABASE=sqlite3
export DEBUG=False
export WORKERS=4
export THREADS=8
```

5. **Di chuyển cơ sở dữ liệu**

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

6. **Tạo tài khoản quản trị viên**

```bash
python manage.py createsuperuser
```

7. **Khởi động dịch vụ**

```bash
# Phát triển
python manage.py runserver 0.0.0.0:21114

# Sản xuất
./start.sh
```

## ⚙️ Cấu hình

### Biến môi trường

| Biến              | Mô tả                     | Mặc định        | Tùy chọn                         |
|-------------------|---------------------------|-----------------|----------------------------------|
| `DATABASE`        | Loại cơ sở dữ liệu        | `sqlite3`       | `sqlite3`, `mysql`, `postgresql` |
| `DEBUG`           | Chế độ gỡ lỗi             | `False`         | `True`, `False`                  |
| `HOST`            | Địa chỉ lắng nghe         | `0.0.0.0`       | Bất kỳ IP hợp lệ nào             |
| `PORT`            | Cổng lắng nghe            | `21114`         | 1-65535                          |
| `WORKERS`         | Số lượng worker Gunicorn  | `4`             | Khuyên dùng 2-8                  |
| `THREADS`         | Luồng trên mỗi worker     | `8`             | Khuyên dùng 2-16                 |
| `SESSION_TIMEOUT` | Thời gian chờ phiên (giây)| `3600`          | Bất kỳ số nguyên dương nào       |
| `TZ`              | Múi giờ                   | `Asia/Shanghai` | Tên múi giờ tiêu chuẩn           |

### Cấu hình cơ sở dữ liệu

#### SQLite (Mặc định)

```bash
export DATABASE=sqlite3
```

Tập tin dữ liệu nằm tại `./data/db.sqlite3`

#### MySQL

```bash
export DATABASE=mysql
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=rustdesk
export MYSQL_PASSWORD=yourpassword
export MYSQL_DATABASE=rustdesk_api
```

#### PostgreSQL

```bash
export DATABASE=postgresql
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=rustdesk
export POSTGRES_PASSWORD=yourpassword
export POSTGRES_DB=rustdesk_api
```

## 📡 Tài liệu API

### API máy khách

#### Xác thực

**Đăng nhập**

```http
POST /api/client/login
Content-Type: application/json

{
    "username": "user",
    "password": "pass",
    "uuid": "device-uuid"
}
```

**Đăng xuất**

```http
POST /api/client/logout
Authorization: Bearer <token>
```

**Lấy người dùng hiện tại**

```http
GET /api/client/currentUser
Authorization: Bearer <token>
```

#### Quản lý thiết bị

**Nhịp tim**

```http
POST /api/client/heartbeat
Authorization: Bearer <token>

{
    "uuid": "device-uuid",
    "peer_id": "peer-id",
    "ver": "1.2.3"
}
```

**Báo cáo thông tin hệ thống**

```http
POST /api/client/sysinfo
Authorization: Bearer <token>

{
    "uuid": "device-uuid",
    "peer_id": "peer-id",
    "cpu": "Intel Core i7",
    "memory": "16GB",
    "os": "Windows 11",
    "device_name": "MyComputer",
    "username": "user",
    "version": "1.2.3"
}
```

**Lấy danh sách thiết bị**

```http
GET /api/client/peers
Authorization: Bearer <token>
```

#### Quản lý sổ địa chỉ

**Lấy danh sách sổ địa chỉ**

```http
GET /api/client/ab
Authorization: Bearer <token>
```

**Lấy sổ địa chỉ cá nhân**

```http
GET /api/client/ab/personal
Authorization: Bearer <token>
```

**Thêm thiết bị vào sổ địa chỉ**

```http
POST /api/client/ab/peer/add/{guid}
Authorization: Bearer <token>

{
    "peer_id": "peer-id",
    "alias": "device-alias"
}
```

**Cập nhật thông tin thiết bị**

```http
PUT /api/client/ab/peer/update/{guid}
Authorization: Bearer <token>

{
    "peer_id": "peer-id",
    "alias": "new-alias"
}
```

**Xóa thiết bị**

```http
DELETE /api/client/ab/peer/{guid}?peer_id={peer_id}
Authorization: Bearer <token>
```

**Lấy danh sách thẻ**

```http
GET /api/client/ab/tags/{guid}
Authorization: Bearer <token>
```

**Thêm/Cập nhật thẻ**

```http
POST /api/client/ab/tag/add/{guid}
Authorization: Bearer <token>

{
    "name": "tag-name",
    "color": "#FF0000"
}
```

**Đổi tên thẻ**

```http
PUT /api/client/ab/tag/rename/{guid}
Authorization: Bearer <token>

{
    "old_name": "old-tag",
    "new_name": "new-tag"
}
```

#### Nhật ký kiểm toán

**Lấy nhật ký kết nối**

```http
GET /api/client/audit/conn
Authorization: Bearer <token>
```

**Lấy nhật ký chuyển tập tin**

```http
GET /api/client/audit/file
Authorization: Bearer <token>
```

### API quản lý Web

#### Xác thực

```http
POST /web/login
GET  /web/logout
```

#### Quản lý thiết bị

```http
GET  /web/home                    # Trang chủ
POST /web/device/rename-alias     # Đổi tên thiết bị
GET  /web/device/detail           # Chi tiết thiết bị
POST /web/device/update           # Cập nhật thiết bị
GET  /web/device/statuses         # Trạng thái thiết bị
```

#### Quản lý người dùng

```http
POST /web/user/create             # Tạo người dùng
POST /web/user/update             # Cập nhật người dùng
POST /web/user/reset-password     # Đặt lại mật khẩu
POST /web/user/delete             # Xóa người dùng
```

#### Quản lý sổ địa chỉ

```http
GET  /web/personal/list           # Danh sách sổ địa chỉ
POST /web/personal/create         # Tạo sổ địa chỉ
POST /web/personal/delete         # Xóa sổ địa chỉ
POST /web/personal/rename         # Đổi tên sổ địa chỉ
GET  /web/personal/detail         # Chi tiết sổ địa chỉ
POST /web/personal/add-device     # Thêm thiết bị
POST /web/personal/remove-device  # Xóa thiết bị
POST /web/personal/update-alias   # Cập nhật bí danh
POST /web/personal/update-tags    # Cập nhật thẻ
```

## 💾 Mô hình cơ sở dữ liệu

### Mô hình cốt lõi

| Mô hình         | Mô tả                            |
|-----------------|----------------------------------|
| `User`          | Tài khoản người dùng (Django)    |
| `Token`         | Mã xác thực người dùng           |
| `HeartBeat`     | Hồ sơ nhịp tim máy khách         |
| `PeerInfo`      | Thông tin hệ thống máy khách     |
| `Personal`      | Sổ địa chỉ                       |
| `Tag`           | Thẻ thiết bị                     |
| `ClientTags`    | Liên kết thẻ thiết bị            |
| `Alias`         | Bí danh thiết bị                 |
| `LoginClient`   | Hồ sơ khách hàng đăng nhập       |
| `Log`           | Nhật ký hoạt động                |
| `AutidConnLog`  | Nhật ký kiểm toán kết nối        |
| `AuditFileLog`  | Nhật ký kiểm toán chuyển tập tin |
| `UserPrefile`   | Hồ sơ người dùng                 |
| `UserPersonal`  | Liên kết sổ địa chỉ người dùng   |
| `PeerPersonal`  | Liên kết sổ địa chỉ thiết bị     |
| `SharePersonal` | Hồ sơ chia sẻ sổ địa chỉ         |
| `UserConfig`    | Mục cấu hình người dùng          |

### Quan hệ cơ sở dữ liệu

```
User
  ├─→ Token
  ├─→ Personal
  ├─→ ClientTags
  ├─→ LoginClient
  └─→ UserConfig

PeerInfo
  ├─→ HeartBeat
  ├─→ PeerPersonal
  ├─→ Alias
  ├─→ AutidConnLog
  └─→ AuditFileLog

Personal
  ├─→ UserPersonal
  ├─→ PeerPersonal
  └─→ SharePersonal
```

## 🔧 Hướng dẫn phát triển

### Phát triển cục bộ

1. **Bật chế độ gỡ lỗi**

```bash
export DEBUG=True
```

2. **Chạy máy chủ phát triển**

```bash
python manage.py runserver
```

3. **Truy cập công cụ gỡ lỗi**

Truy cập `http://localhost:8000/__debug__/` để xem Thanh công cụ gỡ lỗi Django

### Tạo lệnh quản lý

Tạo lệnh mới trong `apps/commands/management/commands/`:

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Mô tả lệnh'
    
    def handle(self, *args, **options):
        # Logic lệnh
        pass
```

Chạy lệnh:

```bash
python manage.py your_command
```

### Di chuyển cơ sở dữ liệu

```bash
# Tạo tập tin di chuyển
python manage.py makemigrations

# Áp dụng di chuyển
python manage.py migrate

# Xem trạng thái di chuyển
python manage.py showmigrations
```

### Tiêu chuẩn mã

- Sử dụng định dạng reStructuredText cho nhận xét hàm
- Tuân theo tiêu chuẩn mã PEP 8
- Đảm bảo tương thích đa nền tảng (Windows, macOS, Linux)

## ❓ Câu hỏi thường gặp

### 1. Lỗi khóa cơ sở dữ liệu

**Vấn đề**: Lỗi khóa cơ sở dữ liệu SQLite

**Giải pháp**:

- Sử dụng MySQL hoặc PostgreSQL
- Giảm các thao tác ghi đồng thời
- Điều chỉnh tham số `WORKERS` và `THREADS`

### 2. Hết hạn phiên

**Vấn đề**: Người dùng cần đăng nhập thường xuyên

**Giải pháp**:

```bash
# Tăng thời gian chờ phiên (giây)
export SESSION_TIMEOUT=86400  # 24 giờ
```

### 3. Vấn đề CORS

**Vấn đề**: Giao diện quản trị Web không thể truy cập API

**Giải pháp**:

- Đảm bảo sử dụng cùng miền và cổng
- Cấu hình middleware CORS (nếu cần)

### 4. Docker Container không khởi động

**Vấn đề**: Docker container không khởi động được

**Giải pháp**:

```bash
# Xem nhật ký
docker logs rustdesk_api

# Xây dựng lại
docker-compose down
docker-compose up --build
```

### 5. Tập tin tĩnh không tải

**Vấn đề**: Tập tin CSS/JS trả về 404

**Giải pháp**:

```bash
# Thu thập lại tập tin tĩnh
python manage.py collectstatic --noinput
```

## 🤝 Đóng góp

Chúng tôi hoan nghênh mọi hình thức đóng góp!

### Quy trình đóng góp

1. Fork kho lưu trữ này
2. Tạo nhánh tính năng (`git checkout -b feature/AmazingFeature`)
3. Commit thay đổi của bạn (`git commit -m 'Add some AmazingFeature'`)
4. Push lên nhánh (`git push origin feature/AmazingFeature`)
5. Mở Pull Request

### Tiêu chuẩn phát triển

- Viết tin nhắn commit rõ ràng
- Thêm các bài kiểm tra cần thiết
- Cập nhật tài liệu liên quan
- Đảm bảo mã vượt qua kiểm tra linting

## 📄 Giấy phép

Dự án này được cấp phép theo Giấy phép MIT - xem tập tin [LICENSE](LICENSE) để biết chi tiết.

## 🙏 Lời cảm ơn

- [RustDesk](https://github.com/rustdesk/rustdesk) - Phần mềm máy tính từ xa tuyệt vời
- [Django](https://www.djangoproject.com/) - Khung web mạnh mẽ
- Tất cả những người đóng góp

## 📮 Liên hệ

- Tác giả: 御风
- Vấn đề: [GitHub Issues](https://github.com/JokerYF/rustdesk_api/issues)

---

<div align="center">

Được làm với ❤️ bởi 御风

[English](./README_EN.md) | [中文](./README.md)

</div>
