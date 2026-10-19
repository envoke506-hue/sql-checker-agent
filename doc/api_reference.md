# RESTful 核心接口规范与使用手册 (API Reference)

本文档提供 `sql-checker-agent` 所有对外开放的 RESTful API 接口定义、请求参数结构体、响应信封及调用示例。

---

## 一、 通用设计规范与响应信封

所有 API 均统一挂载在 `/api/v1` 前缀下，遵循统一的响应信封封装格式 `ApiResponse[T]`：

```json
{
  "code": 20000,
  "message": "操作成功描述",
  "data": { ... }
}
```

### 业务状态码 (ErrorCode)

| 状态码 | 枚举名 | 含义 |
| :--- | :--- | :--- |
| `20000` | `SUCCESS` | 请求处理成功 |
| `40001` | `BAD_REQUEST` | 业务请求参数不合法 |
| `42201` | `VALIDATION_ERROR` | FastAPI Pydantic 参数强类型校验拦截失败 |
| `40401` | `SPEC_NOT_FOUND` | 未找到数据库规范源文档 |
| `50001` | `INTERNAL_SERVER_ERROR`| 服务器内部未捕获异常 |
| `50201` | `OLLAMA_SERVICE_ERROR` | 本地 Ollama 向量模型调用失败或超时 |
| `50202` | `RELAY_MODEL_ERROR` | 云端/中转站大模型推理调用异常 |

---

## 二、 核心接口清单

### 1. SQL 规范合规审查接口
- **URL**: `POST /api/v1/sql/audits`
- **功能描述**: 对研发人员提交的 MySQL DDL 语句进行智能特征感知、双路混合检索、Prompt 编排、大模型审查、Double Check 防幻觉断言过滤及合规打分。
- **请求体 (SqlAuditRequest)**:
  ```json
  {
    "sql_text": "CREATE TABLE `order` (\n  `order_id` bigint(20) NOT NULL AUTO_INCREMENT,\n  `order_no` varchar(64) NOT NULL,\n  `total_amount` double NOT NULL COMMENT '总金额',\n  `user_id` bigint(20) NOT NULL COMMENT '用户ID',\n  PRIMARY KEY (`order_id`),\n  CONSTRAINT `fk_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';",
    "db_type": "mysql"
  }
  ```
- **成功响应 (200 OK)**:
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
          "target_object": "order",
          "description": "order 为数据库保留关键字，表名不允许使用",
          "suggested_fix": "表名改为 db_order 等非保留字命名",
          "citation_index": 5
        },
        {
          "rule_id": "rule_no_double",
          "rule_name": "禁止使用浮点数 double",
          "severity": "ERROR",
          "target_object": "total_amount",
          "description": "double 存在精度丢失风险，金额须用 decimal(20, 6) 且后缀 _money",
          "suggested_fix": "改为 total_money decimal(20, 6) NOT NULL",
          "citation_index": 5
        }
      ],
      "suggested_sql": "CREATE TABLE db_order (\n  id BIGINT UNSIGNED NOT NULL COMMENT '主键',\n  code VARCHAR(64) NOT NULL DEFAULT '' COMMENT '订单编号',\n  total_money DECIMAL(20, 6) NOT NULL DEFAULT 0.000000 COMMENT '总金额',\n  version INT NOT NULL DEFAULT 0 COMMENT '数据版本',\n  deleted TINYINT(4) NOT NULL DEFAULT 0 COMMENT '逻辑删除',\n  disabled TINYINT(4) NOT NULL DEFAULT 0 COMMENT '是否禁用',\n  create_id BIGINT NOT NULL DEFAULT 0 COMMENT '创建人标识',\n  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',\n  modify_id BIGINT NOT NULL DEFAULT 0 COMMENT '修改人标识',\n  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',\n  PRIMARY KEY (id)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';",
      "markdown_report": "### ⚠️ 不满足项与整改方案（共 2 项）\n\n**1. 表名禁止使用保留关键字** · 🔴 ERROR · 依据：[5] 《数据库规范》- 数据库规范 > 建表规范 > 建库规范\n- 不满足片段：`order`\n- 问题说明：order 为数据库保留关键字，表名不允许使用\n- 整改方案：表名改为 db_order 等非保留字命名\n\n### ✅ 修改后的 SQL\n```sql\nCREATE TABLE db_order (...);\n```\n"
    }
  }
  ```

---

### 2. 数据库设计规范智能问答接口
- **URL**: `POST /api/v1/spec/queries`
- **功能描述**: 基于规范知识库与 RAG 双路召回，回答研发人员有关表设计、字段类型、命名约定的咨询。
- **请求体 (SpecQueryRequest)**:
  ```json
  {
    "question": "规范中金额和单价字段的数据类型和命名后缀有什么强制规定？"
  }
  ```
- **成功响应 (200 OK)**:
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

### 3. 知识库索引运维管理接口
- **查询当前知识库索引状态**:
  - **URL**: `GET /api/v1/knowledge/indices/status`
  - **响应数据**:
    ```json
    {
      "code": 20000,
      "message": "索引状态获取成功",
      "data": {
        "is_indexed": true,
        "chunk_count": 6,
        "dimension": 2560,
        "doc_hash": "5babb89649467fda3c81da470aa4968ed5b7c74c25e1837770a3f21fbd94e9cd",
        "last_updated": "2026-10-19 11:06:05"
      }
    }
    ```
- **触发索引全量/增量重构**:
  - **URL**: `POST /api/v1/knowledge/indices`
  - **请求体**: `{"force": true}` (传 `false` 仅做增量哈希守卫比对)

---

### 4. 全链路依赖健康体检接口
- **URL**: `GET /api/v1/health`
- **功能描述**: 并发检测本地 Ollama Embedding 模型服务与中转站 DeepSeek 推理接口的网络连通性与时延。
- **响应示例**:
  ```json
  {
    "code": 20000,
    "message": "系统与依赖服务体检完成",
    "data": {
      "app_status": "running_healthy",
      "version": "v1.0.0",
      "services": [
        {
          "name": "Local Ollama Embedding",
          "status": "healthy",
          "latency_ms": 780.2,
          "message": "向量输出维度: 2560"
        },
        {
          "name": "Relay DeepSeek LLM",
          "status": "healthy",
          "latency_ms": 1820.5,
          "message": "API 响应正常"
        }
      ]
    }
  }
  ```
