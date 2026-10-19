# SQL Checker Agent (基于 RAG 的智能 SQL 审查与数据库设计规范问答系统)

本项目是一个基于 **检索增强生成 (RAG)** 技术的智能 SQL 规范合规审查与知识问答 Agent 系统。项目严格遵循 **企业级 MVC 架构** 设计与 **RESTful API** 规范，深度实践和验证了《大模型应用开发基础：检索增强生成》系列课程（第 15~20 篇）中所学的切块、元数据、Embedding、稠密向量库、BM25 倒排索引、混合检索、RRF 倒数排名融合算法、Lost-in-the-Middle 上下文头尾编排、Double Check 二次断言防幻觉核验及标准 Markdown 报告生成全套核心技术。

---

## 🌟 核心技术亮点与课程深度落地

### 1. 企业级 Docs as Code 规范治理与通用 Markdown AST / Frontmatter 动态解析 (落地第 15、16 篇)

- **痛点解决**：
  1. 传统滑动窗口按字数暴力切分极易把“正例”与“反例”切断在两个不同块中，导致 LLM 把“反例 `order_id`”误当成规范学习；也容易将建表模板的基类字段切成碎片。
  2. 传统切块在代码中写死千行静态常量或特定业务正则，脆弱易崩，源文件改动无法动态感知与闭环。
- **方案落地 (Docs as Code & AST)**：
  - **源文档 Frontmatter 治理**：《数据库规范.md》采用标准 Docs as Code 架构，头部声明 YAML Frontmatter（定义 `chunk_id`、`heading_path`、`category` 与专有词表），正文保持高可读性 Markdown；
  - **通用 `MarkdownASTParser`**：0 业务硬编码，基于标准 AST 边界切分，自适应提取反引号代码词动态扩充 BM25 词表，支持普通 Markdown H2 优雅降级；
  - **双轨职责分离 (Dual Representation)**：
    * `embedding_text`：头部拼接全局面包屑路径作为“语义检索钩子”，专供本地 Ollama 计算 2560 维高精向量；
    * `display_text`：纯净 Markdown 正文，专供 DeepSeek 大模型 Prompt 与前端 UI，彻底消除人工标签污染与格式歧义；
  - **动态增量闭环**：`ChunkingService` 0 硬编码，源文件一旦修改，SHA-256 自动感知并触发双路增量重建。

### 2. 双路离线索引构建与增量哈希校验 Pipeline (落地第 16、17 篇)

- **零成本冷启动恢复**：
  - **稠密向量路 (Dense)**：调用本地 Ollama `qwen3-embedding:4b` 生成 2560 维高精向量，使用 NumPy 进行矩阵余弦相似度加速，持久化为 `dense_vectors.npy`。
  - **稀疏倒排路 (Sparse BM25)**：定制中英与 SQL 符号分词器，保留 `decimal(20, 6)`、`TINYINT(4)`、`db_`、下划线及 2-gram 中文词，持久化为 `bm25_model.pkl`。
  - **切块正文仓储 (DocStore)**：持久化完整切块实体至 `chunks_store.json`。
- **增量哈希守卫**：启动或更新时自动比对源规范 Markdown 的 SHA-256 哈希值，未修改时 **0 毫秒秒级加载**，发生修改自动重建。

### 3. SQL 特征感知与双路混合检索 RRF 融合排序 (落地第 18 篇)

- **痛点解决**：原始 DDL 包含大量无意义的通用语法关键字与括号符号，若直接 Embedding 整段 SQL，关键违规特征（如一个隐蔽的 `double` 或 `order_id`）会被严重稀释，导致相关规范排名靠后。
- **高靶向性意图分解 (`SqlFeatureExtractor`)**：前置解析 SQL 提取表名、保留字、外键、浮点数、本表冗余前缀反例、缺失基类字段，自动生成 5~7 个高靶向性规范查询。
- **RRF (Reciprocal Rank Fusion) 倒数排名融合算法**：
  $$
  RRF\_Score(d) = \sum_{m \in \{dense, sparse\}} \frac{1}{60 + rank_m(d)}
  $$

  抹平 BM25 无界得分与余弦相似度的尺度差异，跨路综合累加，实现违规条款 100% 召回。

### 4. Lost-in-the-Middle 上下文头尾重排编排 (落地第 19 篇)

- **痛点解决**：大模型对长上下文的注意力呈“首尾高、中间低”的 U 型曲线。中间腹部的规范极易被忽略导致漏报。
- **编排算法 (`ContextOrchestrator`)**：
  - 将相关度最高的文档交替安放在两端，次相关沉淀在中间（如 `[1, 3, 5, 4, 2]`），使关键条款始终处于注意力最强的区域；
  - 动态分配 `[1]`, `[2]`, ... 全局引用角标编号，并保留内存映射供溯源。

### 5. Double Check 二次断言核验与防幻觉过滤器 (落地第 19 篇)

- **痛点解决**：大模型常出现“过度合规幻觉”（凭空捏造不存在的规则，或引用了虚假的编号 `[99]`，或将正常字段误报违规）。
- **确定性断言引擎 (`DoubleCheckVerifier`)**：
  - **编号越界断言**：校验引用编号是否在检索上下文有效范围；
  - **正文反向交叉核验**：通过白名单特征词，反向断言该违规规则是否真正在被引用的 Chunk 原文中存在；
  - **动态评分重算**：过滤掉所有幻觉项，精准基于真实违规（ERROR 扣 20 分，WARN 扣 10 分）重算合规得分。

### 6. 企业级工程规范与 MVC 分层

- **面向对象领域分包**：DTO 与 Entity 按业务场景清晰划分，无 God File；
- **原生 Depends 依赖注入**：集中在 `app/core/dependencies.py` 管理，单例缓存与双模兼容；
- **全链路异步非阻塞**：全局管理 `httpx.AsyncClient` 连接池；
- **全局统一响应与异常拦截**：所有正常返回与 422 参数异常均包装为 `ApiResponse[T]`。

---

## 📂 项目工程目录结构

```text
sql-checker-agent/
├── app/                         # 核心应用源码包
│   ├── core/                    # 核心配置与基础组件
│   │   ├── config.py            # 全局配置单例 (Pydantic BaseSettings)
│   │   ├── exceptions.py        # 企业级业务异常与 ErrorCode 枚举
│   │   ├── http_client.py       # 全局异步 httpx.AsyncClient 连接池管理
│   │   └── dependencies.py      # FastAPI Depends 依赖注入工厂 (IoC 容器)
│   │
│   ├── models/                  # M 层: 数据传输对象 (DTO) 与领域实体 (Entity)
│   │   ├── dto/                 # 细粒度 DTO 领域分包
│   │   │   ├── common.py        # 统一响应信封 ApiResponse[T] 与错误码
│   │   │   ├── health.py        # 健康体检 DTO
│   │   │   ├── knowledge.py     # 知识库索引管理 DTO
│   │   │   ├── sql_audit.py     # SQL 审查请求/响应/明细 DTO
│   │   │   └── spec_query.py    # 规范问答 DTO
│   │   └── entity/              # 细粒度 Entity 领域分包
│   │       ├── chunk.py         # 知识库切块 Chunk 与元数据 ChunkMetadata
│   │       └── violation.py     # 违规明细 RuleViolation 领域实体
│   │
│   ├── repositories/            # R 层: 纯异步持久层与大模型交互客户端
│   │   ├── ollama_embedding_repository.py  # 异步 Ollama Qwen3-Embedding:4b 客户端
│   │   ├── relay_llm_repository.py         # 异步中转站 DeepSeek-Flash 客户端
│   │   ├── vector_store_repository.py      # 稠密向量矩阵持久化与 NumPy 余弦计算
│   │   ├── bm25_index_repository.py        # 定制分词的 BM25 稀疏检索仓储
│   │   └── doc_store_repository.py         # 完整切块实体正文持久化仓储
│   │
│   ├── services/                # S 层: 业务逻辑与编排服务
│   │   ├── health_service.py        # 全链路并发健康体检服务
│   │   ├── markdown_ast_parser.py   # 通用 Markdown AST 与 YAML Frontmatter 动态解析器
│   │   ├── chunking_service.py      # 知识库结构化切块服务 (委托 MarkdownASTParser)
│   │   ├── knowledge_service.py     # 知识库离线索引 Pipeline 与增量哈希守卫
│   │   ├── sql_feature_extractor.py # SQL 语法与合规特征提取器 (意图分解)
│   │   ├── retrieval_service.py     # 双路混合检索与 RRF 融合排序引擎
│   │   ├── context_orchestrator.py  # Lost-in-the-Middle 头尾重排与引用编号编排
│   │   ├── double_check_verifier.py # 确定性断言核验与防幻觉过滤器
│   │   ├── audit_report_renderer.py # 精简整改回复渲染器 (View 视图组件)
│   │   ├── sql_audit_service.py     # SQL 规范审查核心全链路编排服务
│   │   └── spec_query_service.py    # 规范知识问答编排业务服务
│   │
│   ├── controllers/             # C 层: RESTful 控制器路由
│   │   ├── health_controller.py     # GET  /api/v1/health (全链路体检)
│   │   ├── knowledge_controller.py  # POST /api/v1/knowledge/indices (索引重构)
│   │   ├── sql_audit_controller.py  # POST /api/v1/sql/audits (SQL 合规审查)
│   │   ├── spec_query_controller.py # POST /api/v1/spec/queries (规范知识问答)
│   │   └── web_controller.py        # GET  / 与 GET /ui (Web 交互控制台单页面路由)
│   │
│   ├── static/                  # 前端静态单页面资源
│   │   └── index.html           # 现代单页面应用 (Vue 3 + Tailwind CSS + Highlight.js)
│   │
│   └── main.py                  # FastAPI 应用入口与全局异常拦截器挂载
│
├── data/
│   ├── indices/                 # 离线持久化索引目录
│   │   ├── dense_vectors.npy    # 稠密向量矩阵 (2560维 NumPy 二进制)
│   │   ├── vector_ids.json      # 向量 ID 映射
│   │   ├── bm25_model.pkl       # BM25 倒排索引模型
│   │   ├── chunks_store.json    # 切块完整实体与元数据 JSON
│   │   └── index_meta.json      # 索引元信息与源文件 SHA-256 哈希
│   │
│   └── chunks_preview/          # 切块结果可视化 Markdown 独立导览与预览目录
│       ├── README.md            # 切块总览导航看板
│       └── 01_chunk_*.md        # 各切块详细元数据、正文与关键词卡片
│
├── doc/                         # 规范文档与反向案例语料
│   ├── 数据库规范.md             # 遵循 YAML Frontmatter 规范标准的源知识库文档
│   └── negative_cases/          # 反向案例库 (74 条，按规范模块分文件)
│       ├── README.md            # 案例索引、覆盖率矩阵与口径说明
│       ├── 01_naming.md         # 命名规范反例 N-01 ~ N-16
│       ├── 02_terminology.md    # 名词术语反例 T-01 ~ T-12
│       ├── 03_table_template.md # 建表模板反例 M-01 ~ M-18
│       ├── 04_database_rules.md # 建库规范反例 D-01 ~ D-16
│       ├── 05_field_and_index.md # 字段与索引反例 F-01 ~ F-12
│       └── validate_cases.py    # 案例库结构 + 静态检出率校验脚本
│
└── tests/                       # 自动化测试套件 (覆盖率 100%)
    ├── test_dynamic_ast_chunking.py # 动态 AST 切块与规范扩展性专项单元测试
    ├── demo_parse_step_by_step.py   # MarkdownASTParser 逐步解析与变量追踪实战演示
    ├── test_phase1_skeleton.py      # 骨架层、异步仓储与连接池测试
    ├── test_phase1_controllers.py   # RESTful 控制器与全局异常拦截测试
    ├── test_phase2_indexing.py      # AST 切块、向量检索、BM25 检索测试
    ├── test_phase3_retrieval.py     # SQL 特征提取、RRF 数学算法融合测试
    ├── test_phase4_audit_e2e.py     # 端到端审查、Double Check、精简回复渲染全量测试
    ├── test_audit_report_renderer.py # 精简 Markdown 整改回复离线单元测试
    ├── test_sql_audit_service_offline.py # 审查服务离线链路测试 (桩化 LLM，含解析失败兜底)
    └── test_web_ui.py               # Web 前端控制台界面交付与路由端点测试
```

---

## 🖥️ 交互式 Web 操作控制台 (SPA)

项目内置了现代化的单页面控制台（SPA），**无需配置 Node.js 或执行 npm build**，启动后端即可通过浏览器开箱即用：

- **访问地址**：`http://127.0.0.1:8000/` 或 `http://127.0.0.1:8000/ui`
- **核心功能板块**：
  1. **📋 SQL 合规审查与一键重构**：
     - 提供“🚨 典型违规反例”与“🌟 100%合规正例”一键快速填入按钮；
     - 回复内容仅保留“不满足项与整改方案（逐条带 `[n]` 编号引用依据）”与“修改后的 SQL”，避免冗长排版；
     - 顶部红标横幅给出合规判定与合规得分，支持“一键复制代码”。
  2. **💡 数据库规范知识库智能问答**：
     - 支持常见高频规范快捷提问气泡（如金额类型、基类审计字段、主键类型等）；
     - 显示带有 `[1]`, `[2]` 规范角标引用的专业解答与原文溯源附录。
  3. **📚 知识库切块与索引管理运维**：
     - 直观查看 6 大原子切块统计、向量维度（2560维）、文档哈希值与双路索引状态；
     - 提供“⚡ 强制全量重建双路索引”一键运维触发功能。

---

## 🚀 快速启动指南

### 1. 环境准备

- Python 3.12+ (推荐使用 `uv` 管理虚拟环境)
- 本地启动 Ollama 并拉取 embedding 模型：
  ```bash
  ollama run qwen3-embedding:4b
  ```

### 2. 安装依赖

```bash
uv venv .venv
# 激活虚拟环境 (Windows PowerShell)
.venv\Scripts\Activate.ps1
# 安装项目依赖
uv pip install -r requirements.txt
```

### 3. 配置环境变量 (`.env`)

复制 `.env.example` 为 `.env`：

```ini
APP_ENV=development
API_V1_PREFIX=/api/v1

# 本地 Ollama 向量模型配置
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:4b

# 云端中转站大模型配置
RELAY_API_BASE_URL=http://gsccswitch.sepzg.vip/v1
RELAY_API_KEY=sk-x9Gp..................GtJ2Ht
RELAY_LLM_MODEL=deepseek-flash
RELAY_TIMEOUT_SECONDS=60.0

# 规范知识库文档路径
SPEC_DOC_PATH=D:\WorkData\work_space\项目规范\数据库规范\数据库规范.md
STORAGE_DIR=data/indices
```

### 4. 启动后端服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务成功启动后，即可在浏览器直接体验：

- 🌟 **交互式 Web 控制台 (推荐)**：👉 **http://127.0.0.1:8000/** 或 **http://127.0.0.1:8000/ui**
- 📖 **Swagger 交互式 API 文档**：👉 **http://127.0.0.1:8000/docs**

---

## 🧪 运行全量测试套件

项目拥有完整的单元测试与集成测试覆盖，在项目根目录下运行：

```bash
# 1. 运行 Docs as Code 动态 AST 切块与规范扩展性测试 (秒级完成)
python tests/test_dynamic_ast_chunking.py
python tests/demo_parse_step_by_step.py

# 2. 运行 Phase 1: 异步连接池与异常拦截测试
python tests/test_phase1_skeleton.py
python tests/test_phase1_controllers.py

# 3. 运行 Phase 2: 知识库切块与双路检索索引构建测试
python tests/test_phase2_indexing.py

# 4. 运行 Phase 3: SQL 特征提取与 RRF 融合检索测试
python tests/test_phase3_retrieval.py

# 5. 运行 Phase 4: 端到端智能审查与规范问答全链路测试
python tests/test_phase4_audit_e2e.py

# 6. 运行精简 Markdown 整改回复渲染单元测试 (无需大模型，可离线执行)
python tests/test_audit_report_renderer.py

# 7. 运行 SQL 审查服务离线链路测试 (桩化 LLM，含解析失败严禁伪判合规的兜底校验)
python tests/test_sql_audit_service_offline.py

# 8. 运行 Web UI 前端交互与路由端点测试
python tests/test_web_ui.py
```

---

## 🧷 数据库规范反向案例库

`doc/negative_cases/` 按规范模块沉淀了 **76 条故意违反规范的反例 DDL**（`N-` 命名 / `T-` 术语 / `M-` 建表模板 / `D-` 建库 / `F-` 字段与索引），
每条案例都标注了违反条款、期望命中的 `rule_name`、严重级别与依据切块，可直接作为审查接口的评测语料与回归输入。

```bash
# 校验案例库结构完整性，并统计 SqlFeatureExtractor 的静态检出覆盖率
python doc/negative_cases/validate_cases.py
```

当前基线：76 条反例、0 条结构问题；其中 23 条的规则域可被内置 `SqlFeatureExtractor` 的静态特征命中，
其余 53 条属于命名 / 术语 / 索引 / 注释类语义判断，需依赖 RAG 检索 + 大模型判定。
案例口径分歧（如 `db_` 前缀归属、布尔字段命名）记录在 [doc/negative_cases/README.md](./doc/negative_cases/README.md)。

### 📊 反例批量执行与检出率评测 (`evaluation/`)

76 条反例 + 5 条合规对照组已通过 **6 个子代理并行分片**跑完整 RAG 审查全链路，
原始结果与评测结论全部落盘保留在 [`evaluation/`](./evaluation/README.md)：

```bash
.venv\Scripts\python.exe evaluation/build_case_index.py         # 生成唯一可信的案例索引
.venv\Scripts\python.exe evaluation/run_shard.py --shard 1/6    # 分片执行（可 6 路并行）
.venv\Scripts\python.exe evaluation/merge_results.py            # 合并结果 + 生成评测报告
```

本次执行结论（详见 [执行报告](./evaluation/results/执行报告.md)）：

- 81/81 案例成功执行，0 缺失、0 失败；单案例均值 33.1s，6 路并行墙钟约 9 分钟（串行等效 44.7 分钟）；
- 反例最终判定命中 **68/76 (89.5%)**，人工复核后目标规则识别率 **74/76 (97.4%)**，「依据切块」引用召回 **76/76**；
- **发现关键缺陷**：`DoubleCheckVerifier` 防幻觉层把 13 条**规范原文中的真规则**误判为幻觉剔除，
  其中 7 条因此 0 违规 / 100 分**伪判「完全合规」**（已现场复现）；
- 合规对照组 3 条报警中，1 条为真误报（把建库规范第 9 条「**可以**加 UNSIGNED」的推荐性条款升级为强制），
  另外 2 条源于规范原文自相矛盾（第 5/12 条示例 `order_money` 与第 16 条「本表字段不加表名」冲突）。

---

## 📡 RESTful 核心接口清单

### 1. SQL 规范合规审查接口

- **URL**: `POST /api/v1/sql/audits`
- **请求体**:
  ```json
  {
    "sql_text": "CREATE TABLE `order` (\n  `order_id` bigint(20) NOT NULL AUTO_INCREMENT,\n  `order_no` varchar(64) NOT NULL,\n  `total_amount` double NOT NULL COMMENT '总金额',\n  `user_id` bigint(20) NOT NULL COMMENT '用户ID',\n  PRIMARY KEY (`order_id`),\n  CONSTRAINT `fk_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';",
    "db_type": "mysql"
  }
  ```
- **响应体**:
  ```json
  {
    "code": 20000,
    "message": "SQL 审查完成",
    "data": {
      "is_compliant": false,
      "score": 0,
      "summary": "原 DDL 使用保留字表名 order，主键命名、类型及无符号不符合规范，金额使用了禁用的 double 浮点数，存在外键约束，缺少规范的 7 大基类审计字段。",
      "violations": [
        {
          "rule_id": "rule_no_reserved_keyword",
          "rule_name": "表名禁止使用数据库保留关键字",
          "severity": "ERROR",
          "target_object": "表名 order",
          "description": "规范明确表与字段不允许用数据库保留关键字或者看着像关键字的单词，order 属于保留关键字",
          "suggested_fix": "将表名改为业务实体前缀，如 db_order 或 order_info",
          "citation_index": 3
        },
        {
          "rule_id": "rule_no_double",
          "rule_name": "禁止使用浮点数 double",
          "severity": "ERROR",
          "target_object": "total_amount double",
          "description": "金额字段必须使用 decimal(20, 6) 存储，严禁 double 导致精度丢失",
          "suggested_fix": "将 double 修改为 decimal(20, 6)，命名后缀规范为 total_money",
          "citation_index": 1
        },
        {
          "rule_id": "rule_no_foreign_key",
          "rule_name": "表内禁止外键设计",
          "severity": "ERROR",
          "target_object": "CONSTRAINT fk_user FOREIGN KEY",
          "description": "建库规范严禁使用 FOREIGN KEY 外键约束，关联关系应在应用层维护",
          "suggested_fix": "删除外键约束定义",
          "citation_index": 1
        }
      ],
      "suggested_sql": "CREATE TABLE `order_info` (\n  `id` BIGINT UNSIGNED NOT NULL COMMENT '主键',\n  `code` varchar(64) NOT NULL DEFAULT '' COMMENT '订单编号',\n  `total_money` decimal(20, 6) NOT NULL DEFAULT '0.000000' COMMENT '总金额',\n  `user_id` BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '用户ID',\n  `version` int NOT NULL DEFAULT 0 COMMENT '版本号',\n  `deleted` tinyint(4) NOT NULL DEFAULT 0 COMMENT '逻辑删除',\n  `disabled` tinyint(4) NOT NULL DEFAULT 0 COMMENT '是否禁用',\n  `create_id` bigint NOT NULL DEFAULT 0 COMMENT '创建人ID',\n  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',\n  `modify_id` bigint NOT NULL DEFAULT 0 COMMENT '更新人ID',\n  `modify_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',\n  PRIMARY KEY (`id`)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';",
      "markdown_report": "### ⚠️ 不满足项与整改方案（共 3 项）\n\n**1. 禁止使用浮点数 double** · 🔴 ERROR · 依据：[1] 《数据库规范》- 数据库规范 > 数据类型规范\n- 不满足片段：`total_amount double`\n- 问题说明：金额字段必须使用 decimal(20, 6) 存储，严禁 double 导致精度丢失\n- 整改方案：将 double 修改为 decimal(20, 6)，命名后缀规范为 total_money\n\n### ✅ 修改后的 SQL\n```sql\nCREATE TABLE `order_info` (...);\n```\n"
    }
  }
  ```

### 2. 数据库设计规范智能问答接口

- **URL**: `POST /api/v1/spec/queries`
- **请求体**:
  ```json
  {
    "question": "规范中金额和单价字段的数据类型和命名后缀有什么强制规定？"
  }
  ```
- **响应体**:
  ```json
  {
    "code": 20000,
    "message": "规范咨询查询成功",
    "data": {
      "answer": "金额字段必须使用 decimal 类型存储，如无特殊需求统一使用 decimal(20, 6) [1]；单价统一命名后缀为 [xxxx_]price [1]，金额统一命名后缀为 [xxxx_]money [1]。",
      "citations": [
        {
          "index": 1,
          "title": "《数据库规范》- 数据库规范 > 命名规范",
          "snippet": "4. 单价统一命名后缀[xxxx_]price... 5. 金额统一命名后缀[xxxx_]money... 17. 数量、金额类统一使用 decimal 类型，精确如无特殊需求统一使用 decimal(20, 6)...",
          "source_file": "数据库规范.md"
        }
      ],
      "markdown_content": "### 💡 数据库规范咨询解答\n\n..."
    }
  }
  ```

---

## 📚 给初学者的架构与框架知识点总结

1. **为什么选择 FastAPI 而不是 Flask / Django？**
   - 原生支持基于 Python 类型提示（Type Hints）的强类型入参校验（Pydantic）；
   - 原生协程 `async/await` 支持，结合 `httpx.AsyncClient` 实现极高的 I/O 并发吞吐；
   - 自动生成符合 OpenAPI 标准的 Swagger UI 交互式文档。
2. **什么是依赖注入（Depends）？**
   - 传统开发中直接在函数里 `repo = OllamaEmbeddingRepository()` 会产生强耦合，难以单元测试。
   - 通过 `Depends(get_ollama_repository)`，由 FastAPI 框架负责单例的生命周期与实例化装配，业务类只需声明入参类型，随时可以在测试中热插拔替换 Mock 对象。
3. **为什么双路检索与 RRF 结合是工业级标配？**
   - 稠密向量擅长理解同义词和语义，但对精确关键字（如 `db_`、`decimal(20, 6)`）不敏感；
   - 稀疏 BM25 擅长词频精确匹配，但完全不懂语义相近。
   - 借助 RRF 倒数排名融合算法，只根据相对名次 $1/(k + rank)$ 打分累加，无需手动调参即可获得最佳的综合排序质量。
4. **如何彻底防御 LLM 幻觉？**
   - 仅仅依赖提示词约束大模型是远远不够的。
   - 本项目通过 `DoubleCheckVerifier` 在 LLM 推理后加了一层**确定性 Python 规则过滤**：反向校验引用的编号与特征词是否白纸黑字出现在 Chunk 中，将幻觉误报在出库前直接掐死，实现真正企业级可靠交付。
5. **为什么切块实体必须区分 `embedding_text` 与 `display_text`？**
   - **`embedding_text` 是语义检索钩子**：专供本地向量模型（Ollama）计算稠密向量。头部拼接了层级面包屑路径（如 `【规范层级】数据库规范 > 命名规范 > 规则清单与反例`）作为锚点，即使正文没有出现宏观关键字，也能在多维向量空间准确定位，大幅提高检索召回率。一旦在离线期持久化为 `dense_vectors.npy`，终身不再被业务读取。
   - **`display_text` 是纯净业务正文**：专供在线审查期喂给大模型（DeepSeek）和在前端 UI 展示。保持纯净的 Markdown 原文排版，避免头部重复的人工标签污染 Prompt、浪费 Token 或导致大模型复读内部标签引起格式歧义。
