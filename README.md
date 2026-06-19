# 🏦 BankDB Transaction Monitoring System

A secure and intelligent banking management platform built with **Python, Streamlit, SQLite, and Pandas**. The system provides comprehensive banking operations including customer management, account management, transaction processing, audit logging, security monitoring, and automated fraud detection through high-value transaction alerts.

Designed with **Role-Based Access Control (RBAC)**, the application supports both **Administrator** and **Customer** functionalities while maintaining detailed security and compliance records.

---

## 🚀 Features

### 👨‍💼 Administrator Features

* Customer Management (Create, View, Update, Delete)
* Bank Account Management
* Deposit & Withdrawal Operations
* Transaction Monitoring Dashboard
* High-Value Transaction Alert System
* Security Log Monitoring
* Audit Trail & Activity Tracking
* Locked Account Management
* Branch-wise Financial Reports
* Real-Time Banking Statistics

### 👤 Customer Features

* Secure Login
* Create New Bank Accounts
* Deposit Funds
* Withdraw Funds
* Check Account Balance
* View Transaction History
* Access Personal Banking Dashboard

---

## 🔐 Security Features

### Account Protection

* Login attempt monitoring
* Automatic account lock after 3 failed login attempts
* 5-minute temporary account suspension
* Administrator-controlled account unlocking

### Audit Logging

Every administrative action is recorded, including:

* Customer creation
* Customer modification
* Customer deletion
* Account creation
* Account updates
* Account deletion

### Security Event Tracking

The system records:

* Failed login attempts
* Account lock events
* Account unlock events
* Security-related activities

---

## 🚨 Fraud Detection & Monitoring

The application automatically monitors all banking transactions.

### High-Value Transaction Alerts

Whenever a deposit or withdrawal exceeds:

₹50,000

The system automatically:

* Generates a security alert
* Stores alert details in the database
* Displays alerts in the monitoring dashboard

---

## 🛠️ Technology Stack

| Technology      | Purpose                          |
| --------------- | -------------------------------- |
| Python          | Core Application Logic           |
| Streamlit       | Interactive Web Interface        |
| SQLite          | Relational Database              |
| Pandas          | Data Analysis & Reporting        |
| SQL Triggers    | Automated Monitoring & Logging   |
| Decimal Module  | Financial Precision              |
| Datetime Module | Security & Time-Based Operations |

---

## 📂 Database Schema

### Customers Table

Stores customer information and login security data.

| Field           |
| --------------- |
| customer_id     |
| full_name       |
| email           |
| phone           |
| city            |
| failed_attempts |
| lock_until      |

---

### Accounts Table

Stores account details and balances.

| Field          |
| -------------- |
| account_number |
| customer_id    |
| branch         |
| balance        |
| account_type   |

---

### Transactions Table

Maintains transaction records.

| Field            |
| ---------------- |
| transaction_id   |
| account_number   |
| transaction_type |
| amount           |
| transaction_time |

---

### Alerts Table

Stores high-value transaction alerts.

| Field          |
| -------------- |
| alert_id       |
| account_number |
| amount         |
| alert_time     |
| message        |

---

### Admin Logs Table

Maintains administrator activity records.

| Field          |
| -------------- |
| log_id         |
| table_name     |
| operation_type |
| record_id      |
| old_data       |
| new_data       |
| action_time    |

---

### Security Logs Table

Stores authentication and security-related events.

| Field           |
| --------------- |
| log_id          |
| customer_id     |
| event_type      |
| failed_attempts |
| event_time      |
| details         |

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/bankdb-transaction-monitoring-system.git

cd bankdb-transaction-monitoring-system
```

### 2. Install Dependencies

```bash
pip install streamlit pandas
```

### 3. Run the Application

```bash
streamlit run bankapp.py
```

---

## 🔑 Default Administrator Credentials

> These credentials are provided for demonstration and academic purposes.

| Username | Password   |
| -------- | ---------- |
| admin    | admin@1234 |

---

## 📊 System Modules

### Customer Management

* Add Customers
* View Customers
* Edit Customer Information
* Delete Customers

### Account Management

* Create Savings Accounts
* Create Current Accounts
* Update Account Information
* Delete Accounts

### Transaction Management

* Deposit Funds
* Withdraw Funds
* Balance Verification
* Transaction History

### Monitoring & Analytics

* Dashboard Statistics
* Alert Management
* Branch-wise Reports
* Security Monitoring

### Compliance & Auditing

* Admin Logs
* Security Logs
* Transaction Records
* Audit Trail

---

## 🎯 Business Rules

* Minimum account balance must remain **₹1000**
* Account numbers are automatically generated
* Only valid account types are allowed:

  * Savings
  * Current
* High-value transactions (₹50,000+) trigger alerts
* User accounts lock after 3 consecutive failed login attempts

---

## 🖥️ User Interface

The application features:

* Modern Dark Theme UI
* Responsive Layout
* Interactive Data Tables
* Real-Time Dashboard Metrics
* Search & Filter Functionality
* Secure Authentication System

---

## 📚 Educational Concepts Demonstrated

This project demonstrates practical implementation of:

* Database Management Systems (DBMS)
* Banking Information Systems
* Role-Based Access Control (RBAC)
* Database Triggers
* Transaction Processing Systems
* Audit Logging
* Security Monitoring
* Financial Data Management
* Streamlit Web Application Development

---

## 👨‍💻 Author

**Soumyadeep Basu**

Developed as a Banking Transaction Monitoring and Security Management System using Python, Streamlit, SQLite, and Pandas.

---

## 📜 License

This project is developed for educational, academic, and learning purposes.

Feel free to use, modify, and extend the project for personal or academic use.
