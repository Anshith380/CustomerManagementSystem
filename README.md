# Customer Management System (CRM)

A web-based Customer Relationship Management application built using **Python, Streamlit, and MySQL**. The system helps manage customers, leads, tasks, opportunities, user permissions, and audit logs through a centralized dashboard.

## Project Overview

The Customer Management System (CRM) is designed to organize customer information and support business workflows in one application. It provides a dashboard for monitoring customer activity and dedicated modules for managing sales-related records and tasks.

The application includes role-based access control and audit logging to help protect data and track user actions.

## Key Features

- **Dashboard:** View customer statistics, lead conversion information, task summaries, and opportunity pipeline metrics.
- **Customer Management:** Add, view, edit, and archive customer records.
- **Lead Management:** Manage leads and track their statuses.
- **Opportunity Management:** Track sales opportunities and their stages.
- **Task Management:** Create and manage tasks and monitor their statuses.
- **User Authentication:** Log in to the application securely.
- **Role-Based Access Control:** Apply permissions based on user roles, including admin, manager, and employee.
- **Audit Logging:** Record supported application actions for review and accountability.
- **Reports and Analytics:** Review CRM information through reporting features.
- **MySQL Database:** Store application data in a relational database.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Application logic and backend |
| Streamlit | Web interface |
| MySQL | Relational database |
| MySQL Workbench | Database management |
| Git and GitHub | Version control and source code hosting |
| pytest | Automated testing |

## Project Structure

```text
CustomerManagementSystem/
├── main.py
├── database.py
├── backend.py
├── auth.py
├── user_admin.py
├── lead_backend.py
├── task_backend.py
├── interaction_backend.py
├── opportunity_backend.py
├── audit_backend.py
├── reports.py
├── tests/
├── .env.example
├── .gitignore
└── README.md
```

*Note: The folder structure above is illustrative. Adjust it to match the actual files and folders in your repository.*

## Prerequisites

Install the following before running the application:

- Python
- MySQL Server
- MySQL Workbench (optional, for database administration)
- Git

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Anshith380/CustomerManagementSystem.git
cd CustomerManagementSystem
```

### 2. Create a virtual environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

If the project contains `requirements.txt`, run:

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure the database

Create the MySQL database named `crm_db` and ensure the required tables are initialized according to the project's database setup.

Create a local `.env` file in the project root with your own MySQL connection settings:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_NAME=crm_db
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
```

Replace the example values with your local configuration. Never commit `.env` or publish real passwords, API keys, or other secrets.

### 5. Start the application

Activate your virtual environment and run:

```powershell
streamlit run main.py
```

Open the local URL displayed in the terminal, usually:

```text
http://localhost:8501
```

## Testing

Run the automated tests from the project root:

```powershell
python -m pytest -q
```

The project previously reported **27 passing tests** in the development environment. Run the tests again after making changes to verify the current result.

## Security

- Store database credentials in environment variables.
- Keep `.env` excluded from Git version control.
- Use password hashing and authentication safeguards.
- Enforce role-based permissions for restricted operations.
- Review audit logs to investigate supported user actions.
- Do not commit credentials, private keys, or sensitive production data.

## Future Improvements

- Deploy the application to a suitable hosting platform.
- Improve reporting and visualization.
- Add automated backups and database recovery procedures.
- Expand automated testing and security checks.
- Improve the user interface and documentation.

## Author

**Project:** Customer Management System (CRM)

**Repository:** [GitHub - CustomerManagementSystem](https://github.com/Anshith380/CustomerManagementSystem)

## License

Add a license if you intend to distribute this project publicly. Until then, the repository's licensing terms should be clarified before others reuse the code.
