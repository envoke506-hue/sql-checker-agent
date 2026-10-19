# SQL Checker Agent (基于 RAG 的智能 SQL 审查与数据库设计规范问答系统)

本项目是一个基于 **检索增强生成 (RAG)** 技术的智能 SQL 规范合规审查与知识问答 Agent 系统。项目严格遵循 **企业级 MVC 架构** 设计与 **RESTful API** 规范，深度实践并落地了切块治理、Embedding、稠密向量库、BM25 倒排索引、双路混合检索、RRF 倒数排名融合算法、Lost-in-the-Middle 上下文头尾编排、Double Check 二次断言防幻觉核验及标准 Markdown 报告生成全套核心技术。

---

## 📚 模块化文档体系导航 (Documentation Hub)

为方便快速查阅与高效维护，完整文档已按工程领域拆分为独立专题：

| 专题文档 | 核心内容概述 |
| :--- | :--- |
| 🏛️ [**系统架构与核心 RAG 算法**](./doc/architecture.md) | MVC 分层设计、Docs as Code 规范治理、双轨文本职责分离、RRF 融合数学公式、Lost-in-the-Middle 编排、Double Check 防幻觉核验及初学者常见 Q&A |
| 🗄️ [**向量数据库技术选型方案**](./doc/vector_database_selection.md) | ChromaDB、NumPy、FAISS、Milvus、pgvector、ES 深度横向评测矩阵、企业级决策树与从 NumPy 演进至 Chroma 的收益 |
| 🚀 [**快速启动与部署运行指南**](./doc/quickstart.md) | Python 3.12+ 与 uv 环境准备、本地 Ollama 向量模型拉取、环境变量 `.env` 配置表、服务启动与 Web 控制台使用说明 |
| 📡 [**RESTful 核心接口规范**](./doc/api_reference.md) | `POST /sql/audits`、`POST /spec/queries`、`GET /health` 等核心 API 的请求体、响应体信封 `ApiResponse[T]`、业务错误码及示例 |
| 🧪 [**自动化测试与评测体系**](./doc/testing_and_evaluation.md) | 100% 覆盖率的分阶段自动化测试套件运行命令、76 条反向案例库说明及子代理并发批量评测报告 |
| 🗂️ [**切块可视化预览导览**](./data/chunks_preview/README.md) | 知识库 6 大标准原子切块的元数据、专有词表、纯净正文与检索增强文本独立卡片预览 |

---

## 🌟 核心技术亮点速览

1. **企业级 Docs as Code 规范治理与通用 AST 解析**：源规范《数据库规范.md》注入 YAML Frontmatter，通用 `MarkdownASTParser` 0 硬编码动态解析，支持代码反引号专有词自动提炼与纯 Markdown 自然降级；
2. **双轨文本设计 (Dual Representation)**：`embedding_text` 注入层级面包屑充当向量检索钩子；`display_text` 保持纯净正文专供大模型 Prompt 与前端呈现，彻底杜绝标签污染；
3. **双路索引与增量哈希守卫**：本地 Ollama 2560 维稠密向量 + 定制分词 BM25 稀疏倒排；基于 SHA-256 哈希比对实现 **0 毫秒秒级冷启动**；
4. **SQL 特征感知与 RRF 融合排序**：前置分解 5~7 个高靶向性规范查询，利用倒数排名融合算法（RRF）抹平量纲差异，违规条款 100% 召回；
5. **Lost-in-the-Middle 头尾上下文编排**：依据大模型“首尾高、中间低”注意力曲线，交替将高相关条款排布在 Prompt 两端；
6. **确定性 Double Check 防幻觉断言**：通过有效编号校验与白名单特征词反向交叉核验，坚决掐死大模型幻觉误报。

---

## 🚀 极速开箱上手 (3 步启动)

### 1. 准备环境与安装依赖
```bash
# 本地启动 Ollama 并拉取 2560 维向量模型
ollama run qwen3-embedding:4b

# 安装依赖
uv venv .venv
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

### 2. 配置环境变量 (`.env`)
复制 `.env.example` 为 `.env` 并按需调整（详细说明参见 [部署指南](./doc/quickstart.md)）。

### 3. 启动后端服务
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- 🌟 **交互式 Web 控制台**：👉 **`http://127.0.0.1:8000/`** 或 **`http://127.0.0.1:8000/ui`**
- 📖 **Swagger 交互式 API 文档**：👉 **`http://127.0.0.1:8000/docs`**

---

## 🧪 一键运行测试套件

```bash
# 运行 Docs as Code 动态切块专项与逐步演练
python tests/test_dynamic_ast_chunking.py
python tests/demo_parse_step_by_step.py

# 运行双路索引构建与端到端智能审查
python tests/test_phase2_indexing.py
python tests/test_phase3_retrieval.py
python tests/test_phase4_audit_e2e.py

# 运行 Web UI 端点与全链路接口测试
python tests/test_phase1_controllers.py
python tests/test_web_ui.py
```
> 完整测试命令与回归评测详情请参阅 [测试与评测手册](./doc/testing_and_evaluation.md)。

---

## 📂 项目精简工程目录

```text
sql-checker-agent/
├── app/                         # 核心源码包 (遵循企业级 MVC 分层)
│   ├── core/                    # 全局配置、依赖注入 (DI)、异步连接池、业务异常
│   ├── models/                  # M 层: 细粒度 DTO (请求/响应/信封) 与 Entity 实体
│   ├── repositories/            # R 层: 纯异步持久层 (NumPy向量、BM25倒排、DocStore、Ollama、LLM)
│   ├── services/                # S 层: 业务编排服务 (动态切块、双路检索、RRF融合、编排、防幻觉断言)
│   ├── controllers/             # C 层: RESTful 控制器路由 (/sql, /spec, /knowledge, /health)
│   ├── static/                  # 前端静态单页面控制台 (Vue 3 + Tailwind CSS)
│   └── main.py                  # FastAPI 应用入口与全局异常拦截器
│
├── data/
│   ├── indices/                 # 离线持久化索引 (dense_vectors.npy, bm25_model.pkl, chunks_store.json)
│   └── chunks_preview/          # 切块结果可视化 Markdown 独立导览卡片
│
├── doc/                         # 模块化技术文档库
│   ├── architecture.md          # 架构全景、五大 RAG 机制与常见 Q&A
│   ├── quickstart.md            # 快速部署、环境变量与 Web UI 操作指南
│   ├── api_reference.md         # RESTful 接口清单与报文契约
│   ├── testing_and_evaluation.md# 自动化测试与 76 条反例评测
│   ├── 数据库规范.md             # 遵循 YAML Frontmatter 规范标准的源知识库文档
│   └── negative_cases/          # 76 条反向案例评测语料库
│
└── tests/                       # 自动化测试套件 (覆盖率 100%)
```
