STARCLINCH NOTIFICATION SYSTEM
Local Setup and Usage Guide
Backend: Python and Django | Database: Microsoft SQL Server

1. Project Overview
This project is a Django-based notification system for managing notification triggers and message templates. It includes a web interface for notification settings, user login/logout flows, database-backed templates, and provider integrations for Email, Web Push, and WhatsApp.
The code uses Microsoft SQL Server through a custom database utility layer. The SQL schema and data script are expected to be supplied separately; use that file to create the required tables and any initial trigger/user records before running the application.
2. Technology and Main Components
•	Python and Django for the web application and request handling.
•	Microsoft SQL Server, accessed through mssql-django and pyodbc.
•	HTML/CSS/JavaScript templates for the notification settings screen and user login/home pages.
•	Brevo API integration for sending Email notifications.
•	OneSignal integration for browser Web Push notifications.
•	WhatsApp Cloud API integration code, with a mock mode available for development/testing.
3. Prerequisites
•	Windows computer with Python installed (use a Python version compatible with the packages in requirements.txt).
•	Microsoft SQL Server running locally, plus SQL Server Management Studio (SSMS) or another SQL client.
•	Microsoft ODBC Driver 18 for SQL Server installed.
•	The project ZIP extracted to a local folder.
•	The SQL table/schema file supplied with the project.
4. Extract and Open the Project
1.	Extract noti_system(9).zip to a working folder, for example C:\Projects\noti_system.
2.	Open Command Prompt or PowerShell and change directory to the extracted project folder, the folder that contains manage.py.
cd C:\Projects\noti_system
The project folder should contain manage.py, requirements.txt, the noti_system package, adminpanel, common, Templates, and static folders.
5. Create and Activate a Virtual Environment
python -m venv .venv
.venv\Scripts\activate
If Windows blocks activation in PowerShell, use Command Prompt or adjust the local PowerShell execution policy according to your organization's rules.
6. Install Python Dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
The supplied requirements.txt contains a large list of pinned dependencies, including some packages that may be platform-specific or unnecessary for this project. If installation fails, review the exact error and install/fix the required packages in a controlled way rather than changing versions blindly.
7. Configure SQL Server and Create the Tables
3.	Open SQL Server Management Studio and connect to your local SQL Server instance.
4.	Create the database named NotificationDB, or use the database name you intend to configure.
5.	Open and execute the separate SQL schema/table script supplied with the project. Confirm that all tables and any required initial records are created successfully.
6.	Verify that the SQL Server login has permission to connect to the database and read/write the required tables.
The application code refers to tables including NotificationTrigger, NotificationTemplate, NotificationLog, AppUser, and PushSubscription. Confirm that the SQL file creates the tables and columns expected by the code. The Django models file is currently empty, so the application relies on the supplied SQL schema and direct SQL queries rather than Django model definitions.
8. Configure Environment Variables
Create or update a .env file in the project root (the same folder as manage.py). Do not share this file or commit it to Git. Use your own local values; never copy real credentials into the README.
DB_NAME=NotificationDB
DB_USER=your_sql_server_username
DB_PASSWORD=your_sql_server_password
DB_HOST=localhost
DB_PORT=1433
DB_DRIVER=ODBC Driver 18 for SQL Server
BREVO_API_KEY=your_brevo_api_key
BREVO_FROM_EMAIL=your_verified_sender_email
ONESIGNAL_APP_ID=your_onesignal_app_id
ONESIGNAL_REST_API_KEY=your_onesignal_rest_api_key
WHATSAPP_ACCESS_TOKEN=your_meta_test_access_token
PHONE_NUMBER_ID=your_meta_test_phone_number_id
WHATSAPP_API_VERSION=v23.0
WHATSAPP_MOCK_MODE=True
The exact provider variables used by the code are listed above. If your SQL Server uses Windows Authentication or a named instance, adjust the database connection configuration accordingly. The current settings file also contains development-only settings and fallback database credentials; replace those with environment-based configuration before sharing or deploying the project.
9. Start the Django Application
7.	Make sure the virtual environment is active and SQL Server is running.
8.	From the project root, run:
python manage.py check
9.	If the checks pass and the database connection is configured, start the local server:
python manage.py runserver
Open http://127.0.0.1:8000/ in your browser. If the server reports a database, ODBC, or missing-table error, verify the .env values, ODBC driver, SQL Server service, database permissions, and that the SQL script has been executed.
10. Main Pages and API Routes
The following routes are defined in adminpanel/urls.py:
Purpose	Local URL path
Notification settings page	/admin_dashboard
User login page	/login_user
User home page (requires a session)	/user_home
User logout	/logout_user
Fetch notification templates (GET)	/noti_temp
Create notification template (POST)	/noti/temp/manage
Update notification template (PUT)	/update_template
Send Email test (POST)	/email_noti_sending
Send WhatsApp test (POST)	/whatsapp_noti_sending
Send Web Push test (POST)	/webpush_noti_sending
Save browser push subscription (POST)	/save_one_suscrip
OneSignal service worker	/OneSignalSDKWorker.js
11. How to Use the Application
A. Set up notification triggers and templates
10.	Open the Notification Settings page at http://127.0.0.1:8000/admin_dashboard.
11.	Review the trigger rows loaded from NotificationTrigger in SQL Server.
12.	Create or edit a template for the required channel: EMAIL, WEB_PUSH, or WHATSAPP.
13.	For Email templates, provide a subject and message body. For other channels, provide the template name and message body as required by the interface.
14.	Save the template and make sure its IsEnabled setting is enabled before testing.
B. Test Email
Use a template whose Channel is EMAIL and whose IsEnabled value is enabled. Send a POST request to /email_noti_sending with JSON fields TemplateID and Recipient. The configured Brevo sender email must be verified and the API key must be valid.
{"TemplateID": 1, "Recipient": "recipient@example.com"}
The project code submits the email through Brevo and records the result in NotificationLog. A successful provider response means the provider accepted the request; it is not by itself proof of final inbox delivery.
C. Test Web Push
Log in through the application, allow browser notifications, and complete the OneSignal subscription flow. The subscription ID must be saved against the logged-in user's UserID in PushSubscription. Then send a POST request to /webpush_noti_sending with TemplateID and UserID.
{"TemplateID": 2, "UserID": 1}
Use a WEB_PUSH template that is enabled and ensure the OneSignal App ID and REST API key are configured. Browser permissions, HTTPS requirements for non-local environments, and a saved active subscription can affect delivery.
D. Test WhatsApp
The WhatsApp sending function is implemented in the code. In mock mode (WHATSAPP_MOCK_MODE=True), the application prepares a mock result and does not send a real WhatsApp message. To perform a real sandbox test, configure valid Meta WhatsApp Cloud API credentials, an eligible test recipient, a valid phone number ID, and an approved template name.
Project testing note: WhatsApp was not end-to-end verified because the required Meta WhatsApp API access/setup was unavailable due to an issue on the Meta side during testing. The code is present, but a real WhatsApp delivery should be considered unverified until tested successfully with working Meta credentials.
12. Trigger Behaviour
The login and logout views call the notification dispatcher using trigger codes LOGIN and LOGOUT. The dispatcher retrieves active triggers and enabled templates from SQL Server, then attempts the relevant channel. To test these flows, the database must contain matching active trigger records, enabled templates, and a test user with valid contact details.
Other trigger examples in the assignment include inactive-user reminders. Such triggers require an event/scheduler implementation and suitable database records; do not assume that every example trigger is automatically active just because it appears in the assignment brief.
13. Testing Status
•	Email: Reported as working in the developer's test environment. Re-test with the recipient, sender, and Brevo credentials available on the machine where the project is run.
•	Web Push: Reported as working in the developer's test environment. Re-test with OneSignal configuration, browser permission, and an active saved subscription.
•	WhatsApp: Sending code is present, but live API delivery was not verified because Meta API access/setup was unavailable during testing.
•	Local setup: Depends on the separate SQL schema/data file being executed and the environment variables being configured correctly.
14. Troubleshooting
•	ODBC driver / connection error: confirm ODBC Driver 18 is installed, SQL Server is running, and DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME are correct.
•	Invalid object name / table not found: execute the supplied SQL schema script against the configured database and verify the table names.
•	Template not found / disabled: confirm TemplateID exists and IsEnabled is set to 1.
•	Email not sent: verify the Brevo API key, verified sender address, recipient address, and NotificationLog error details.
•	No Web Push subscription: log in, grant browser permission, confirm OneSignal initialization, and verify the subscription is stored as active for the correct UserID.
•	WhatsApp request fails: verify the Meta access token, phone number ID, API version, recipient eligibility, and approved WhatsApp template name. Mock mode does not deliver a real message.
15. Security and Handover Notes
•	Never commit .env, provider tokens, passwords, or other secrets to GitHub.
•	Rotate any API keys or passwords that may have been included in a shared ZIP or repository.
•	Before production use, set DEBUG=False, configure ALLOWED_HOSTS, use a strong environment-provided Django SECRET_KEY, and review CSRF/authentication protections.
•	The current project uses direct SQL queries and an empty adminpanel/models.py; database schema changes should be managed carefully using the supplied SQL scripts.
•	This guide describes local setup. Public deployment needs separate environment, database networking, static-file, HTTPS, and security configuration.
16. Assignment Alignment
The assignment calls for a Django backend, an admin screen for notification triggers/templates, and three notification channels: WhatsApp, Email, and Web Push. This repository contains the Django application, template-management endpoints, login/logout trigger dispatch, Brevo email integration, OneSignal Web Push integration, and WhatsApp sending code. The WhatsApp live-delivery limitation is documented above for transparent review.
Before submission, include the SQL schema/table file, verify that a reviewer can configure the database and environment variables, and provide the repository/live URLs and any walkthrough evidence requested by the assignment.
