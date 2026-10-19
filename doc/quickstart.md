# 快速启动与部署运行指南 (Quickstart & Deployment)

本文档提供 `sql-checker-agent` 的环境依赖准备、本地运行部署、环境变量配置表及 Web 控制台操作指南。

---

## 一、 环境依赖准备

- **操作系统**：Windows 10/11、macOS、Linux
- **Python 版本**：Python 3.12+ (推荐使用现代包管理工具 `uv`)
- **本地 Ollama 向量模型**：
  启动本地 Ollama 并拉取 2560 维的高精 Embedding 模型：
  ```bash
  ollama run qwen3-embedding:4b
  ```

---

## 二、 安装项目依赖

推荐使用 `uv` 极速创建虚拟环境并安装依赖：

```bash
# 1. 创建虚拟环境
uv venv .venv

# 2. 激活虚拟环境 (Windows PowerShell)
.venv\Scripts\Activate.ps1

# (若在 Linux / macOS)
# source .venv/bin/activate

# 3. 安装依赖清单 (包含 FastAPI、Pydantic、NumPy、Rank-BM25、PyYAML 等)
uv pip install -r requirements.txt
```

---

## 三、 环境变量配置 (`.env`)

复制根目录的 `.env.example` 为 `.env`：

```ini
# 服务运行模式与基础路由
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
API_V1_PREFIX=/api/v1

# 本地 Ollama 向量模型配置 (Embedding)
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:4b
OLLAMA_TIMEOUT_SECONDS=60

# 云端中转站大模型配置 (LLM 推理)
RELAY_API_BASE_URL=http://gsccswitch.sepzg.vip/v1
RELAY_API_KEY=sk-x9Gp6vrNe469SQH8yLuNiT4QKSQOmYKeCBlj0SnUUtGtJ2Ht
RELAY_LLM_MODEL=deepseek-flash
RELAY_TIMEOUT_SECONDS=120.0

# 规范知识库文档路径与持久化目录
SPEC_DOC_PATH=D:\WorkData\python_work_space\sql-checker-agent\doc\数据库规范.md
STORAGE_DIR=data/indices
```

### 关键配置项说明

| 配置键名 | 说明 | 默认值 / 示例 |
| :--- | :--- | :--- |
| `OLLAMA_BASE_URL` | 本地 Ollama 服务监听端点 | `http://127.0.0.1:11434` |
| `OLLAMA_EMBEDDING_MODEL` | 向量计算模型 | `qwen3-embedding:4b` |
| `RELAY_API_BASE_URL` | OpenAI 兼容的大模型推理 API 基础端点 | 标准 v1 端点 |
| `RELAY_API_KEY` | 大模型中转站/云端访问密钥 | `sk-...` |
| `RELAY_LLM_MODEL` | 主力推理大模型 | `deepseek-flash` |
| `SPEC_DOC_PATH` | 《数据库规范.md》源文档绝对路径 | `doc/数据库规范.md` |
| `STORAGE_DIR` | 双路索引（向量矩阵、BM25 模型、切块正文）持久化落盘目录 | `data/indices` |

---

## 四、 启动后端服务

在项目根目录下执行：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动时，控制台将输出启动生命周期检查报告：
1. 连通性体检：并发检查本地 Ollama 与中转站 DeepSeek 的心跳延迟；
2. 知识库索引感知：读取规范文件 SHA-256，未修改时 **0 毫秒秒级加载**，发生修改则自动重新计算向量并重建索引；
3. 输出交互式访问地址。

---

## 五、 交互式 Web 控制台 (SPA)

项目内置了现代化的单页面控制台（SPA），**无需配置 Node.js 或执行 npm build**，启动后端即可通过浏览器开箱即用：

- **访问地址**：👉 **`http://127.0.0.1:8000/`** 或 **`http://127.0.0.1:8000/ui`**
- **Swagger API 文档**：👉 **`http://127.0.0.1:8000/docs`**

### 核心功能板块使用说明
1. **📋 SQL 合规审查与一键重构**：
   - 内置“🚨 典型违规反例”与“🌟 100%合规正例”一键快速填入按钮；
   - 回复内容仅保留“不满足项与整改方案（逐条带 `[n]` 编号引用依据）”与“修改后的 SQL”，避免冗长排版；
   - 顶部红标横幅给出合规判定与合规得分，支持“一键复制代码”。
2. **💡 数据库规范知识库智能问答**：
   - 支持常见高频规范快捷提问气泡（如金额类型、基类审计字段、主键类型等）；
   - 显示带有 `[1]`, `[2]` 规范角标引用的专业解答与原文溯源附录。
3. **📚 知识库切块与索引管理运维**：
   - 直观查看 6 大原子切块统计、向量维度（2560维）、文档哈希值与双路索引状态；
   - 提供“⚡ 强制全量重建双路索引”一键运维触发功能。
