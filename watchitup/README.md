⌚ WatchItUp – Django E‑commerce Website

WatchItUp is a full‑stack Django-based e‑commerce web application for selling watches online. The project is designed with a clean separation of concerns, beginner‑friendly structure, and real‑world e‑commerce features such as authentication, product variants, cart, checkout, and payments.

🚀 Project Overview

Project Name: WatchItUp
Domain: E‑commerce (Watches)
Framework: Django (Python)
Architecture: Multi‑app Django project

The application allows users to browse watches for men and women, view product variants (such as color), add items to cart, place orders, and complete payments securely.


🧩 Apps Structure

The project is divided into three main Django apps:

1️⃣ users

Handles all user‑related functionality:

User registration & login

Google SSO (OAuth)

User profile management

Address management

2️⃣ products

Responsible for core e‑commerce features:

Product listing (Men / Women categories)

Product variants (color‑based)

Product images

Search, filter, and sorting

Cart functionality

Orders & checkout

Payment integration (Razorpay)

3️⃣ admin_panel

Custom admin panel for administrators:

Product management

Category management

Order management

User management

Inventory report



✨ Key Features

🔐 User authentication (Email & Google SSO)

🛍️ Browse watches by category (Men / Women)

🎨 Product variants (color‑based)

🖼️ Multiple product images

🔍 Search, filter & sort products

🛒 Cart & checkout system

📍 Address handling during checkout

💳 Razorpay payment integration

🧑‍💼 Custom admin dashboard

🛠️ Technologies Used

Backend: Python, Django

Frontend: HTML, CSS, Bootstrap, JavaScript

Database: PostgreSql

Authentication: Django Auth, Google OAuth

Payments: Razorpay

Version Control: Git & GitHub


This is the Folder structure of my project:


watchitup/
│── users/
│── products/
│── admin_panel/
│── templates/
│── static/
│── manage.py
│── requirements.txt

👩‍💻 Author

Ayisha Safa N
Python Django Developer (Beginner → Intermediate)
