"""
数据库模型和操作模块
使用SQLite作为数据库，SQLAlchemy作为ORM框架
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "overwatch.db")

# 确保数据目录存在
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# 创建数据库引擎
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)


class Client(Base):
    """客户端模型"""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    ip = Column(String(50), nullable=False)
    online = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Client(name='{self.name}', ip='{self.ip}', online={self.online})>"


class Record(Base):
    """系统状态记录模型"""
    __tablename__ = "records"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, index=True)
    os = Column(String(255), nullable=False)
    load = Column(Float, nullable=False)
    cpus = Column(Integer, nullable=False)
    memory_total = Column(Float, nullable=False)  # GB
    memory_used = Column(Float, nullable=False)    # GB
    memory_percent = Column(Float, nullable=False)  # 百分比
    disk_total = Column(Float, nullable=False)    # GB
    disk_used = Column(Float, nullable=False)     # GB
    disk_percent = Column(Float, nullable=False)   # 百分比
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<Record(name='{self.name}', load={self.load}, timestamp={self.timestamp})>"


class Server(Base):
    """服务器模型"""
    __tablename__ = "servers"
    
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Server(ip='{self.ip}')>"


class Alert(Base):
    """告警模型"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(50), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # cpu, memory, disk, offline
    message = Column(Text, nullable=False)
    severity = Column(String(20), default="warning")  # info, warning, critical
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Alert(client='{self.client_name}', type='{self.alert_type}', resolved={self.resolved})>"


class Config(Base):
    """配置模型"""
    __tablename__ = "configs"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Config(key='{self.key}', value='{self.value}')>"


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # 存储哈希值
    email = Column(String(100), nullable=True)
    role = Column(String(20), default="user")  # admin, user
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"


# 数据库操作类
class ClientDAO:
    """客户端数据访问对象"""
    
    @staticmethod
    def get_all(db):
        """获取所有客户端"""
        return db.query(Client).all()
    
    @staticmethod
    def get_online(db):
        """获取在线客户端"""
        return db.query(Client).filter(Client.online == True).all()
    
    @staticmethod
    def get_by_name(db, name):
        """根据名称获取客户端"""
        return db.query(Client).filter(Client.name == name).first()
    
    @staticmethod
    def create_or_update(db, name, ip, online=True):
        """创建或更新客户端"""
        client = db.query(Client).filter(Client.name == name).first()
        if client:
            client.ip = ip
            client.online = online
            client.last_seen = datetime.utcnow()
        else:
            client = Client(name=name, ip=ip, online=online)
            db.add(client)
        db.commit()
        db.refresh(client)
        return client
    
    @staticmethod
    def set_offline(db, name):
        """设置客户端为离线状态"""
        client = db.query(Client).filter(Client.name == name).first()
        if client:
            client.online = False
            db.commit()
            return True
        return False
    
    @staticmethod
    def delete(db, name):
        """删除客户端"""
        client = db.query(Client).filter(Client.name == name).first()
        if client:
            db.delete(client)
            db.commit()
            return True
        return False


class RecordDAO:
    """记录数据访问对象"""
    
    @staticmethod
    def create(db, record_data):
        """创建新记录"""
        record = Record(**record_data)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    
    @staticmethod
    def get_by_client(db, name, limit=100):
        """获取客户端的最新记录"""
        return db.query(Record).filter(
            Record.name == name
        ).order_by(Record.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_by_timerange(db, name, start_time, end_time):
        """获取指定时间范围内的记录"""
        return db.query(Record).filter(
            Record.name == name,
            Record.timestamp >= start_time,
            Record.timestamp <= end_time
        ).order_by(Record.timestamp.desc()).all()
    
    @staticmethod
    def get_latest_by_client(db, name):
        """获取客户端的最新记录"""
        return db.query(Record).filter(
            Record.name == name
        ).order_by(Record.timestamp.desc()).first()
    
    @staticmethod
    def get_all_latest(db):
        """获取所有客户端的最新记录"""
        # 使用子查询获取每个客户端的最新记录ID
        subquery = db.query(
            Record.name,
            db.func.max(Record.timestamp).label('max_timestamp')
        ).group_by(Record.name).subquery()
        
        return db.query(Record).join(
            subquery,
            (Record.name == subquery.c.name) & 
            (Record.timestamp == subquery.c.max_timestamp)
        ).all()


class AlertDAO:
    """告警数据访问对象"""
    
    @staticmethod
    def create(db, alert_data):
        """创建新告警"""
        alert = Alert(**alert_data)
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert
    
    @staticmethod
    def get_unresolved(db):
        """获取未解决的告警"""
        return db.query(Alert).filter(Alert.resolved == False).all()
    
    @staticmethod
    def resolve(db, alert_id):
        """解决告警"""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            db.commit()
            return True
        return False


class ConfigDAO:
    """配置数据访问对象"""
    
    @staticmethod
    def get_all(db):
        """获取所有配置"""
        return db.query(Config).all()
    
    @staticmethod
    def get_by_key(db, key):
        """根据键获取配置"""
        return db.query(Config).filter(Config.key == key).first()
    
    @staticmethod
    def set(db, key, value, description=None):
        """设置配置"""
        config = db.query(Config).filter(Config.key == key).first()
        if config:
            config.value = value
            config.description = description
        else:
            config = Config(key=key, value=value, description=description)
            db.add(config)
        db.commit()
        db.refresh(config)
        return config
    
    @staticmethod
    def delete(db, key):
        """删除配置"""
        config = db.query(Config).filter(Config.key == key).first()
        if config:
            db.delete(config)
            db.commit()
            return True
        return False


class UserDAO:
    """用户数据访问对象"""
    
    @staticmethod
    def get_all(db):
        """获取所有用户"""
        return db.query(User).all()
    
    @staticmethod
    def get_by_username(db, username):
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def create(db, user_data):
        """创建新用户"""
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_login_time(db, username):
        """更新用户登录时间"""
        user = db.query(User).filter(User.username == username).first()
        if user:
            user.last_login = datetime.utcnow()
            db.commit()
            return True
        return False