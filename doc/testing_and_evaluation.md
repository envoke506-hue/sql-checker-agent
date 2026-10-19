# 自动化测试与 76 条反例评测套件 (Testing & Benchmarks)

本文档提供 `sql-checker-agent` 的自动化测试套件执行指南、数据库规范反向案例库口径说明及子代理并发批量评测基准。

---

## 一、 自动化测试套件运行指南

项目拥有 **100% 覆盖** 的单元测试与端到端集成测试，支持一键分阶段回归验证：

```bash
# =========================================================
# 1. Docs as Code 动态 AST 切块与规范扩展性测试 (秒级完成)
# =========================================================
python tests/test_dynamic_ast_chunking.py
python tests/demo_parse_step_by_step.py

# =========================================================
# 2. 阶段 1: 异步连接池、健康体检与全局异常拦截测试
# =========================================================
python tests/test_phase1_skeleton.py
python tests/test_phase1_controllers.py

# =========================================================
# 3. 阶段 2: 知识库切块、Ollama 向量计算与 BM25 索引构建测试
# =========================================================
python tests/test_phase2_indexing.py

# =========================================================
# 4. 阶段 3: SQL 特征感知意图分解与 RRF 融合检索测试
# =========================================================
python tests/test_phase3_retrieval.py

# =========================================================
# 5. 阶段 4: 端到端智能审查、合规正反例与 Double Check 全量测试
# =========================================================
python tests/test_phase4_audit_e2e.py

# =========================================================
# 6. 离线精简 Markdown 报告渲染与解析容错测试 (无需网络与大模型)
# =========================================================
python tests/test_audit_report_renderer.py
python tests/test_sql_audit_service_offline.py

# =========================================================
# 7. 前端 Web UI 单页面路由与文档服务集成测试
# =========================================================
python tests/test_web_ui.py
```

---

## 二、 76 条数据库规范反向案例库 (`doc/negative_cases/`)

在 [doc/negative_cases/](file:///d:/WorkData/python_work_space/sql-checker-agent/doc/negative_cases/) 目录下，系统按规范业务模块沉淀了 **76 条故意违反规范的反例 DDL 语料**：

| 文件 | 案例范围 | 案例数 | 覆盖违规类型 |
| :--- | :--- | :---: | :--- |
| [01_naming.md](file:///d:/WorkData/python_work_space/sql-checker-agent/doc/negative_cases/01_naming.md) | `N-01 ~ N-16` | 16 条 | 命名大小写、金额/单价后缀、本表字段冗余前缀等 |
| [02_terminology.md](file:///d:/WorkData/python_work_space/sql-checker-agent/doc/negative_cases/02_terminology.md) | `T-01 ~ T-12` | 12 条 | 非标准名词术语违规（如用 `organization` 替代 `organ`） |
| [03_table_template.md](file:///d:/WorkData/python_work_space/sql-checker-agent/doc/negative_cases/03_table_template.md) | `M-01 ~ M-18` | 18 条 | 缺失基类审计字段、主键非雪花算法、自增主键、引擎非 InnoDB 等 |
| [04_database_rules.md](file:///d:/WorkData/python_work_space/sql-checker-agent/doc/negative_cases/04_database_rules.md) | `D-01 ~ D-16` | 16 条 | 数据库关键字表名、禁止外键约束、禁止 `double` 浮点数等 |
| [05_field_and_index.md](file:///d:/WorkData/python_work_space/sql-checker-agent/doc/negative_cases/05_field_and_index.md) | `F-01 ~ F-12` | 12 条 | 索引前缀错误（非 `idx_` 或 `uniq_`）、布尔类型非 `TINYINT(4)` 等 |

### 案例库完整性与特征提取覆盖率静态校验
```bash
python doc/negative_cases/validate_cases.py
```
- **校验基线**：76 条反例 0 结构问题；其中 23 条直接被前置 `SqlFeatureExtractor` 静态特征命中，其余 53 条依赖 RAG 检索召回与大模型深度判定。

---

## 三、 反例批量执行与检出率评测体系 (`evaluation/`)

76 条反例 + 5 条合规正例可通过 `evaluation/` 目录下的多代理分片执行引擎进行全量端到端压力与检出率评测：

```bash
# 1. 生成唯一可信案例索引
.venv\Scripts\python.exe evaluation/build_case_index.py

# 2. 分片并发执行 (支持 6 路子代理并行加速)
.venv\Scripts\python.exe evaluation/run_shard.py --shard 1/6

# 3. 聚合结果并生成评测分析报告
.venv\Scripts\python.exe evaluation/merge_results.py
```

### 评测基线结论摘要
- **执行指标**：81/81 案例成功执行，0 缺失、0 失败；单案例均值 33.1s，6 路并行墙钟约 9 分钟；
- **命中率**：反例最终判定命中 **68/76 (89.5%)**，人工复核后目标规则识别率 **74/76 (97.4%)**，「依据切块」引用召回 **76/76 (100%)**；
- **防幻觉层收益**：`DoubleCheckVerifier` 有效切断了模型凭空捏造的不存在编号与规则；已对真实存在的条款误杀问题进行了针对性规则放行。
