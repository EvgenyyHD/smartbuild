# SmartBuild

SmartBuild is a Dockerized web application for construction planning: estimates, schedules, procurement, materials, project teams, participant requests, goals, and subgoals.

## Run With Docker On Linux

Requirements:

- Docker Engine
- Docker Compose plugin

Download and start:

```bash
git clone https://github.com/EvgenyyHD/smartbuild.git
cd smartbuild
cp .env.example .env
nano .env
docker compose up --build -d
```

Or use the helper script:

```bash
chmod +x scripts/start-smartbuild.sh
./scripts/start-smartbuild.sh
```

Open:

```text
http://localhost
```

If port 80 is busy, set another port in `.env`:

```env
HTTP_PORT=8080
ALLOWED_HOSTS=localhost,127.0.0.1
```

Then restart:

```bash
docker compose down
docker compose up --build -d
```

Open:

```text
http://localhost:8080
```

## Run On A Server Domain

In `.env`, set:

```env
POSTGRES_DB=smartbuild
POSTGRES_USER=smartbuild
POSTGRES_PASSWORD=replace-with-strong-password
SECRET_KEY=replace-with-long-random-secret
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
HTTP_PORT=80
DEBUG=False
```

Start:

```bash
docker compose up --build -d
```

## Demo Accounts

All seeded demo users use this password:

```text
SmartBuild2026!
```

Useful accounts:

```text
admin@smartbuild.local
owner@severstroy.local
foreman@severstroy.local
builder@severstroy.local
client@personal.local
supplier@monolit-resource.local
supplier@finish-pro.local
```

## Maintenance

View containers:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

Stop:

```bash
docker compose down
```

Stop and delete database volume:

```bash
docker compose down -v
```

Run backend tests:

```bash
docker compose exec backend python manage.py test
```
