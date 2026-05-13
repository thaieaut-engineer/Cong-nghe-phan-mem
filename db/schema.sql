-- Billiards Manager schema (MySQL 8.0+)

CREATE DATABASE IF NOT EXISTS billiards_manager
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE billiards_manager;

-- Roles / permissions (shared for users + employees)
CREATE TABLE IF NOT EXISTS roles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE,
  base_salary FLOAT NOT NULL DEFAULT 0
);

-- Users (login)
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  role_id INT,
  CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL
);

-- Employees
CREATE TABLE IF NOT EXISTS employees (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  phone VARCHAR(20),
  salary FLOAT DEFAULT 0,
  role_id INT,
  CONSTRAINT fk_employees_role FOREIGN KEY (role_id) REFERENCES roles(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL
);

-- Shifts
CREATE TABLE IF NOT EXISTS shifts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  salary_factor FLOAT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS employee_shifts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  employee_id INT NOT NULL,
  shift_id INT NOT NULL,
  work_date DATE NOT NULL,
  CONSTRAINT fk_emp_shifts_employee FOREIGN KEY (employee_id) REFERENCES employees(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_emp_shifts_shift FOREIGN KEY (shift_id) REFERENCES shifts(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  UNIQUE KEY uq_employee_shift_day (employee_id, shift_id, work_date)
);

-- Table types
CREATE TABLE IF NOT EXISTS table_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE,
  price_per_hour FLOAT NOT NULL DEFAULT 0
);

-- Tables
CREATE TABLE IF NOT EXISTS tables (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE,
  type_id INT,
  status ENUM('empty','playing','maintenance') NOT NULL DEFAULT 'empty',
  CONSTRAINT fk_tables_type FOREIGN KEY (type_id) REFERENCES table_types(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL
);

-- Service types
CREATE TABLE IF NOT EXISTS service_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE,
  image_path VARCHAR(255) NULL
);

-- Services
CREATE TABLE IF NOT EXISTS services (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  price FLOAT NOT NULL DEFAULT 0,
  image_path VARCHAR(255) NULL,
  type_id INT,
  CONSTRAINT fk_services_type FOREIGN KEY (type_id) REFERENCES service_types(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL
);

-- Sessions (playing)
CREATE TABLE IF NOT EXISTS sessions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  table_id INT NOT NULL,
  start_time DATETIME NOT NULL,
  end_time DATETIME NULL,
  total FLOAT NOT NULL DEFAULT 0,
  CONSTRAINT fk_sessions_table FOREIGN KEY (table_id) REFERENCES tables(id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

-- Session services (optional: drinks/food during session)
CREATE TABLE IF NOT EXISTS session_services (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL,
  service_id INT NOT NULL,
  quantity INT NOT NULL DEFAULT 1,
  unit_price FLOAT NOT NULL DEFAULT 0,
  CONSTRAINT fk_ss_session FOREIGN KEY (session_id) REFERENCES sessions(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_ss_service FOREIGN KEY (service_id) REFERENCES services(id)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL UNIQUE,
  total FLOAT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_invoices_session FOREIGN KEY (session_id) REFERENCES sessions(id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

-- Bookings (schedule)
CREATE TABLE IF NOT EXISTS bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  table_id INT NOT NULL,
  customer_name VARCHAR(100) NOT NULL,
  phone VARCHAR(20),
  start_time DATETIME NOT NULL,
  end_time DATETIME NOT NULL,
  note VARCHAR(255),
  CONSTRAINT fk_bookings_table FOREIGN KEY (table_id) REFERENCES tables(id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

-- =====================================================================
-- Mở rộng nghiệp vụ (Members, Power log, Activity log, Group payment,
-- Expense, Inventory, Shift handover)
-- =====================================================================

-- Thẻ thành viên
CREATE TABLE IF NOT EXISTS members (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(40) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  phone VARCHAR(20),
  email VARCHAR(120),
  discount_percent FLOAT NOT NULL DEFAULT 0,
  total_spent FLOAT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Gắn 1 thẻ thành viên vào 1 phiên (áp dụng giảm giá)
CREATE TABLE IF NOT EXISTS session_members (
  session_id INT NOT NULL PRIMARY KEY,
  member_id INT NOT NULL,
  applied_discount_percent FLOAT NOT NULL DEFAULT 0,
  CONSTRAINT fk_sm_session FOREIGN KEY (session_id) REFERENCES sessions(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_sm_member FOREIGN KEY (member_id) REFERENCES members(id)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Lịch sử bật/tắt điện bàn
CREATE TABLE IF NOT EXISTS power_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  table_id INT NOT NULL,
  action ENUM('on','off') NOT NULL,
  user_id INT NULL,
  action_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  note VARCHAR(255),
  CONSTRAINT fk_pl_table FOREIGN KEY (table_id) REFERENCES tables(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_pl_user FOREIGN KEY (user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX idx_pl_table_time (table_id, action_time)
);

-- Lịch sử người dùng (audit / activity log)
CREATE TABLE IF NOT EXISTS activity_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  username VARCHAR(50) NULL,
  action VARCHAR(60) NOT NULL,
  target_type VARCHAR(40),
  target_id INT,
  detail VARCHAR(500),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_al_user FOREIGN KEY (user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX idx_al_user_time (user_id, created_at),
  INDEX idx_al_action (action)
);

-- Nhóm thanh toán (gộp nhiều phiên thanh toán 1 lần)
CREATE TABLE IF NOT EXISTS payment_groups (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  total FLOAT NOT NULL DEFAULT 0,
  created_by INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pg_user FOREIGN KEY (created_by) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS payment_group_invoices (
  payment_group_id INT NOT NULL,
  invoice_id INT NOT NULL,
  PRIMARY KEY (payment_group_id, invoice_id),
  CONSTRAINT fk_pgi_group FOREIGN KEY (payment_group_id) REFERENCES payment_groups(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_pgi_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

-- Quản lý chi phí
CREATE TABLE IF NOT EXISTS expenses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  category VARCHAR(60) NOT NULL,
  amount FLOAT NOT NULL DEFAULT 0,
  expense_date DATE NOT NULL,
  note VARCHAR(255),
  created_by INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_exp_user FOREIGN KEY (created_by) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX idx_exp_date (expense_date)
);

-- Quản lý kho
CREATE TABLE IF NOT EXISTS inventory_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  unit VARCHAR(20) NOT NULL DEFAULT 'cái',
  stock FLOAT NOT NULL DEFAULT 0,
  min_stock FLOAT NOT NULL DEFAULT 0,
  cost_price FLOAT NOT NULL DEFAULT 0,
  service_id INT NULL,
  CONSTRAINT fk_inv_service FOREIGN KEY (service_id) REFERENCES services(id)
    ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS inventory_movements (
  id INT AUTO_INCREMENT PRIMARY KEY,
  item_id INT NOT NULL,
  movement_type ENUM('in','out','adjust') NOT NULL,
  quantity FLOAT NOT NULL DEFAULT 0,
  ref_type VARCHAR(40),
  ref_id INT,
  note VARCHAR(255),
  created_by INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_im_item FOREIGN KEY (item_id) REFERENCES inventory_items(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_im_user FOREIGN KEY (created_by) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX idx_im_item_time (item_id, created_at)
);

-- Giao ca: bàn giao tiền/tình trạng giữa nhân viên
CREATE TABLE IF NOT EXISTS shift_handovers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  from_user_id INT NULL,
  to_user_id INT NULL,
  handover_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  cash_amount FLOAT NOT NULL DEFAULT 0,
  note VARCHAR(255),
  CONSTRAINT fk_sh_from FOREIGN KEY (from_user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_sh_to FOREIGN KEY (to_user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL
);

