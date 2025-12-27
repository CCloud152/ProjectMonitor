from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
from datetime import datetime
from .database import Client as DBClient, Record as DBRecord, Server as DBServer, Alert as DBAlert, Config as DBConfig, User as DBUser


class Client(BaseModel):
    """客户端数据模型"""
    name: str
    ip: str
    online: bool = True
    
    class Config:
        json_encoders = {
            # 自定义JSON编码器
        }
        
    @classmethod
    def create_random_name(cls):
        """生成随机客户端名称"""
        return str(uuid.uuid4())[:8].upper()
    
    @classmethod
    def from_db(cls, db_client: DBClient):
        """从数据库模型创建"""
        return cls(
            name=db_client.name,
            ip=db_client.ip,
            online=db_client.online
        )


class Server(BaseModel):
    """服务器数据模型"""
    id: Optional[int] = None
    ip: str
    
    @classmethod
    def from_db(cls, db_server: DBServer):
        """从数据库模型创建"""
        return cls(
            id=db_server.id,
            ip=db_server.ip
        )


class Report(BaseModel):
    """系统状态报告"""
    name: str
    os: str
    load: float
    cpus: int
    memory_total: Optional[float] = None
    memory_used: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_total: Optional[float] = None
    disk_used: Optional[float] = None
    disk_percent: Optional[float] = None
    timestamp: Optional[datetime] = None
    
    @classmethod
    def from_db(cls, db_record: DBRecord):
        """从数据库模型创建"""
        return cls(
            name=db_record.name,
            os=db_record.os,
            load=db_record.load,
            cpus=db_record.cpus,
            memory_total=db_record.memory_total,
            memory_used=db_record.memory_used,
            memory_percent=db_record.memory_percent,
            disk_total=db_record.disk_total,
            disk_used=db_record.disk_used,
            disk_percent=db_record.disk_percent,
            timestamp=db_record.timestamp
        )
    
    def to_db_dict(self):
        """转换为数据库字典格式"""
        return {
            "name": self.name,
            "os": self.os,
            "load": self.load,
            "cpus": self.cpus,
            "memory_total": self.memory_total,
            "memory_used": self.memory_used,
            "memory_percent": self.memory_percent,
            "disk_total": self.disk_total,
            "disk_used": self.disk_used,
            "disk_percent": self.disk_percent,
            "timestamp": self.timestamp or datetime.utcnow()
        }


class Alert(BaseModel):
    """告警数据模型"""
    id: Optional[int] = None
    client_name: str
    alert_type: str
    message: str
    severity: str = "warning"
    resolved: bool = False
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    @classmethod
    def from_db(cls, db_alert: DBAlert):
        """从数据库模型创建"""
        return cls(
            id=db_alert.id,
            client_name=db_alert.client_name,
            alert_type=db_alert.alert_type,
            message=db_alert.message,
            severity=db_alert.severity,
            resolved=db_alert.resolved,
            created_at=db_alert.created_at,
            resolved_at=db_alert.resolved_at
        )
    
    def to_db_dict(self):
        """转换为数据库字典格式"""
        return {
            "client_name": self.client_name,
            "alert_type": self.alert_type,
            "message": self.message,
            "severity": self.severity,
            "resolved": self.resolved,
            "created_at": self.created_at or datetime.utcnow(),
            "resolved_at": self.resolved_at
        }


class Config(BaseModel):
    """配置数据模型"""
    id: Optional[int] = None
    key: str
    value: str
    description: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_db(cls, db_config: DBConfig):
        """从数据库模型创建"""
        return cls(
            id=db_config.id,
            key=db_config.key,
            value=db_config.value,
            description=db_config.description,
            updated_at=db_config.updated_at
        )
    
    def to_db_dict(self):
        """转换为数据库字典格式"""
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": datetime.utcnow()
        }


class User(BaseModel):
    """用户数据模型"""
    id: Optional[int] = None
    username: str
    password: str
    email: Optional[str] = None
    role: str = "user"
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    @classmethod
    def from_db(cls, db_user: DBUser):
        """从数据库模型创建"""
        return cls(
            id=db_user.id,
            username=db_user.username,
            password=db_user.password,
            email=db_user.email,
            role=db_user.role,
            created_at=db_user.created_at,
            last_login=db_user.last_login
        )
    
    def to_db_dict(self):
        """转换为数据库字典格式"""
        return {
            "username": self.username,
            "password": self.password,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at or datetime.utcnow(),
            "last_login": self.last_login
        }


class Command(BaseModel):
    """通信命令"""
    type: str
    contents: dict
    
    @classmethod
    def create_client_register(cls, client: Client):
        """创建客户端注册命令"""
        return cls(
            type="CLIENT_REGIST",
            contents={"client": client.model_dump()}
        )
    
    @classmethod
    def create_client_online(cls, client: Client):
        """创建客户端上线命令"""
        return cls(
            type="CLIENT_ONLINE",
            contents={"client": client.model_dump()}
        )
    
    @classmethod
    def create_client_report(cls, report: Report):
        """创建客户端报告命令"""
        # 使用自定义序列化方法处理datetime对象
        report_dict = report.model_dump()
        if report_dict.get("timestamp") and isinstance(report_dict["timestamp"], datetime):
            report_dict["timestamp"] = report_dict["timestamp"].isoformat()
            
        return cls(
            type="CLIENT_REPORT",
            contents={"report": report_dict}
        )
    
    @classmethod
    def create_server_online(cls, server: Server):
        """创建服务器上线命令"""
        return cls(
            type="SERVER_ONLINE",
            contents={"ip": server.ip}
        )


class CommandType:
    """命令类型常量"""
    CLIENT_REGIST = "CLIENT_REGIST"
    CLIENT_ONLINE = "CLIENT_ONLINE"
    CLIENT_REPORT = "CLIENT_REPORT"
    SERVER_ONLINE = "SERVER_ONLINE"