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

## Mobile API Foundation

The project now includes a REST API for a future Capacitor mobile app. The existing Django template web app still works, and the mobile app should call the API instead of reading `db.sqlite3` directly.

Key endpoints:

- Register: `POST /api/auth/register/`
- Login/JWT token: `POST /api/auth/login/`
- Refresh token: `POST /api/auth/token/refresh/`
- Current user: `GET /api/me/`
- Items: `GET /api/items/`, `POST /api/items/`
- Item detail: `GET /api/items/<id>/`
- Submit claim for found item: `POST /api/items/<id>/claims/`
- Claims visible to claimant/reporter/staff: `GET /api/claims/`
- Review claim as reporter/staff: `POST /api/claims/<id>/review/`
- Start conversation: `POST /api/items/<id>/start-conversation/`
- Conversations: `GET /api/conversations/`
- Conversation detail: `GET /api/conversations/<id>/`
- Send message: `POST /api/conversations/<id>/messages/`

Authenticated API requests should send:

```http
Authorization: Bearer <access-token>
```

Privacy rule: regular users browse found items as photo-first cards with only a small found-item label and posted date. Full item details are visible to the reporter, staff, or users already in an existing conversation. Submitting a claim does not reveal hidden details. Claim verification answers are stored hashed and are never returned by the API.

For local mobile development, keep SQLite on the Django server and point the Capacitor app at the Django API. Android emulators usually reach the host machine at `http://10.0.2.2:8000/`; physical devices need your computer's LAN IP and a matching `ALLOWED_HOSTS` entry.

Run tests:

```powershell
python manage.py test
```

## Mobile App Setup

The installable mobile client lives in `mobile/`. It is an Ionic React app wrapped by Capacitor and talks to the Django API over HTTP during local development.

Install mobile dependencies:

```powershell
cd mobile
npm install
```

Run Django in one terminal:

```powershell
python manage.py runserver
```

Run the mobile web app in another terminal:

```powershell
cd mobile
npm run dev
```

Open the mobile web app at `http://127.0.0.1:5173/`.

Build and sync the Android project:

```powershell
cd mobile
npm run build
npm run cap:sync
npm run cap:android
```

For the Android emulator, the app uses `http://10.0.2.2:8000/api` to reach the Django server on your computer. For a physical Android device, set `VITE_API_URL` to your computer's LAN API URL before building and add that LAN host to `ALLOWED_HOSTS`.

For a physical Android device on the same Wi-Fi/network, first find your computer's LAN IP, then run Django on all interfaces:

```powershell
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost,10.0.2.2,YOUR_COMPUTER_LAN_IP"
python manage.py runserver 0.0.0.0:8000
```

Then rebuild the mobile app with that API URL:

```powershell
cd mobile
$env:VITE_API_URL = "http://YOUR_COMPUTER_LAN_IP:8000/api"
npm run build
npm run cap:sync
npm run cap:android
```

If the app shows "Could not reach the Django API", check that Windows Firewall allows Python/Django on port `8000`, the phone and computer are on the same network, and the app was rebuilt after setting `VITE_API_URL`.

Android builds require Android Studio and a JDK. If you build from the command line, make sure `JAVA_HOME` points to your Java installation.

On this machine, Android Studio's bundled JDK is available at:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
```

The local Android SDK path is stored in the ignored file `mobile/android/local.properties`:

```properties
sdk.dir=C\:\\Sdk
```

This project currently pins Capacitor 7 because this machine has Node 20.14. Upgrade Node before moving to Capacitor 8.
