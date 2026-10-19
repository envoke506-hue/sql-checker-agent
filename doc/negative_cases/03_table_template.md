# 反向案例 · 建表模板

> **依据**：《数据库规范》> 建表模板（实体基类必须字段）
> **知识库切块**：`chunk_table_template`、`chunk_framework_mybatis`
> **案例数**：20

规范原文要求：

1. 每一张业务表**必须包含** 7 个基础字段：`version`、`deleted`、`disabled`、`create_id`、`create_time`、`modify_id`、`modify_time`；
2. 主键**必须**为 `id BIGINT UNSIGNED NOT NULL`；
3. **必须**使用 `ENGINE=InnoDB`；
4. **必须**包含表级注释 `COMMENT='...'`。

本模块反例集中在「字段缺失」与「字段类型写错」两类，这是实际审查中漏报率最高的场景
（字段名都在、命名也合规，但类型与模板不符）。

---

### M-01 缺少 `version` 字段

- **违反条款**：建表模板 —— 必须包含 `version` 基础字段
- **命中规则**：`建表模板 · 缺少基类字段 version`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：补 `version INT NOT NULL DEFAULT 0 COMMENT '数据版本'`。

---

### M-02 缺少 `deleted` 字段

- **违反条款**：建表模板 —— 必须包含 `deleted` 基础字段
- **命中规则**：`建表模板 · 缺少基类字段 deleted`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：补 `deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0 COMMENT '删除标记 0: 未删除 1: 已删除'`。

---

### M-03 缺少 `disabled` 字段

- **违反条款**：建表模板 —— 必须包含 `disabled` 基础字段
- **命中规则**：`建表模板 · 缺少基类字段 disabled`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：补 `disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0 COMMENT '停用标记 0: 未停用 1: 已停用'`。

---

### M-04 缺少 `create_id` 字段

- **违反条款**：建表模板 —— 必须包含 `create_id` 基础字段
- **命中规则**：`建表模板 · 缺少基类字段 create_id`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：补 `create_id BIGINT UNSIGNED NOT NULL COMMENT '创建人标识'`。

---

### M-05 缺少 `create_time` 字段

- **违反条款**：建表模板 —— 必须包含 `create_time` 基础字段
- **命中规则**：`建表模板 · 缺少基类字段 create_time`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：补 `create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'`。

---

### M-06 缺少 `modify_id` 字段

- **违反条款**：建表模板 —— 必须包含 `modify_id` 基础字段
- **命中规则**：`建表模板 · 缺少基类字段 modify_id`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：补 `modify_id BIGINT UNSIGNED NOT NULL COMMENT '修改人标识'`。

---

### M-07 缺少 `modify_time` 字段

- **违反条款**：建表模板 —— 必须包含 `modify_time` 基础字段
- **命中规则**：`建表模板 · 缺少基类字段 modify_time`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：补 `modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '修改时间'`。

---

### M-08 一次缺失 4 个基类字段

- **违反条款**：建表模板 —— 必须包含全部 7 个基础字段
- **命中规则**：`建表模板 · 必须包含通用基类审计字段`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  order_money DECIMAL(20, 6) NOT NULL DEFAULT 0              COMMENT '订单金额',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：一次性补齐 `version`、`deleted`、`disabled`、`create_id`、`modify_id`。

---

### M-09 主键字段名不是 `id`

- **违反条款**：建表模板 —— 主键必须为 `id BIGINT UNSIGNED NOT NULL`
- **命中规则**：`建表模板 · 主键必须为 id`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`、`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_order` (
  order_id    BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `order_id BIGINT UNSIGNED` | `id BIGINT UNSIGNED NOT NULL` |
| `PRIMARY KEY (order_id)` | `PRIMARY KEY (id)` |

> 该反例同时命中命名规范 16「本表字段不加表名前缀」。

---

### M-10 主键类型不符合模板（`INT` / 缺少 `UNSIGNED`）

- **违反条款**：建表模板 —— 主键必须为 `id BIGINT UNSIGNED NOT NULL`
- **命中规则**：`建表模板 · 主键类型必须为 BIGINT UNSIGNED`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          INT NOT NULL                                   COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：`id INT` → `id BIGINT UNSIGNED NOT NULL`（`INT` 无法承载雪花算法 64 位 ID）。

---

### M-11 主键缺少 `NOT NULL`

- **违反条款**：建表模板 —— 主键必须为 `id BIGINT UNSIGNED NOT NULL`
- **命中规则**：`建表模板 · 主键必须 NOT NULL`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED                                COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：`id BIGINT UNSIGNED` → `id BIGINT UNSIGNED NOT NULL`。

---

### M-12 主键使用数据库自增

- **违反条款**：建表规范 —— 主键（雪花）：`id BIGINT UNSIGNED NOT NULL COMMENT '主键'`；框架主键实现要求 `IdType.ASSIGN_ID` 由 `IdWorker` 生成
- **命中规则**：`建表模板 · 主键雪花算法`
- **级别**：ERROR
- **依据切块**：`chunk_field_and_index_rules`、`chunk_framework_mybatis`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT        COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：去掉 `AUTO_INCREMENT`，由应用侧 `IdWorker.getId()` 生成，实体上标注 `@TableId(type = IdType.ASSIGN_ID)`。

---

### M-13 `create_id` / `modify_id` 类型写成了 `VARCHAR`

- **违反条款**：建表模板 —— `create_id` / `modify_id` 必须为 `BIGINT UNSIGNED NOT NULL`
- **命中规则**：`建表模板 · 基类字段类型不符 create_id/modify_id`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   VARCHAR(32) NOT NULL                           COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   VARCHAR(32) NOT NULL                           COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：`create_id VARCHAR(32)` → `create_id BIGINT UNSIGNED NOT NULL`；`modify_id` 同理。

> 这是最典型的**漏报场景**：字段名齐全、命名合规，只有类型不对，容易在「字段是否缺失」的检查里被放过。

---

### M-14 `create_time` / `modify_time` 使用 `DATE` 或 `TIMESTAMP`

- **违反条款**：建表模板 —— 两者必须为 `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`
- **命中规则**：`建表模板 · 基类字段类型不符 create_time/modify_time`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATE NOT NULL                                  COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP   COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `create_time DATE` | `create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP` |
| `modify_time TIMESTAMP` | `modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP` |

---

### M-15 `deleted` / `disabled` 使用 `TINYINT(1)`

- **违反条款**：建表模板 —— `deleted` / `disabled` 为 `TINYINT(4) UNSIGNED NOT NULL DEFAULT 0`；建库规范 14 —— TINYINT 统一 `TINYINT(4)`
- **命中规则**：`建库规范 · TINYINT 统一 TINYINT(4)`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`、`chunk_database_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(1) NOT NULL DEFAULT 0                  COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(1) NOT NULL DEFAULT 0                  COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：`TINYINT(1)` → `TINYINT(4) UNSIGNED`，规避驱动误转为布尔值。

---

### M-16 `version` 类型写成字符串

- **违反条款**：建表模板 —— `version INT NOT NULL DEFAULT 0`
- **命中规则**：`建表模板 · 基类字段类型不符 version`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     VARCHAR(20) NOT NULL DEFAULT ''                COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：`version VARCHAR(20)` → `version INT NOT NULL DEFAULT 0`（乐观锁依赖数值自增比较）。

---

### M-17 未声明 `ENGINE=InnoDB`

- **违反条款**：建表模板 —— 必须使用 `ENGINE=InnoDB`
- **命中规则**：`建表模板 · 必须使用 InnoDB 引擎`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：补上 `ENGINE=InnoDB`（依赖默认引擎不可控，测试/生产环境默认值可能不同）。

---

### M-18 缺少表级注释

- **违反条款**：建表模板 —— 必须包含表级注释 `COMMENT='...'`；建表规范 —— 建表结尾 `) COMMENT='司机报名申请表';`
- **命中规则**：`建表模板 · 必须包含表级注释`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`、`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**整改要点**：结尾补 `COMMENT='订单表'`。

---

### M-19 缺少表级 `PRIMARY KEY (id)` 声明

- **违反条款**：建表模板 —— 主键定义必须包含表级约束 `PRIMARY KEY(id)`
- **命中规则**：`建表模板 · 缺少表级主键约束`
- **级别**：ERROR
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：括号内补 `PRIMARY KEY (id)`。

> 这是**字段齐全但表级约束缺失**的场景：`id` 字段本身类型完全正确，
> 但 InnoDB 会退化为隐藏聚簇索引，主键查询与乐观锁都会失效。

---

### M-20 字段定义缺少 `COMMENT` 注释

- **违反条款**：建表模板 —— 模板中每个字段都携带 `COMMENT '...'`
- **命中规则**：`建表模板 · 字段缺少注释`
- **级别**：WARN
- **依据切块**：`chunk_table_template`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL,
  code        VARCHAR(64) NOT NULL DEFAULT '',
  order_money DECIMAL(20, 6) NOT NULL DEFAULT 0,
  version     INT NOT NULL DEFAULT 0,
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
  create_id   BIGINT UNSIGNED NOT NULL,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  modify_id   BIGINT UNSIGNED NOT NULL,
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：每个字段补齐 `COMMENT '...'`，与模板写法保持一致。

> 本条为**模板推断型**条款（规范未单列「字段必须写注释」的文字，但模板示例逐列都有注释），
> 因此级别定为 `WARN`，避免与强制条款混为一谈。

---

## 本模块合规正例

严格对齐规范模板的标准建表语句，可作为新建表的复制起点：

```sql
CREATE TABLE `db_table` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  -- ... 其它业务字段定义
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB COMMENT='这张表的功能说明';
```

MapBatis-Plus 侧的配套写法（雪花算法主键）：

```java
// import com.baomidou.mybatisplus.core.toolkit.IdWorker;
// IdWorker.getId()      返回值 long
// IdWorker.getIdStr()   返回值 String
// Long ID = IdWorker.getId(entity);

@TableId(type = IdType.ASSIGN_ID)
private Long id;
```
