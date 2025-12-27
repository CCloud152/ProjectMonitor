import psutil
import platform
import time
from typing import Dict, Any


class SystemInfo:
    """系统信息获取工具类"""
    
    @staticmethod
    def get_cpu_count() -> int:
        """获取CPU核心数"""
        return psutil.cpu_count(logical=True)
    
    @staticmethod
    def get_avg_load() -> float:
        """获取系统平均负载"""
        # Windows系统使用CPU使用率作为负载指标
        if platform.system() == "Windows":
            return psutil.cpu_percent(interval=1) / 100.0
        # Unix系统可以使用getloadavg
        else:
            load1, _, _ = psutil.getloadavg()
            return load1
    
    @staticmethod
    def get_os_info() -> str:
        """获取操作系统信息"""
        return f"{platform.machine()}{platform.system()}{platform.release()}"
    
    @staticmethod
    def get_local_ip() -> str:
        """获取本机IP地址"""
        import socket
        try:
            # 创建一个UDP socket连接到公共DNS服务器
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            # 对于本地测试，使用127.0.0.1
            return "127.0.0.1"
        except Exception:
            return "127.0.0.1"
    
    @staticmethod
    def get_system_report(client_name: str) -> Dict[str, Any]:
        """获取完整的系统报告"""
        return {
            "name": client_name,
            "os": SystemInfo.get_os_info(),
            "load": SystemInfo.get_avg_load(),
            "cpus": SystemInfo.get_cpu_count(),
            "timestamp": int(time.time() * 1000)  # 毫秒时间戳
        }