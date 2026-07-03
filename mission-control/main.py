from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import logging
import docker
import base64
from datetime import datetime, timedelta, timezone
import psycopg2
from collections import deque
import asyncio

# Logging setup
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Config
ADMIN_USERNAME = os.environ.get("BASIC_AUTH_USER", "admin")
ADMIN_PASSWORD = os.environ.get("BASIC_AUTH_PASSWORD", "change_this_password")

# Docker client setup
docker_client = None
try:
    docker_client = docker.from_env()
    docker_client.ping()  # Test connection
    logger.info("Docker client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to connect to Docker daemon: {e}. Ensure docker.sock is mounted.")
    docker_client = None


class SimpleUser:
    def __init__(self, username: str):
        self.identity = username
        self.is_authenticated = True


# FastAPI App Setup
app = FastAPI(
    title="Mission Control Dashboard",
    description="VPS Health, Security, and Application Audit Dashboard",
    version="0.1.0",
    docs_url=None,  # Disable docs for security
    redoc_url=None,
    root_path="/control",
)

# Jinja2 templates for HTML pages
templates = Jinja2Templates(directory="/app/templates")


# Middleware for HTTP Basic Authentication
@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    # Allow access to login page and api/static assets without auth
    # We use request.scope["path"] so it remains agnostic of the root_path prefix
    path = request.scope.get("path", "")
    if path in ["/login", "/static/"]:
        return await call_next(request)

    auth = request.headers.get("Authorization")
    if auth:
        try:
            scheme, credentials = auth.split()
            if scheme.lower() == "basic":
                decoded = base64.b64decode(credentials).decode("ascii")
                username, password = decoded.split(":", 1)
                if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                    request.scope["user"] = SimpleUser(username)
                    return await call_next(request)
        except Exception as e:
            logger.error(f"Basic Auth processing error: {e}")

    # If no valid auth, return 401
    from starlette.responses import PlainTextResponse
    response = PlainTextResponse("Authentication required", status_code=401)
    response.headers["WWW-Authenticate"] = "Basic"
    return response

# Store historical system resource metrics
system_metrics_history = deque(maxlen=360)  # 60 minutes of data at 10s intervals

@app.on_event("startup")
async def start_background_tasks():
    async def collect_metrics():
        while True:
            resources = get_system_resources()
            
            cpu_val = 0
            if resources.get("cpu_load") and resources["cpu_load"] != "N/A":
                try:
                    cpu_val = float(resources["cpu_load"].split(',')[0].strip())
                except Exception:
                    pass
                
            disk_val = 0
            if resources.get("disk_usage") and resources["disk_usage"] != "N/A":
                try:
                    disk_val = float(resources["disk_usage"].split('(')[1].replace('%', '').replace(')', '').strip())
                except Exception:
                    pass

            system_metrics_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cpu": cpu_val,
                "disk": disk_val
            })
            await asyncio.sleep(10)
    asyncio.create_task(collect_metrics())

# Helper Functions
def get_all_container_names():
    if not docker_client:
        return []
    try:
        # Filter out the migration container as it exits after running
        return [c.name for c in docker_client.containers.list(all=True) if c.name != "emailagg_migration"]
    except Exception as e:
        logger.error(f"Error listing containers: {e}")
        return []


def get_service_status(container_name):
    if not docker_client:
        return {"status": "Docker not available", "details": ""}
    try:
        container = docker_client.containers.get(container_name)
        status = container.status
        health = "unknown"
        if hasattr(container, 'attrs') and 'State' in container.attrs and 'Health' in container.attrs['State']:
            health = container.attrs['State']['Health']['Status']
        return {"status": status, "health": health, "details": ""}
    except docker.errors.NotFound:
        return {"status": "Not running", "details": "Container not found."}
    except Exception as e:
        return {"status": "Error", "details": str(e)}


async def get_container_logs_async(container_name: str, tail: int = 100):
    if not docker_client:
        return "Docker client not initialized. Check /var/run/docker.sock mount."
    try:
        container = docker_client.containers.get(container_name)
        logs = container.logs(tail=tail, timestamps=True)
        return logs.decode('utf-8', errors='replace').strip()
    except docker.errors.NotFound:
        return f"Container '{container_name}' not found."
    except Exception as e:
        logger.error(f"Error fetching logs for {container_name}: {e}")
        return f"Error fetching logs: {e}"


async def get_error_logs_async(container_name: str, since_seconds: int = 3600):
    if not docker_client:
        return "Docker client not initialized."
    try:
        container = docker_client.containers.get(container_name)
        # We fetch last 500 lines to parse for errors
        logs = container.logs(tail=500, timestamps=True).decode('utf-8', errors='replace').split('\n')
        error_lines = []
        for line in logs:
            if "error" in line.lower() or "fail" in line.lower() or "exception" in line.lower():
                error_lines.append(line.strip())
        return "\n".join(error_lines)
    except docker.errors.NotFound:
        return f"Container '{container_name}' not found."
    except Exception as e:
        logger.error(f"Error fetching error logs for {container_name}: {e}")
        return f"Error fetching error logs: {e}"


def get_db_stats():
    conn = None
    try:
        conn = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "db"),
            database=os.environ.get("POSTGRES_DB", "emailagg"),
            user=os.environ.get("POSTGRES_USER", "emailagg"),
            password=os.environ.get("POSTGRES_PASSWORD"),
            connect_timeout=3
        )
        cur = conn.cursor()
        
        # Total users
        cur.execute("SELECT COUNT(*) FROM users;")
        total_users = cur.fetchone()[0]
        
        # Active mailboxes
        cur.execute("SELECT COUNT(*) FROM mail_accounts WHERE status != 'disconnected';")
        active_mailboxes = cur.fetchone()[0]
        
        # Sent notifications in last 24h
        cur.execute("SELECT COUNT(*) FROM notifications WHERE status = 'sent' AND sent_at >= NOW() - INTERVAL '24 hours';")
        active_24h = cur.fetchone()[0]
        
        cur.close()
        return {
            "total_users": total_users,
            "recently_active_users_count": active_24h,
            "active_mailboxes": active_mailboxes,
            "message": "Real-time VPS database analytics active."
        }
    except Exception as e:
        logger.error(f"Failed to fetch user stats from DB: {e}")
        return {
            "total_users": 0,
            "recently_active_users_count": 0,
            "active_mailboxes": 0,
            "message": f"DB connection offline: {e}"
        }
    finally:
        if conn:
            conn.close()


def get_system_resources():
    try:
        # CPU Load
        cpu_load = "N/A"
        if os.path.exists("/proc/loadavg"):
            with open("/proc/loadavg", "r") as f:
                load = f.read().split()
                cpu_load = f"{load[0]}, {load[1]}, {load[2]}"
            
        # RAM usage
        ram_usage = "N/A"
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
                mem_info = {}
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        mem_info[parts[0].replace(":", "")] = int(parts[1])
                
                total = mem_info.get("MemTotal", 0)
                free = mem_info.get("MemFree", 0)
                buffers = mem_info.get("Buffers", 0)
                cached = mem_info.get("Cached", 0)
                
                used = total - free - buffers - cached
                ram_pct = (used / total * 100) if total > 0 else 0
                ram_usage = f"{used / 1024 / 1024:.1f} GB / {total / 1024 / 1024:.1f} GB ({ram_pct:.0f}%)"
            
        # Disk usage
        stat = os.statvfs('/')
        total_disk = stat.f_blocks * stat.f_frsize
        free_disk = stat.f_bfree * stat.f_frsize
        used_disk = total_disk - free_disk
        disk_pct = (used_disk / total_disk * 100) if total_disk > 0 else 0
        disk_usage = f"{used_disk / 1024 / 1024 / 1024:.1f} GB / {total_disk / 1024 / 1024 / 1024:.1f} GB ({disk_pct:.0f}%)"
        
        return {
            "cpu_load": cpu_load,
            "ram_usage": ram_usage,
            "disk_usage": disk_usage
        }
    except Exception as e:
        logger.error(f"Error fetching system resources: {e}")
        return {"cpu_load": "N/A", "ram_usage": "N/A", "disk_usage": "N/A"}


# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    if not hasattr(request, "user") or not request.user or not request.user.is_authenticated:
        return RedirectResponse(url=request.url_for("login_get"))

    container_names = get_all_container_names()
    service_health_data = {}
    for name in container_names:
        service_health_data[name] = get_service_status(name)
    
    user_analytics_data = get_db_stats()
    system_resources = get_system_resources()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": request.user.identity,
        "services": service_health_data,
        "user_analytics": user_analytics_data,
        "system_resources": system_resources
    })


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_post(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url=request.url_for("read_root"), status_code=303)
        return response
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})


@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}


@app.get("/api/v1/health")
async def get_dashboard_health():
    container_names = get_all_container_names()
    service_health_data = {}
    for name in container_names:
        service_health_data[name] = get_service_status(name)
    return {"services": service_health_data, "status": "ok"}


@app.get("/api/v1/logs/{container_name}")
async def get_dashboard_logs(container_name: str, tail: int = 100):
    logs = await get_container_logs_async(container_name, tail)
    return {"logs": logs}


@app.get("/api/v1/errors/{container_name}")
async def get_dashboard_errors(container_name: str, since_seconds: int = 3600):
    error_logs = await get_error_logs_async(container_name, since_seconds)
    return {"error_logs": error_logs}


@app.get("/api/v1/users")
async def get_dashboard_users():
    return get_db_stats()


@app.get("/api/v1/system_resources")
async def get_dashboard_system_resources():
    return get_system_resources()


@app.get("/api/v1/system_resources/history")
async def get_dashboard_system_resources_history():
    return list(system_metrics_history)
