"""
监控服务器
接收并存储客户端上报的状态数据，提供RESTful API接口
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.responses import JSONResponse

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import Client, Server, Report, Command, CommandType
from common.system_info import SystemInfo
from common.database import get_db, init_db, ClientDAO, RecordDAO, AlertDAO

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 存储客户端状态和报告数据（临时缓存，用于实时通信）
registered_clients: Dict[str, Client] = {}
offline_clients: List[Client] = []

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务器生命周期管理"""
    # 启动时初始化数据库并向注册中心注册
    # 初始化数据库
    init_db()
    logger.info("Database initialized")
    
    # 向注册中心注册（在后台任务中）
    asyncio.create_task(register_to_register_center())
    
    yield
    
    # 关闭时的清理工作（如果需要）

# 创建FastAPI应用
app = FastAPI(title="Overwatch Server Service", version="1.0.0", lifespan=lifespan)


async def register_to_register_center():
    """向注册中心注册服务器"""
    import websockets
    
    register_url = "ws://127.0.0.1:10640/ws"
    
    try:
        async with websockets.connect(register_url) as websocket:
            # 创建服务器上线命令
            server = Server(ip=SystemInfo.get_local_ip())
            command = Command.create_server_online(server)
            
            # 发送注册命令
            await websocket.send(json.dumps(command.model_dump()))
            logger.info(f"Server registered to register center: {server.ip}")
            
            # 保持连接一段时间后退出，让服务器能够正常启动
            await asyncio.sleep(5)
                
    except Exception as e:
        logger.error(f"Failed to register to register center: {e}")
        # 不再重试，避免阻塞服务器启动


@app.get("/")
async def root():
    """根路径，返回服务状态"""
    return {"message": "Overwatch Server Service is running"}


@app.get("/clients")
async def get_clients():
    """获取当前所有在线的客户端"""
    # 从数据库获取所有客户端
    db = next(get_db())
    try:
        db_clients = ClientDAO.get_online(db)
        return [
            {
                "ip": client.ip,
                "name": client.name,
                "online": client.online
            }
            for client in db_clients
        ]
    finally:
        db.close()


@app.get("/client")
async def get_client_reports(
    name: str = Query(..., description="客户端名称"),
    starttime: int = Query(0, description="起始时间戳（毫秒）"),
    endtime: int = Query(int(time.time() * 1000), description="结束时间戳（毫秒）")
):
    """获取特定客户端的状态报告"""
    # 从数据库获取记录
    db = next(get_db())
    try:
        # 转换时间戳为datetime对象
        from datetime import datetime
        start_dt = datetime.fromtimestamp(starttime / 1000)
        end_dt = datetime.fromtimestamp(endtime / 1000)
        
        # 查询指定时间范围内的记录
        records = RecordDAO.get_by_timerange(db, name, start_dt, end_dt)
        
        return [
            {
                "avgload": record.load,
                "cpunum": record.cpus,
                "id": record.id,
                "name": record.name,
                "os": record.os,
                "timestamp": int(record.timestamp.timestamp() * 1000)  # 转换为毫秒时间戳
            }
            for record in records
        ]
    finally:
        db.close()


@app.get("/alert")
async def get_offline_clients():
    """获取掉线的客户端"""
    # 从数据库获取离线客户端
    db = next(get_db())
    try:
        # 获取所有客户端，筛选离线的
        all_clients = ClientDAO.get_all(db)
        offline_db_clients = [
            {
                "ip": client.ip,
                "name": client.name,
                "online": False
            }
            for client in all_clients
            if not client.online
        ]
        
        # 添加临时离线客户端（从内存中的列表）
        for client in offline_clients:
            # 检查是否已在数据库中
            if not any(c["name"] == client.name for c in offline_db_clients):
                offline_db_clients.append({
                    "ip": client.ip,
                    "name": client.name,
                    "online": False
                })
        
        return offline_db_clients
    finally:
        db.close()


@app.get("/delclient")
async def delete_client(name: str = Query(..., description="客户端名称")):
    """删除客户端"""
    # 从数据库中删除客户端
    db = next(get_db())
    try:
        success = ClientDAO.delete(db, name)
        if success:
            # 从内存缓存中删除
            if name in registered_clients:
                del registered_clients[name]
            
            # 从离线列表中删除
            offline_clients[:] = [
                c for c in offline_clients 
                if c.name != name
            ]
            
            logger.info(f"Client deleted: {name}")
            return {}
        else:
            return {"error": "Client not found"}
    finally:
        db.close()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，接收客户端上报的数据"""
    await manager.connect(websocket)
    client_name = None
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            logger.info(f"Received message: {data}")
            
            try:
                # 解析命令
                command_data = json.loads(data)
                command = Command(**command_data)
                
                # 处理不同类型的命令
                if command.type == CommandType.CLIENT_ONLINE:
                    # 客户端上线
                    client_data = command.contents.get("client")
                    client = Client(**client_data)
                    registered_clients[client.name] = client
                    client_name = client.name
                    
                    # 更新数据库中的客户端状态
                    db = next(get_db())
                    try:
                        ClientDAO.create_or_update(db, client.name, client.ip, True)
                        logger.info(f"Updated client {client.name} in database")
                    except Exception as e:
                        logger.error(f"Error updating client in database: {e}")
                    finally:
                        db.close()
                    
                    # 从离线列表中移除
                    offline_clients[:] = [
                        c for c in offline_clients 
                        if c.name != client.name
                    ]
                    
                    logger.info(f"Client online: {client.name}")
                
                elif command.type == CommandType.CLIENT_REPORT:
                    # 客户端报告
                    report_data = command.contents.get("report")
                    report = Report(**report_data)
                    
                    # 存储报告到数据库
                    db = next(get_db())
                    try:
                        RecordDAO.create(db, report.to_db_dict())
                        logger.info(f"Saved report from {report.name} to database")
                    except Exception as e:
                        logger.error(f"Error saving report to database: {e}")
                    finally:
                        db.close()
                    
                    logger.info(f"Received report from {report.name}")
                
                else:
                    logger.warning(f"Unknown command type: {command.type}")
                    
            except Exception as e:
                logger.error(f"Error processing command: {e}")
                await manager.send_personal_message(
                    json.dumps({"error": str(e)}), websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
        # 客户端断开连接，标记为离线
        if client_name and client_name in registered_clients:
            client = registered_clients[client_name]
            client.online = False
            offline_clients.append(client)
            
            # 更新数据库中的客户端状态
            db = next(get_db())
            try:
                ClientDAO.set_offline(db, client_name)
                logger.info(f"Updated client {client_name} status to offline in database")
            except Exception as e:
                logger.error(f"Error updating client status in database: {e}")
            finally:
                db.close()
            
            logger.info(f"Client offline: {client_name}")


if __name__ == "__main__":
    import uvicorn
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=10641,
        reload=True,
        log_level="info"
    )