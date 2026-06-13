# 🎵 TikTok Registrar

> TikTok 批量账号注册机 + 控制台：后端跑在 GitHub Actions，前端控制台本地/VPS 部署。

## ⚠️ 合规声明

本项目仅供**技术学习与研究**用途。批量注册账号违反 TikTok 服务条款，可能导致账号封禁、IP 封锁，部分场景下涉及法律风险。使用者自行承担一切后果。

---

## 🏗 架构概览

```
┌──────────────────────────────────────────────────┐
│  后端 backend/ (GitHub Actions, 手动/push 触发)   │
│  ├─ Playwright + stealth 跑 TikTok 注册流程       │
│  ├─ TempMail 对接 mail.Minecraft-cn.net 接收验证码│
│  ├─ OpenCV 解滑块验证码                            │
│  └─ HMAC-SHA256 签名后 POST 凭证到 webhook        │
└──────────────────────────────────────────────────┘
                       ↓ HTTPS/HTTP POST
┌──────────────────────────────────────────────────┐
│  前端 frontend/ (VPS 部署)                         │
│  ├─ FastAPI (Python)                              │
│  │   ├─ 接收 webhook + 验签                        │
│  │   ├─ SQLite (WAL 模式) + JSON + Netscape 三存  │
│  │   └─ 查询/统计/导出 API                         │
│  └─ Vue 3 + Naive UI (Web 控制台)                 │
│      ├─ 仪表盘 (ECharts 趋势图)                    │
│      ├─ 账号列表 (虚拟滚动表格)                    │
│      ├─ 账号详情 (cookie/sessionid)                │
│      └─ 导出 JSON / CSV / cookies.txt              │
└──────────────────────────────────────────────────┘
```

## 📂 项目结构

```
tiktokreg/
├── backend/                # 后端：GitHub Actions 注册机
│   ├── core/
│   │   ├── browser.py          # Playwright + stealth + 指纹
│   │   ├── tempmail_client.py  # 临时邮箱 API 客户端
│   │   ├── human_emulator.py   # 贝塞尔轨迹 + 打字节奏
│   │   ├── register_pipeline.py# 注册主流程
│   │   ├── webhook_exporter.py # HMAC 签名推送
│   │   ├── proxy_manager.py    # 代理管理（默认走本机）
│   │   ├── credential_extractor.py
│   │   └── captcha/
│   │       ├── slider_solver.py# OpenCV 解滑块
│   │       └── rotate_solver.py# 3D 旋转（预留）
│   ├── main.py
│   ├── config.yaml
│   └── requirements.txt
│
├── frontend/               # 前端：本地/VPS 控制台
│   ├── api/                # FastAPI
│   │   ├── routers/
│   │   │   ├── webhook.py
│   │   │   ├── accounts.py
│   │   │   ├── export.py
│   │   │   └── stats.py
│   │   ├── models.py
│   │   ├── storage.py      # 三合一存储
│   │   ├── security.py     # Basic Auth + HMAC
│   │   ├── database.py     # SQLite WAL
│   │   └── main.py
│   ├── web/                # Vue 3
│   │   └── src/views/
│   │       ├── Dashboard.vue
│   │       ├── AccountsList.vue
│   │       ├── AccountDetail.vue
│   │       └── Settings.vue
│   └── Dockerfile          # 多阶段构建
│
├── .github/workflows/register.yml  # GitHub Actions
├── docker-compose.yml      # 前端一键部署
├── .env.example
└── README.md
```

---

## 🚀 快速开始

### 步骤 1：克隆仓库

```bash
git clone https://github.com/weige0831/tiktokreg.git
cd tiktokreg
```

### 步骤 2：部署前端控制台（VPS）

#### 2.1 配置环境变量

```bash
cp .env.example .env
nano .env
```

填写：
```ini
ADMIN_USER=admin
ADMIN_PASSWORD=YourStrongPassword123   # 留空则首次启动自动生成
WEBHOOK_SECRET=YourRandomSecret32Chars # 留空则首次启动自动生成
```

#### 2.2 启动服务

```bash
docker-compose up -d --build
docker logs -f tiktokreg-frontend  # 查看自动生成的密码
```

浏览器访问：`http://你的VPS_IP:8080`

### 步骤 3：配置 GitHub Actions Secrets

进入 GitHub 仓库 → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`：

| Secret 名 | 值 |
|----------|-----|
| `TEMPMAIL_BASE_URL` | `https://mail.Minecraft-cn.net` |
| `WEBHOOK_URL` | `http://你的VPS_IP:8080/api/webhook/accounts` |
| `WEBHOOK_SECRET` | 与 `.env` 里的 `WEBHOOK_SECRET` 完全一致 |

### 步骤 4：触发注册任务

**方式 A：手动触发（推荐）**

进入仓库 → `Actions` → `TikTok Batch Register` → `Run workflow`

输入：
- `count`：注册数量（建议 5-10）
- `concurrency`：并发数（建议 2-3）

**方式 B：Push 触发（调试用）**

任何对 `backend/**` 或 workflow 文件的 push 都会自动触发，使用默认参数（count=2, concurrency=1）做冒烟测试。

### 步骤 5：查看结果

- Actions 日志：`Actions` → 选最近的运行 → 查看注册日志
- 控制台：刷新 `http://你的VPS_IP:8080` 查看新增账号

---

## 🔑 凭证存储（三合一）

每个成功注册的账号会同时写入 3 个位置：

1. **SQLite** (`data/accounts.db`)：主索引库，支持查询/统计
2. **JSON 文件** (`data/accounts/<email>/info.json`)：人类可读详情
3. **Netscape cookies.txt** (`data/accounts/<email>/cookies.txt`)：可导入：
   - yt-dlp / yt-dl
   - IDM / Downie
   - 指纹浏览器（BitBrowser / AdsPower）
   - curl / wget

控制台还支持：
- 一键导出全量 JSON
- 一键导出 CSV（Excel 兼容）
- 单账号 Netscape cookies.txt 下载

---

## ⚙️ 高级配置

### 启用代理

默认走 GitHub Actions 本机 IP（Azure 数据中心，**易被风控**）。如需启用代理：

1. 在仓库根目录创建 `proxies.txt`（每行一个代理）：
   ```
   http://user:pass@1.2.3.4:8080
   http://user:pass@5.6.7.8:8080
   ```

2. 修改 `backend/config.yaml`：
   ```yaml
   proxy:
     enabled: true
     max_uses_per_proxy: 3
   ```

3. 提交后 Actions 会自动加载

### 修改并发/数量

- **手动触发**：在 `Run workflow` 时输入
- **Push 触发**：修改 `.github/workflows/register.yml` 中的默认值

### 调整行为模拟参数

`backend/config.yaml` 中的 `human` 段控制：
- 打字延迟
- 鼠标移动速度
- 滑块拖拽时长
- 操作停顿

---

## 🔧 本地开发

### 后端调试（本地）

```bash
cd backend
pip install -r requirements.txt
playwright install chromium

# 设置环境变量
export TEMPMAIL_BASE_URL=https://mail.Minecraft-cn.net
export WEBHOOK_URL=http://localhost:8080/api/webhook/accounts
export WEBHOOK_SECRET=your_secret

# 单账号测试
python main.py --count 1 --concurrency 1
```

### 前端开发模式（热重载）

```bash
# 终端 1：启动 FastAPI（开发模式）
cd frontend/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8080

# 终端 2：启动 Vue 开发服务器
cd frontend/web
npm install
npm run dev   # → http://localhost:5173
```

---

## 🛡 安全提示

- ⚠️ **默认 HTTP 无加密**：cookie/sessionid 在网络中明文传输。生产环境务必加 HTTPS（nginx 反代 + Let's Encrypt）
- 🔑 **Webhook Secret**：必须 ≥ 32 字符，且 GitHub Actions 和前端保持一致
- 🛡 **Basic Auth**：前端控制台强制 Basic Auth，密码首次启动自动生成（查看 `docker logs`）
- 📁 **数据备份**：`data/` 目录包含所有账号凭证，建议定期备份并加密

---

## 🐛 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| Actions 跳过注册 | Secrets 未配置 | 在仓库设置中添加 3 个 Secrets |
| 注册成功率低 | GitHub IP 被风控 | 启用住宅代理 |
| 滑块验证码失败 | OpenCV 求解失败 3 次 | 重试，或后续接入付费打码 |
| Webhook 推送 401 | 签名密钥不一致 | 检查 GitHub 和 .env 的 WEBHOOK_SECRET |
| 控制台 401 | Basic Auth 凭据错 | 清除浏览器 localStorage 重新输入 |

---

## 📜 License

MIT

## 🙏 致谢

- [Playwright](https://playwright.dev/)
- [PuzzleCaptchaSolver](https://github.com/vsmutok/PuzzleCaptchaSolver) - 滑块求解算法参考
- [tiktok-captcha-solver](https://github.com/Gisnsl/tiktok-captcha-solver) - TikTok 滑块逆向参考
- [tempmail-server](https://github.com/lm36/tempmail-server) - 临时邮箱服务
- [FastAPI](https://fastapi.tiangolo.com/) + [Naive UI](https://www.naiveui.com/)
