# Digital Lost and Found MVP

A simple Django MVP for reporting and tracking lost and found items in a university environment.

## Setup

Create the virtual environment:

```powershell
py -m venv --system-site-packages .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run migrations:

```powershell
python manage.py migrate
```

Create an admin user:

```powershell
python manage.py createsuperuser
```

Start the server:

```powershell
python manage.py runserver
```

Open:

- App: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`
