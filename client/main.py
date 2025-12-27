"""
监控客户端
收集系统状态并定期上报给监控服务器
"""

import asyncio
import json
import logging
import time
import websockets
from typing import Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import Client, Server, Report, Command, CommandType
from common.system_info import SystemInfo

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OverwatchClient:
    """监控客户端类"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.server: Optional[Server] = None
        self.register_url = "ws://127.0.0.1:10640/ws"
        self.server_url = None
        self.running = False
        self.report_interval = 1  # 报告间隔（秒）
        
    async def start(self):
        """启动客户端"""
        logger.info("Starting Overwatch Client...")
        self.running = True
        
        # 初始化客户端信息
        self.client = Client(
            name=Client.create_random_name(),
            ip=SystemInfo.get_local_ip(),
            online=True
        )
        
        logger.info(f"Client initialized: {self.client.name} ({self.client.ip})")
        
        # 主循环
        while self.running:
            try:
                # 连接到注册中心
                await self.register_to_center()
                
                # 连接到监控服务器
                if self.server:
                    await self.connect_to_server()
                    
            except Exception as e:
                logger.error(f"Error in client loop: {e}")
                await asyncio.sleep(5)  # 出错后等待5秒重试
    
    async def register_to_center(self):
        """向注册中心注册"""
        try:
            async with websockets.connect(self.register_url) as websocket:
                logger.info(f"Connected to register center: {self.register_url}")
                
                # 发送注册命令
                register_cmd = Command.create_client_register(self.client)
                await websocket.send(json.dumps(register_cmd.model_dump()))
                logger.info("Sent registration command")
                
                # 接收服务器信息
                response = await websocket.recv()
                server_data = json.loads(response)
                self.server = Server(**server_data)
                self.server_url = f"ws://{self.server.ip}:10641/ws"
                
                logger.info(f"Received server info: {self.server_url}")
                
        except Exception as e:
            logger.error(f"Failed to register to center: {e}")
            raise
    
    async def connect_to_server(self):
        """连接到监控服务器并上报数据"""
        if not self.server_url:
            logger.error("No server URL available")
            return
            
        try:
            async with websockets.connect(self.server_url) as websocket:
                logger.info(f"Connected to server: {self.server_url}")
                
                # 发送上线命令
                online_cmd = Command.create_client_online(self.client)
                await websocket.send(json.dumps(online_cmd.model_dump()))
                logger.info("Sent online command")
                
                # 启动定期报告任务
                report_task = asyncio.create_task(
                    self.periodic_report(websocket)
                )
                
                # 保持连接并处理响应
                try:
                    while self.running:
                        response = await websocket.recv()
                        logger.info(f"Received from server: {response}")
                        
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("Server connection closed")
                finally:
                    report_task.cancel()
                    try:
                        await report_task
                    except asyncio.CancelledError:
                        pass
                        
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            raise
    
    async def periodic_report(self, websocket):
        """定期上报系统状态"""
        while self.running:
            try:
                # 获取系统报告
                report_data = SystemInfo.get_system_report(self.client.name)
                report = Report(**report_data)
                
                # 创建报告命令
                report_cmd = Command.create_client_report(report)
                
                # 发送报告
                await websocket.send(json.dumps(report_cmd.model_dump(), default=str))
                logger.debug(f"Sent report: load={report.load:.2f}, cpus={report.cpus}")
                
                # 等待下一次报告
                await asyncio.sleep(self.report_interval)
                
            except asyncio.CancelledError:
                logger.info("Report task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic report: {e}")
                await asyncio.sleep(1)  # 出错后等待1秒再试
    
    def stop(self):
        """停止客户端"""
        logger.info("Stopping Overwatch Client...")
        self.running = False


async def main():
    """主函数"""
    client = OverwatchClient()
    
    try:
        await client.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        client.stop()


if __name__ == "__main__":
    asyncio.run(main())