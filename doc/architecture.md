# 系统架构与核心 RAG 技术深度解析 (Architecture & Core RAG)

本文档深入解析 `sql-checker-agent` 的企业级 MVC 架构设计、全链路数据流转机制以及 5 大高阶 RAG 核心技术实现。

---

## 一、 系统全景架构与 MVC 分层

本项目严格遵循 **企业级 MVC 分层架构** 与 **依赖倒置 (IoC) / 依赖注入 (DI)** 模式设计：

```mermaid
flowchart TD
    subgraph Client["前端与调用方 (View / Caller)"]
        UI["Web SPA 交互控制台 (/ui)"]
        API_Client["研发平台 / CI-CD 流水线"]
    end

    subgraph Controller_Layer["Controller 控制器层 (app/controllers)"]
        AuditCtrl["SqlAuditController<br/>POST /api/v1/sql/audits"]
        SpecCtrl["SpecQueryController<br/>POST /api/v1/spec/queries"]
        KnowCtrl["KnowledgeController<br/>POST /api/v1/knowledge/indices"]
        HealthCtrl["HealthController<br/>GET /api/v1/health"]
    end

    subgraph Service_Layer["Service 业务编排层 (app/services)"]
        Extractor["SqlFeatureExtractor<br/>(SQL 静态特征提取与意图分解)"]
        RetrievalSvc["RetrievalService<br/>(双路混合检索与 RRF 融合排序)"]
        Orchestrator["ContextOrchestrator<br/>(Lost-in-the-Middle 头尾重排与动态编号)"]
        Verifier["DoubleCheckVerifier<br/>(规则反向交叉断言与防幻觉重算)"]
        Renderer["AuditReportRenderer<br/>(精简 Markdown 整改回复渲染)"]
        ASTParser["MarkdownASTParser<br/>(通用 Markdown AST & Frontmatter 解析器)"]
        ChunkSvc["ChunkingService<br/>(知识切块调度服务)"]
    end

    subgraph Repository_Layer["Repository 持久与外部模型交互层 (app/repositories)"]
        DenseRepo["VectorStoreRepository<br/>(NumPy 矩阵 + 余弦相似度计算)"]
        BM25Repo["Bm25IndexRepository<br/>(定制分词 BM25 稀疏检索仓储)"]
        DocRepo["DocStoreRepository<br/>(完整切块实体正文持久化仓储)"]
        OllamaRepo["OllamaEmbeddingRepository<br/>(本地 Ollama qwen3-embedding:4b)"]
        LLMRepo["RelayLlmRepository<br/>(DeepSeek-Flash 推理客户端)"]
    end

    UI --> AuditCtrl & SpecCtrl & KnowCtrl
    API_Client --> AuditCtrl & SpecCtrl & KnowCtrl
    AuditCtrl --> Extractor
    Extractor -->|生成高靶向 Queries| RetrievalSvc
    RetrievalSvc --> DenseRepo & BM25Repo
    DenseRepo --> OllamaRepo
    RetrievalSvc -->|RRF 融合候选切块| Orchestrator
    Orchestrator -->|构建提示词 & [n] 引用编号| LLMRepo
    LLMRepo -->|返回 JSON 审查初稿| Verifier
    Verifier -->|断言过滤假阳性 & 重算得分| Renderer
    Renderer --> AuditCtrl
    KnowCtrl --> ChunkSvc
    ChunkSvc --> ASTParser
```

---

## 二、 五大核心 RAG 机制深度解析

### 1. Docs as Code 规范治理与通用 Markdown AST 动态切块
- **痛点解决**：
  1. 传统按固定字数切块易把“正例”与“反例”切散在两个 Chunk，使大模型把“反例 `order_id`”误当正例；也容易把建表模板中的基类字段切断；
  2. 传统切块在代码中硬编码千行静态常量，源文件变动无法动态联动。
- **方案落地**：
  - **源文档 Frontmatter 治理**：《数据库规范.md》采用 Docs as Code 范式，头部注入声明式 YAML Frontmatter，声明 `chunk_id`、`heading_path`、`category` 及专有词表；
  - **通用 `MarkdownASTParser`**：0 业务硬编码，基于标准 AST 边界切分，自适应提取反引号代码词动态扩充 BM25 词表，支持普通 Markdown H2 优雅降级；
  - **动态增量闭环**：`ChunkingService` 0 硬编码，源文件一旦修改，SHA-256 自动感知并触发双路增量重建。

### 2. 双轨文本职责分离 (Dual Representation)
- **`embedding_text` (语义检索钩子)**：
  - 专供本地向量模型（Ollama）计算稠密向量；
  - 头部拼接了层级面包屑路径（如 `【规范层级】数据库规范 > 命名规范 > 规则清单与反例`）作为锚点，即使正文中没有出现宏观关键字，也能在多维向量空间准确定位，大幅提高检索召回率；
  - 一旦在离线期持久化为 `dense_vectors.npy`，终身不再被业务读取。
- **`display_text` (纯净业务正文)**：
  - 专供在线审查期喂给大模型（DeepSeek）和在前端 UI 展示；
  - 保持纯净的 Markdown 原文排版，避免头部重复的人工标签污染 Prompt、浪费 Token 或导致大模型复读内部标签引起格式歧义。

### 3. 双路离线索引构建与增量哈希校验 Pipeline
- **稠密向量路 (Dense)**：调用本地 Ollama `qwen3-embedding:4b` 生成 2560 维高精向量，使用 NumPy 进行矩阵余弦相似度加速，持久化为 `dense_vectors.npy`；
- **稀疏倒排路 (Sparse BM25)**：定制中英与 SQL 符号分词器，保留 `decimal(20, 6)`、`TINYINT(4)`、`db_`、下划线及 2-gram 中文词，持久化为 `bm25_model.pkl`；
- **增量哈希守卫**：启动或更新时自动比对源规范 Markdown 的 SHA-256 哈希值，未修改时 **0 毫秒秒级加载**，发生修改自动重建。

### 4. SQL 特征感知与双路混合检索 RRF 融合排序
- **痛点解决**：原始 DDL 包含大量通用语法关键字与括号，若直接 Embedding 整段 SQL，关键违规特征（如 `double` 或 `order_id`）会被严重稀释。
- **高靶向性意图分解 (`SqlFeatureExtractor`)**：前置解析 SQL 提取表名、保留字、外键、浮点数、本表冗余前缀反例、缺失基类字段，自动生成 5~7 个高靶向性规范查询。
- **RRF (Reciprocal Rank Fusion) 倒数排名融合算法**：
  $$RRF\_Score(d) = \sum_{m \in \{dense, sparse\}} \frac{1}{60 + rank_m(d)}$$
  抹平 BM25 无界得分与余弦相似度的尺度差异，跨路综合累加，实现违规条款 100% 召回。

### 5. Lost-in-the-Middle 上下文头尾重排与引用编号编排
- **痛点解决**：大模型对长上下文的注意力呈“首尾高、中间低”的 U 型曲线。中间腹部的规范极易被忽略导致漏报。
- **编排算法 (`ContextOrchestrator`)**：
  - 将相关度最高的文档交替安放在两端，次相关沉淀在中间（如 `[1, 3, 5, 4, 2]`），使关键条款始终处于注意力最强的区域；
  - 动态分配 `[1]`, `[2]`, ... 全局引用角标编号，并保留内存映射供溯源。

### 6. Double Check 二次断言核验与防幻觉过滤器
- **痛点解决**：大模型常出现“过度合规幻觉”（凭空捏造不存在的规则，或引用了虚假的编号 `[99]`，或将正常字段误报违规）。
- **确定性断言引擎 (`DoubleCheckVerifier`)**：
  - **编号越界断言**：校验引用编号是否在检索上下文有效范围；
  - **正文反向交叉核验**：通过白名单特征词，反向断言该违规规则是否真正在被引用的 Chunk 原文中存在；
  - **动态评分重算**：过滤掉所有幻觉项，精准基于真实违规（ERROR 扣 20 分，WARN 扣 10 分）重算合规得分。

---

## 三、 初学者常见架构 Q&A

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
   - 详细参见本篇第二节第 2 点：`embedding_text` 是语义检索钩子，`display_text` 是纯净业务正文，两者的生命周期与消费者完全隔离。
