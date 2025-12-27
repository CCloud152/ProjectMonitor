"""
注册中心服务
负责管理客户端和服务器的注册信息
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import Client, Server, Command, CommandType

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="Overwatch Register Service", version="1.0.0")

# 存储注册信息
registered_clients: Dict[str, Client] = {}
registered_servers: Dict[str, Server] = {}

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
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # 连接已断开，移除
                self.active_connections.remove(connection)

manager = ConnectionManager()


@app.get("/")
async def root():
    """根路径，返回服务状态"""
    return {"message": "Overwatch Register Service is running"}


@app.get("/clients")
async def get_clients():
    """获取所有注册的客户端"""
    return {"clients": [client.model_dump() for client in registered_clients.values()]}


@app.get("/servers")
async def get_servers():
    """获取所有注册的服务器"""
    return {"servers": [server.model_dump() for server in registered_servers.values()]}


@app.get("/client/{client_name}")
async def get_client(client_name: str):
    """获取特定客户端信息"""
    client = registered_clients.get(client_name)
    if client:
        return client.model_dump()
    return {"error": "Client not found"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，处理客户端和服务器的连接"""
    await manager.connect(websocket)
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
                if command.type == CommandType.CLIENT_REGIST:
                    # 客户端注册
                    client_data = command.contents.get("client")
                    client = Client(**client_data)
                    registered_clients[client.name] = client
                    logger.info(f"Client registered: {client.name}")
                    
                    # 返回服务器信息给客户端
                    if registered_servers:
                        # 返回第一个可用的服务器
                        server = list(registered_servers.values())[0]
                        await manager.send_personal_message(
                            json.dumps(server.model_dump()), websocket
                        )
                
                elif command.type == CommandType.CLIENT_ONLINE:
                    # 客户端上线
                    client_data = command.contents.get("client")
                    client = Client(**client_data)
                    registered_clients[client.name] = client
                    logger.info(f"Client online: {client.name}")
                
                elif command.type == CommandType.SERVER_ONLINE:
                    # 服务器上线
                    ip = command.contents.get("ip")
                    server = Server(ip=ip)
                    registered_servers[ip] = server
                    logger.info(f"Server online: {ip}")
                
                else:
                    logger.warning(f"Unknown command type: {command.type}")
                    
            except Exception as e:
                logger.error(f"Error processing command: {e}")
                await manager.send_personal_message(
                    json.dumps({"error": str(e)}), websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected")


if __name__ == "__main__":
    import uvicorn
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=10640,
        reload=True,
        log_level="info"
    )