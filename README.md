# Python版分布式机群监管系统

## 项目结构

```
python-overwatch/
├── common/          # 公共模块，包含数据模型和工具
├── register/        # 注册中心服务
├── server/          # 监控服务器
├── client/          # 监控客户端
├── web/            # Web界面
└── requirements.txt # Python依赖包
```

## 技术栈

- **Web框架**: FastAPI
- **异步处理**: asyncio
- **数据库ORM**: SQLAlchemy
- **系统信息**: psutil
- **数据验证**: Pydantic
- **模板引擎**: Jinja2

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行步骤

1. 启动注册中心: `python register/main.py`
2. 启动监控服务器: `python server/main.py`
3. 启动监控客户端: `python client/main.py`
4. 启动Web界面: `python web/main.py`

## project by SA25225014李嘉琦