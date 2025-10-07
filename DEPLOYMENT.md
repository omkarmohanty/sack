# SACK Tool Deployment Guide

## Quick Start

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate   # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database setup:**
   ```bash
   python manage.py makemigrations resource_manager
   python manage.py migrate
   ```

4. **Create sample data:**
   ```bash
   python manage.py create_sample_data --users 5 --resources 10
   ```

5. **Run development server:**
   ```bash
   python manage.py runserver
   ```

6. **Access the application:**
   - URL: http://127.0.0.1:8000/
   - Admin: admin / admin123
   - Users: user1, user2, etc. / password123

... (truncated)