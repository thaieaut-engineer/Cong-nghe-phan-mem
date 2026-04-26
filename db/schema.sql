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

