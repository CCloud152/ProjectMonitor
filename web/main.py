"""
Web界面应用
提供监控系统的Web界面
"""

import json
import logging
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.database import get_db, init_db, ClientDAO, RecordDAO, AlertDAO, ConfigDAO, UserDAO
from common.models import Client, Report, Alert, Config, User

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置模板
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Web应用生命周期管理"""
    # 启动时初始化数据库
    # 初始化数据库
    init_db()
    logger.info("Database initialized for web application")
    
    # 创建默认管理员用户
    db = next(get_db())
    try:
        # 检查是否已存在admin用户
        admin_user = UserDAO.get_by_username(db, "admin")
        if not admin_user:
            # 创建默认管理员用户
            # 注意：实际应用中应该使用密码哈希
            admin_data = {
                "username": "admin",
                "password": "123456",  # 实际应用中应该存储哈希值
                "email": "admin@example.com",
                "is_active": True
            }
            UserDAO.create(db, User(**admin_data))
            logger.info("Created default admin user")
        
        # 初始化默认配置
        default_configs = [
            {
                "key": "system.name",
                "value": "集群监控系统",
                "description": "系统名称"
            },
            {
                "key": "system.data_retention",
                "value": "30",
                "description": "数据保留天数"
            },
            {
                "key": "system.collection_interval",
                "value": "60",
                "description": "数据收集间隔（秒）"
            },
            {
                "key": "monitor.cpu_warning",
                "value": "70",
                "description": "CPU使用率告警阈值（%）"
            },
            {
                "key": "monitor.cpu_critical",
                "value": "90",
                "description": "CPU使用率严重告警阈值（%）"
            },
            {
                "key": "monitor.memory_warning",
                "value": "80",
                "description": "内存使用率告警阈值（%）"
            },
            {
                "key": "monitor.memory_critical",
                "value": "95",
                "description": "内存使用率严重告警阈值（%）"
            },
            {
                "key": "monitor.disk_warning",
                "value": "80",
                "description": "磁盘使用率告警阈值（%）"
            },
            {
                "key": "monitor.disk_critical",
                "value": "95",
                "description": "磁盘使用率严重告警阈值（%）"
            }
        ]
        
        for config_data in default_configs:
            existing_config = ConfigDAO.get_by_key(db, config_data["key"])
            if not existing_config:
                ConfigDAO.set(db, config_data["key"], config_data["value"], config_data["description"])
        
        logger.info("Database initialization completed")
    finally:
        db.close()
    
    yield
    
    # 关闭时的清理工作（如果需要）

# 创建FastAPI应用
app = FastAPI(title="Overwatch Web Interface", version="1.0.0", lifespan=lifespan)

# 静态文件
import os
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 服务器API地址
SERVER_API_BASE = "http://127.0.0.1:10641"




@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """处理登录"""
    # 从数据库验证用户
    db = next(get_db())
    try:
        user = UserDAO.get_by_username(db, username)
        if user and user.password == password:  # 实际应用中应该验证密码哈希
            # 更新最后登录时间
            UserDAO.update_login_time(db, username)
            # 登录成功，重定向到主页
            return RedirectResponse(url="/index", status_code=303)
        else:
            # 登录失败，返回登录页面
            return templates.TemplateResponse(
                "login.html", 
                {"request": request, "error": "用户名或密码错误"}
            )
    finally:
        db.close()


@app.get("/index", response_class=HTMLResponse)
async def index_page(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/tables", response_class=HTMLResponse)
async def tables_page(request: Request):
    """客户端列表页面"""
    return templates.TemplateResponse("tables.html", {"request": request})


@app.get("/data_dynamic", response_class=HTMLResponse)
async def dynamic_page(request: Request):
    """动态数据页面"""
    return templates.TemplateResponse("data_dynamic.html", {"request": request})


@app.get("/data_history", response_class=HTMLResponse)
async def history_page(request: Request):
    """历史数据页面"""
    return templates.TemplateResponse("data_history.html", {"request": request})


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """配置页面"""
    return templates.TemplateResponse("config.html", {"request": request})


# API端点，用于获取服务器数据
@app.get("/api/clients")
async def get_clients():
    """获取所有在线客户端"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SERVER_API_BASE}/clients")
        return response.json()


@app.get("/api/alert")
async def get_alerts():
    """获取所有离线客户端"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SERVER_API_BASE}/alert")
        return response.json()


@app.get("/api/client/{client_name}")
async def get_client_reports(
    client_name: str,
    starttime: int = Query(0),
    endtime: int = Query(int(9999999999999))
):
    """获取客户端报告"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SERVER_API_BASE}/client",
            params={
                "name": client_name,
                "starttime": starttime,
                "endtime": endtime
            }
        )
        return response.json()


@app.get("/api/delete_client")
async def delete_client(name: str = Query(...)):
    """删除客户端"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SERVER_API_BASE}/delclient",
            params={"name": name}
        )
        return response.json()


@app.get("/api/realtime")
async def get_realtime_data():
    """获取实时数据"""
    # 模拟实时数据
    import random
    import time
    
    return {
        "cluster": {
            "cpu": random.uniform(20, 80),
            "memory": random.uniform(30, 90),
            "disk": random.uniform(40, 70),
            "network": random.uniform(5, 50),
            "network_in": random.uniform(5, 30),
            "network_out": random.uniform(2, 20)
        },
        "time_series": {
            "cpu": [{"timestamp": time.time() - i * 60, "value": random.uniform(20, 80)} for i in range(60, 0, -1)],
            "memory": [{"timestamp": time.time() - i * 60, "value": random.uniform(30, 90)} for i in range(60, 0, -1)],
            "disk": [{"timestamp": time.time() - i * 60, "value": random.uniform(40, 70)} for i in range(60, 0, -1)],
            "network": [{"timestamp": time.time() - i * 60, "in": random.uniform(5, 30), "out": random.uniform(2, 20)} for i in range(60, 0, -1)]
        }
    }


@app.get("/api/history")
async def get_history_data(
    client_id: str = Query(""),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    metric: str = Query("all"),
    page: int = Query(1),
    page_size: int = Query(20)
):
    """获取历史数据"""
    # 模拟历史数据
    import random
    import time
    from datetime import datetime, timedelta
    
    # 生成时间标签
    labels = []
    now = datetime.now()
    for i in range(24):
        labels.append((now - timedelta(hours=i)).strftime("%H:%M"))
    labels.reverse()
    
    # 生成数据
    return {
        "statistics": {
            "avg_cpu": random.uniform(20, 80),
            "avg_memory": random.uniform(30, 90),
            "avg_disk": random.uniform(40, 70),
            "total_network": random.uniform(100, 1000)
        },
        "chart_data": {
            "labels": labels,
            "cpu": [random.uniform(20, 80) for _ in range(24)],
            "memory": [random.uniform(30, 90) for _ in range(24)],
            "disk": [random.uniform(40, 70) for _ in range(24)],
            "network_in": [random.uniform(5, 30) for _ in range(24)],
            "network_out": [random.uniform(2, 20) for _ in range(24)]
        },
        "records": [
            {
                "timestamp": (now - timedelta(hours=i)).isoformat(),
                "client_id": f"client_{random.randint(1, 10)}",
                "client_name": f"服务器{i}",
                "cpu_usage": random.uniform(20, 80),
                "memory_usage": random.uniform(30, 90),
                "disk_usage": random.uniform(40, 70),
                "network_in": random.uniform(5, 30),
                "network_out": random.uniform(2, 20)
            } for i in range(page_size)
        ],
        "pagination": {
            "current_page": page,
            "total_pages": 5,
            "total_records": 100
        }
    }


@app.get("/api/config")
async def get_config():
    """获取系统配置"""
    # 从数据库获取配置
    db = next(get_db())
    try:
        configs = ConfigDAO.get_all(db)
        config_dict = {}
        
        # 将配置转换为字典格式
        for config in configs:
            parts = config.key.split(".", 1)
            if len(parts) == 2:
                category, key = parts
                if category not in config_dict:
                    config_dict[category] = {}
                config_dict[category][key] = config.value
        
        # 确保所有必要的配置都存在
        defaults = {
            "system": {
                "name": "集群监控系统",
                "data_retention": "30",
                "collection_interval": "60",
                "max_clients": "100",
                "log_level": "info",
                "enable_auto_cleanup": "True",
                "enable_debug_mode": "False"
            },
            "monitor": {
                "cpu_warning": "70",
                "cpu_critical": "90",
                "cpu_enable": "True",
                "memory_warning": "80",
                "memory_critical": "95",
                "memory_enable": "True",
                "disk_warning": "80",
                "disk_critical": "95",
                "disk_enable": "True"
            },
            "alert": {
                "enable": "True",
                "cooldown": "15",
                "consecutive": "3",
                "recovery": "True"
            },
            "notification": {
                "email_enable": "False",
                "smtp_server": "",
                "smtp_port": "587",
                "email_username": "",
                "email_password": "",
                "email_recipients": "",
                "webhook_enable": "False",
                "webhook_url": ""
            }
        }
        
        # 合并默认值和数据库中的值
        for category, keys in defaults.items():
            if category not in config_dict:
                config_dict[category] = {}
            for key, value in keys.items():
                if key not in config_dict[category]:
                    config_dict[category][key] = value
        
        # 转换字符串值为适当的类型
        for category, keys in config_dict.items():
            for key, value in keys.items():
                if value.lower() == "true":
                    config_dict[category][key] = True
                elif value.lower() == "false":
                    config_dict[category][key] = False
                elif value.isdigit():
                    config_dict[category][key] = int(value)
        
        return config_dict
    finally:
        db.close()


@app.post("/api/config/system")
async def save_system_config(config: dict):
    """保存系统配置"""
    # 保存配置到数据库
    db = next(get_db())
    try:
        for key, value in config.items():
            config_key = f"system.{key}"
            ConfigDAO.set(db, config_key, str(value))
        
        return {"success": True, "message": "系统配置保存成功"}
    except Exception as e:
        logger.error(f"Error saving system config: {e}")
        return {"success": False, "message": f"保存系统配置失败: {str(e)}"}
    finally:
        db.close()


@app.post("/api/config/monitor")
async def save_monitor_config(config: dict):
    """保存监控配置"""
    # 保存配置到数据库
    db = next(get_db())
    try:
        for key, value in config.items():
            config_key = f"monitor.{key}"
            ConfigDAO.set(db, config_key, str(value))
        
        return {"success": True, "message": "监控配置保存成功"}
    except Exception as e:
        logger.error(f"Error saving monitor config: {e}")
        return {"success": False, "message": f"保存监控配置失败: {str(e)}"}
    finally:
        db.close()


@app.post("/api/config/alert")
async def save_alert_config(config: dict):
    """保存告警配置"""
    # 保存配置到数据库
    db = next(get_db())
    try:
        for key, value in config.items():
            config_key = f"alert.{key}"
            ConfigDAO.set(db, config_key, str(value))
        
        return {"success": True, "message": "告警配置保存成功"}
    except Exception as e:
        logger.error(f"Error saving alert config: {e}")
        return {"success": False, "message": f"保存告警配置失败: {str(e)}"}
    finally:
        db.close()


@app.post("/api/config/notification")
async def save_notification_config(config: dict):
    """保存通知配置"""
    # 保存配置到数据库
    db = next(get_db())
    try:
        # 处理嵌套的通知配置
        if "email" in config:
            for key, value in config["email"].items():
                config_key = f"notification.email_{key}"
                ConfigDAO.set(db, config_key, str(value))
        
        if "webhook" in config:
            for key, value in config["webhook"].items():
                config_key = f"notification.webhook_{key}"
                ConfigDAO.set(db, config_key, str(value))
        
        # 处理扁平化的通知配置
        for key, value in config.items():
            if key not in ["email", "webhook"]:
                config_key = f"notification.{key}"
                ConfigDAO.set(db, config_key, str(value))
        
        return {"success": True, "message": "通知配置保存成功"}
    except Exception as e:
        logger.error(f"Error saving notification config: {e}")
        return {"success": False, "message": f"保存通知配置失败: {str(e)}"}
    finally:
        db.close()


@app.get("/api/config/backup")
async def backup_config():
    """备份配置"""
    # 这里应该生成配置文件并返回
    import json
    from fastapi.responses import Response
    
    config = {
        "system": {
            "name": "集群监控系统",
            "data_retention": 30,
            "collection_interval": 60,
            "max_clients": 100,
            "log_level": "info",
            "enable_auto_cleanup": True,
            "enable_debug_mode": False
        }
    }
    
    return Response(
        content=json.dumps(config, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=config.json"}
    )


@app.post("/api/config/restore")
async def restore_config(request: Request):
    """恢复配置"""
    # 这里应该处理上传的配置文件
    return {"success": True, "message": "配置恢复成功"}


@app.get("/api/users")
async def get_users():
    """获取用户列表"""
    return {
        "users": [
            {
                "id": "1",
                "username": "admin",
                "role": "admin",
                "email": "admin@example.com",
                "created_at": "2023-01-01T00:00:00Z",
                "last_login": "2023-12-20T10:30:00Z",
                "status": "active"
            }
        ]
    }


@app.post("/api/users")
async def create_user(user: dict):
    """创建用户"""
    # 这里应该创建用户
    return {"success": True, "message": "用户创建成功"}


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str):
    """删除用户"""
    # 这里应该删除用户
    return {"success": True, "message": "用户删除成功"}


@app.post("/api/clients/{client_id}/command")
async def send_command_to_client(client_id: str, command: dict):
    """向客户端发送命令"""
    # 这里应该向客户端发送命令
    return {"success": True, "message": "命令发送成功"}


@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    """退出登录"""
    return RedirectResponse(url="/", status_code=303)


if __name__ == "__main__":
    import uvicorn
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8089,
        reload=True,
        log_level="info"
    )