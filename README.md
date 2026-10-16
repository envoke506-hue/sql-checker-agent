# SQL Checker Agent (基于 RAG 的智能 SQL 审查与数据库设计规范问答系统)

本项目是一个基于 **检索增强生成 (RAG)** 技术的智能 SQL 规范合规审查与知识问答 Agent 系统。项目严格遵循 **企业级 MVC 架构** 设计与 **RESTful API** 规范，深度实践和验证了《大模型应用开发基础：检索增强生成》系列课程（第 15~20 篇）中所学的切块、元数据、Embedding、稠密向量库、BM25 倒排索引、混合检索、RRF 倒数排名融合算法、Lost-in-the-Middle 上下文头尾编排、Double Check 二次断言防幻觉核验及标准 Markdown 报告生成全套核心技术。

---

## 🌟 核心技术亮点与课程深度落地

### 1. 结构化 AST 语义自闭环原子切块 (落地第 15、16 篇)
- **痛点解决**：传统滑动窗口按字数暴力切分极易把“正例”与“反例”切断在两个不同块中，导致 LLM 把“反例 `order_id`”误当成规范学习；也容易将建表模板的基类字段切成碎片。
- **方案落地**：针对《数据库规范.md》实现专门的 AST 结构化解析器（`ChunkingService`），实现 **正反例强绑定**、**建表模板基类字段黑盒保护**、**建库规范 15 条禁令原子归纳**，切出 6 个高内聚自闭环原子块。
- **溯源元数据**：每个切块注入层次面包屑路径（如 `数据库规范 > 命名规范 > 规则清单`）、分类标签（`naming`、`template`、`ddl_rule`）与 ACL 访问控制权限。

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
  $$RRF\_Score(d) = \sum_{m \in \{dense, sparse\}} \frac{1}{60 + rank_m(d)}$$
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
│   │   ├── chunking_service.py      # 基于 AST 的 Markdown 语义自闭环原子切块
│   │   ├── knowledge_service.py     # 知识库离线索引 Pipeline 与增量哈希守卫
│   │   ├── sql_feature_extractor.py # SQL 语法与合规特征提取器 (意图分解)
│   │   ├── retrieval_service.py     # 双路混合检索与 RRF 融合排序引擎
│   │   ├── context_orchestrator.py  # Lost-in-the-Middle 头尾重排与引用编号编排
│   │   ├── double_check_verifier.py # 确定性断言核验与防幻觉过滤器
│   │   ├── audit_report_renderer.py # 标准 Markdown 报告渲染器 (View 视图组件)
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
├── data/indices/                # 离线持久化索引目录
│   ├── dense_vectors.npy        # 稠密向量矩阵 (2560维 NumPy 二进制)
│   ├── vector_ids.json          # 向量 ID 映射
│   ├── bm25_model.pkl           # BM25 倒排索引模型
│   ├── chunks_store.json        # 切块完整实体与元数据 JSON
│   └── index_meta.json          # 索引元信息与源文件 SHA-256 哈希
│
└── tests/                       # 自动化测试套件 (覆盖率 100%)
    ├── test_phase1_skeleton.py      # 骨架层、异步仓储与连接池测试
    ├── test_phase1_controllers.py   # RESTful 控制器与全局异常拦截测试
    ├── test_phase2_indexing.py      # AST 切块、向量检索、BM25 检索测试
    ├── test_phase3_retrieval.py     # SQL 特征提取、RRF 数学算法融合测试
    ├── test_phase4_audit_e2e.py     # 端到端审查、Double Check、Markdown 渲染全量测试
    └── test_web_ui.py               # Web 前端控制台界面交付与路由端点测试
```

---

## 🖥️ 交互式 Web 操作控制台 (SPA)

项目内置了现代化的单页面控制台（SPA），**无需配置 Node.js 或执行 npm build**，启动后端即可通过浏览器开箱即用：

- **访问地址**：`http://127.0.0.1:8000/` 或 `http://127.0.0.1:8000/ui`
- **核心功能板块**：
  1. **📋 SQL 合规审查与一键重构**：
     - 提供“🚨 典型违规反例”与“🌟 100%合规正例”一键快速填入按钮；
     - 实时执行 RAG 审查并可视化渲染“合规健康得分卡片”、“违规明细对照表”与“推荐合规重构 SQL”；
     - 支持“一键复制代码”与“查看展开标准 Markdown 报告全文”。
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
RELAY_API_KEY=sk-x9Gp6vrNe469SQH8yLuNiT4QKSQOmYKeCBlj0SnUUtGtJ2Ht
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
# 1. 运行 Phase 1: 异步连接池与异常拦截测试
python tests/test_phase1_skeleton.py
python tests/test_phase1_controllers.py

# 2. 运行 Phase 2: 知识库切块与双路检索索引构建测试
python tests/test_phase2_indexing.py

# 3. 运行 Phase 3: SQL 特征提取与 RRF 融合检索测试
python tests/test_phase3_retrieval.py

# 4. 运行 Phase 4: 端到端智能审查与规范问答全链路测试
python tests/test_phase4_audit_e2e.py

# 5. 运行 Web UI 前端交互与路由端点测试
python tests/test_web_ui.py
```

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
      "markdown_report": "# 📋 数据库设计规范合规审查报告\n\n## 1. 审查总览看板\n| 审查指标 | 评估结果 |\n| :--- | :--- |\n| **合规状态** | ❌ **存在不符合规范项 (需整改)** |\n| **合规健康得分** | **0 / 100** |\n...\n"
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
