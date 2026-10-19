# 反向案例 · 字段设计与索引命名

> **依据**：《数据库规范》> 建表规范（字段设计、索引命名与数据类型规则）
> **知识库切块**：`chunk_field_and_index_rules`
> **案例数**：12

规范原文：

```plaintext
1. 与三方对接的表需要加上系统来源（system_source）和数据来源（data_source）
2. 主键（雪花）：`id` BIGINT UNSIGNED NOT NULL COMMENT '主键'
3. 普通索引：必须以 idx_ 开头，例如：KEY `idx_order_id` (`order_id`) USING BTREE
4. 唯一索引：必须以 uniq_ 开头，例如：UNIQUE KEY `uniq_channel_id` (`channel_id`) USING BTREE
5. 布尔类型：`delete` TINYINT(4) NOT NULL DEFAULT 0 COMMENT '是否删除，0: 否 1: 是'（列名尽量用名词）
6. 1 个字符：`is_split` char(1) NOT NULL DEFAULT 'N' COMMENT '是否需要按段拆单(Y或N)'
7. 大于 1 个字符：`vehicle_number` varchar(30) NOT NULL DEFAULT '' COMMENT '车牌号'
8. 1 个整数：`status` TINYINT(4) NOT NULL DEFAULT 0 COMMENT '状态，0：初始化 1：成功 2：失败'
9. 大于 1 个整数：`valuation_mode` int NOT NULL DEFAULT '1131000' COMMENT '计价方式'
10. 字段定义不要手写：CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci
11. 建表结尾：) COMMENT='司机报名申请表';
```

> 第 11 条（建表结尾表注释）已收录在建表模板模块 M-18，本模块不再重复。

---

### F-01 三方对接表缺少 `system_source`

- **违反条款**：建表规范 1 —— 与三方对接的表需要加上系统来源 `system_source` 和数据来源 `data_source`
- **命中规则**：`建表规范 · 三方对接表缺 system_source`
- **级别**：ERROR
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_third_order` (
  id             BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  third_order_no VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '三方订单号',
  data_source    VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '数据来源（对方机构）',
  version        INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted        TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id      BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id      BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='三方订单表';
```

**整改要点**：补 `system_source VARCHAR(64) NOT NULL DEFAULT '' COMMENT '系统来源（对方系统）'`。

---

### F-02 三方对接表缺少 `data_source`

- **违反条款**：建表规范 1 —— 与三方对接的表需要加上系统来源 `system_source` 和数据来源 `data_source`
- **命中规则**：`建表规范 · 三方对接表缺 data_source`
- **级别**：ERROR
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_third_order` (
  id             BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  third_order_no VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '三方订单号',
  system_source  VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '系统来源（对方系统）',
  version        INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted        TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id      BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id      BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='三方订单表';
```

**整改要点**：补 `data_source VARCHAR(64) NOT NULL DEFAULT '' COMMENT '数据来源（对方机构）'`。

---

### F-03 普通索引未以 `idx_` 开头

- **违反条款**：建表规范 3 —— 普通索引必须以 `idx_` 开头
- **命中规则**：`建表规范 · 普通索引 idx_ 前缀`
- **级别**：ERROR
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  user_id     BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '用户标识',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id),
  KEY `index_user_id` (`user_id`) USING BTREE,
  KEY `order_code_idx` (`code`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `KEY index_user_id` | `KEY idx_user_id` |
| `KEY order_code_idx` | `KEY idx_code`（前缀位置错误） |

---

### F-04 唯一索引未以 `uniq_` 开头

- **违反条款**：建表规范 4 —— 唯一索引必须以 `uniq_` 开头
- **命中规则**：`建表规范 · 唯一索引 uniq_ 前缀`
- **级别**：ERROR
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_channel` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '渠道编码',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id),
  UNIQUE KEY `uk_channel_code` (`code`) USING BTREE,
  UNIQUE KEY `channel_code_unique` (`code`, `version`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='渠道表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `UNIQUE KEY uk_channel_code` | `UNIQUE KEY uniq_code` |
| `UNIQUE KEY channel_code_unique` | `UNIQUE KEY uniq_code_version` |

---

### F-05 布尔字段使用 `BOOLEAN` / `BIT` 类型

- **违反条款**：建表规范 5 —— 布尔类型统一 `TINYINT(4) NOT NULL DEFAULT 0`；建库规范 14 —— `TINYINT` 统一 `TINYINT(4)`
- **命中规则**：`建表规范 · 布尔类型 TINYINT(4)`
- **级别**：ERROR
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  is_paid     BOOLEAN NOT NULL DEFAULT FALSE                 COMMENT '是否已支付',
  is_split    BIT(1) NOT NULL DEFAULT 0                      COMMENT '是否需要按段拆单',
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

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `is_paid BOOLEAN` | `paid TINYINT(4) NOT NULL DEFAULT 0` |
| `is_split BIT(1)` | `is_split CHAR(1) NOT NULL DEFAULT 'N'`（若语义是 Y/N 字符）或 `TINYINT(4)` |

> `BOOLEAN` 在 MySQL 里只是 `TINYINT(1)` 的别名，会落入驱动误转布尔的老问题。

---

### F-06 布尔字段名使用动词/否定式，而非名词

- **违反条款**：建表规范 5 —— 布尔类型列名尽量用名词，这样 Java 框架会映射为 `isDelete()`，符合预期
- **命中规则**：`建表规范 · 布尔字段名用名词`
- **级别**：WARN
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  is_delete   TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '是否删除，0: 否 1: 是',
  not_enabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '是否未启用，0: 否 1: 是',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `is_delete` | `deleted`（框架映射为 `isDeleted()`，而非 `isIsDelete()`） |
| `not_enabled` | `disabled`（避免否定式命名带来的双重否定取值） |

> ⚠️ **规范内部口径冲突**：规范原文的布尔示例写的是 `delete` + 「列名尽量用名词」，
> 而当前知识库切块（`chunk_field_and_index_rules`）里写的是 `is_deleted`。本条按**原文**（名词式）收录，
> 并以 `deleted` / `disabled` 作为整改写法——与建表模板的基类字段保持一致。**最终口径需团队确认。**

---

### F-07 1 个字符的字段未使用 `TINYINT(4)`

- **违反条款**：建表规范 6 —— 1 个字符统一使用 `TINYINT(4)`，如 `is_split TINYINT(4) NOT NULL DEFAULT 0`，不得使用 `CHAR(1)` 或 `VARCHAR(1)`
- **命中规则**：`建表规范 · 1个字符字段用 TINYINT(4)`
- **级别**：ERROR
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  is_split    VARCHAR(1) NOT NULL DEFAULT 'N'                COMMENT '是否需要按段拆单(Y或N)',
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

**整改要点**：`is_split VARCHAR(1)` → `is_split TINYINT(4)`。

---

### F-08 1 个字符的字段缺少默认值

- **违反条款**：建表规范 6 —— `is_split char(1) NOT NULL DEFAULT 'N'`
- **命中规则**：`建表规范 · 单字符字段默认值`
- **级别**：WARN
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  is_split    CHAR(1) NOT NULL                               COMMENT '是否需要按段拆单(Y或N)',
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

**整改要点**：补 `DEFAULT 'N'`。类型已合规（`CHAR(1)`），仅缺默认值。

---

### F-09 大于 1 个字符的字段使用 `TEXT` 且无默认值

- **违反条款**：建表规范 7 —— 大于 1 个字符使用 `varchar(30) NOT NULL DEFAULT ''`
- **命中规则**：`建表规范 · 大于1字符用 varchar`
- **级别**：ERROR
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_vehicle` (
  id             BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  vehicle_number TEXT NOT NULL                                  COMMENT '车牌号',
  driver_name    VARCHAR(30) NOT NULL                           COMMENT '司机姓名',
  version        INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted        TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id      BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id      BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='车辆表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `vehicle_number TEXT` | `vehicle_number VARCHAR(30) NOT NULL DEFAULT ''`（`TEXT` 不能建普通索引、不能有默认值） |
| `driver_name VARCHAR(30) NOT NULL` | 补 `DEFAULT ''` |

---

### F-10 1 个整数的字段使用 `INT` 而非 `TINYINT(4)`

- **违反条款**：建表规范 8 —— 1 个整数使用 `status TINYINT(4) NOT NULL DEFAULT 0`
- **命中规则**：`建表规范 · 单整数用 TINYINT(4)`
- **级别**：WARN
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  status      INT NOT NULL DEFAULT 0                         COMMENT '状态，0：初始化 1：成功 2：失败',
  biz_type    BIGINT NOT NULL DEFAULT 0                      COMMENT '业务类型',
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

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `status INT` | `status TINYINT(4) UNSIGNED NOT NULL DEFAULT 0`（取值仅个位数，无需 4 字节） |
| `biz_type BIGINT` | `biz_type TINYINT(4) UNSIGNED NOT NULL DEFAULT 0` |

---

### F-11 大于 1 个整数的字段用字符串存储

- **违反条款**：建表规范 9 —— 大于 1 个整数使用 `valuation_mode int NOT NULL DEFAULT '1131000'`
- **命中规则**：`建表规范 · 大于1整数用 int`
- **级别**：ERROR
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_order` (
  id              BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  valuation_mode  VARCHAR(20) NOT NULL DEFAULT ''                COMMENT '计价方式(固定值：1131000（按重量）)',
  total_amount    VARCHAR(20) NOT NULL DEFAULT ''                COMMENT '总件数',
  version         INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted         TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled        TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id       BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id       BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `valuation_mode VARCHAR(20)` | `valuation_mode INT NOT NULL DEFAULT 1131000` |
| `total_amount VARCHAR(20)` | 整数用 `INT`；若是数量则为 `total_amount INT NOT NULL DEFAULT 0` |

> 用字符串存整数会让「范围查询」退化成字符串比较（`'9' > '10'`），且索引效率大幅下降。

---

### F-12 字段定义手写 `CHARACTER SET` / `COLLATE`

- **违反条款**：建表规范 10 —— 字段定义不要手写 `CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci`
- **命中规则**：`建表规范 · 字段不手写字符集`
- **级别**：ERROR
- **依据切块**：`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci
                                                             NOT NULL DEFAULT '' COMMENT '订单编号',
  remark      VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin
                                                             NOT NULL DEFAULT '' COMMENT '备注',
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

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `code VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci` | `code VARCHAR(64)` |
| `remark VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin` | `remark VARCHAR(255)` |

> 字段级字符集/排序规则会与表级声明不一致，导致跨表 JOIN 出现隐式转换从而索引失效，必须在表级统一声明。

---

## 本模块合规正例

```sql
CREATE TABLE `db_third_order` (
  id             BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code           VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  system_source  VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '系统来源（对方系统）',
  data_source    VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '数据来源（对方机构）',
  is_split       CHAR(1) NOT NULL DEFAULT 'N'                   COMMENT '是否需要按段拆单(Y或N)',
  vehicle_number VARCHAR(30) NOT NULL DEFAULT ''                COMMENT '车牌号',
  status         TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '状态，0：初始化 1：成功 2：失败',
  valuation_mode INT NOT NULL DEFAULT 1131000                   COMMENT '计价方式(1131000=按重量)',
  version        INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted        TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id      BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id      BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id),
  KEY `idx_code` (`code`) USING BTREE,
  UNIQUE KEY `uniq_vehicle_number` (`vehicle_number`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='三方订单表';
```
