from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request

import ipaddress
from fastapi.security import APIKeyHeader
import secrets
import sqlite3

from app.api import dependencies, schemas
from app.local.daemon import Daemon, DaemonStatus
from app.local.hell import Hell


router = APIRouter()


def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invitations (
            id INTEGER PRIMARY KEY,
            invitation_code TEXT UNIQUE,
            used BOOLEAN DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY,
            api_key TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()


init_db()

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


# Функция для генерации уникальных токенов
def generate_token():
    return secrets.token_urlsafe(32)


# Функция для проверки API ключа
def verify_api_key(api_key: str = Depends(api_key_header)):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM api_keys WHERE api_key = ?", (api_key,))
    result = cursor.fetchone()
    conn.close()
    if not result:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


# Функция для проверки, что запрос сделан с локальной сети
def is_local_network(request: Request):
    if request.client is None:
        return False

    client_ip = request.client.host
    try:
        ip = ipaddress.ip_address(client_ip)
        # Проверяем, что IP-адрес принадлежит локальной сети или является localhost
        if ip.is_loopback or ip.is_private:
            return True
    except ValueError:
        pass
    return False


# Эндпоинт для создания приглашения (например, администратором)
@router.post("/create-invitation/")
def create_invitation(request: Request):
    if not is_local_network(request):
        raise HTTPException(
            status_code=403,
            detail="Access denied: This endpoint is accessible only from the local network.",
        )

    invitation_code = generate_token()
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO invitations (invitation_code) VALUES (?)", (invitation_code,)
    )
    conn.commit()
    conn.close()
    return {"invitation_code": invitation_code}


# Эндпоинт для генерации API ключа по приглашению
@router.post("/generate-api-key/")
def generate_api_key(invitation_code: str):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Проверяем наличие и статус приглашения
    cursor.execute(
        "SELECT * FROM invitations WHERE invitation_code = ? AND used = 0",
        (invitation_code,),
    )
    invitation = cursor.fetchone()
    if not invitation:
        raise HTTPException(
            status_code=400, detail="Invalid or already used invitation code"
        )

    # Генерируем и сохраняем API ключ
    new_api_key = generate_token()
    cursor.execute("INSERT INTO api_keys (api_key) VALUES (?)", (new_api_key,))

    # Отмечаем приглашение как использованное
    cursor.execute(
        "UPDATE invitations SET used = 1 WHERE invitation_code = ?", (invitation_code,)
    )
    conn.commit()
    conn.close()
    return {"api_key": new_api_key}


# Пример защищенного эндпоинта, доступного только с API ключом
# @app.get("/secure-endpoint/")
# def secure_endpoint(api_key: str = Depends(verify_api_key)):
#     return {"message": "Access granted with a valid API key!"}
@router.get("/daemons/", response_model=schemas.DaemonList)
async def list_daemons(
    hell: Hell = Depends(dependencies.get_hell_instance),
    api_key: str = Depends(verify_api_key),
):
    """List all daemons and their statuses"""
    return schemas.DaemonList(
        daemons=[
            schemas.Daemon(
                name=daemon.name,
                directory=str(daemon.project_folder),
                main_file=str(daemon.main_file),
                requirements_path=str(daemon.requirements_path)
                if daemon.requirements_path
                else "None",
                auto_restart=daemon.restart_if_stopped,
                arguments=daemon.main_file_arguments,
                use_virtualenv=daemon.use_virtualenv,
                dependancies_installed=daemon.dependencies_installed,
                deployed_once=daemon.deployed_once,
                deployed_at=daemon.deployed_at,
                virtualenv_path=str(daemon.virtualenv_path)
                if daemon.virtualenv_path
                else "None",
                pid=daemon.PID,
            )
            for daemon in hell.daemons
        ],
        count=len(hell.daemons),
        timestamp=datetime.now().timestamp(),
    )


@router.post("/daemons/{daemon_name}/start", response_model=schemas.DaemonResponse)
async def start_daemon(
    daemon: Daemon = Depends(dependencies.get_daemon),
    api_key: str = Depends(verify_api_key),
):
    """Start a specific daemon"""
    if daemon.deploy():
        return schemas.DaemonResponse(status=DaemonStatus.RUNNING, name=daemon.name)
    else:
        raise HTTPException(status_code=500, detail="Failed to start daemon")


@router.post("/daemons/{daemon_name}/stop", response_model=schemas.DaemonResponse)
async def stop_daemon(
    daemon: Daemon = Depends(dependencies.get_daemon),
    api_key: str = Depends(verify_api_key),
):
    """Stop a specific daemon"""
    if daemon.kill():
        return schemas.DaemonResponse(status=DaemonStatus.STOPPED, name=daemon.name)
    else:
        raise HTTPException(status_code=500, detail="Failed to stop daemon")
