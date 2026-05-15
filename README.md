## Billiards Manager (Python + Qt Designer + MySQL)

Ứng dụng quản lý quán bi-a: đăng nhập, quản lý bàn/loại bàn/dịch vụ/nhân viên, phiên chơi, đặt lịch, in hoá đơn PDF, thống kê.

Thành viên:
Q.Duy.Thái (Nhóm trưởng)
T.Hoài.Sơn (Thành viên)
T.Đình.Dũng (Thành viên)

### Yêu cầu

- **Python**: 3.10+ (khuyến nghị 3.11)
- **MySQL**: 8.0+

### Cài đặt

Tạo môi trường ảo và cài thư viện:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

### Cấu hình MySQL

1) Tạo database và bảng:

- Mở file `db/schema.sql` và chạy trong MySQL (Workbench/CLI).

2) Tạo file cấu hình (không commit):

- Copy `app/.env.example` thành `app/.env` rồi sửa thông tin kết nối.

3) Seed dữ liệu mẫu (tạo role + tài khoản admin):

```bash
python db/seed.py
```

### Chạy ứng dụng

```bash
python -m app.main
```

### Tài khoản mặc định

- **username**: `admin`
- **password**: `admin123`

