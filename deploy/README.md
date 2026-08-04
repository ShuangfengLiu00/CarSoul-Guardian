# CarSoul Guardian 部署辅助

本目录存放部署、启动相关脚本。

## 文件

| 文件 | 用途 |
|------|------|
| `start-dev.ps1` | Windows 一键启动本地开发环境（后端 + 前端） |
| `start-dev.sh` | Linux/macOS 一键启动本地开发环境 |
| `docker-up.ps1` | 一键启动 Docker 全栈（postgres + redis + backend + frontend） |

## 快速开始

### 本地开发（需已安装 Node 20+ 与 Python 3.11+）
```powershell
.\deploy\start-dev.ps1
```

### Docker 全栈
```powershell
.\deploy\docker-up.ps1
```
