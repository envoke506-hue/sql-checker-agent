# 反向案例 · 建库规范

> **依据**：《数据库规范》> 建表规范 > 建库规范（第 1 ~ 15 条）
> **知识库切块**：`chunk_database_rules`
> **案例数**：16

规范原文（第 1 ~ 15 条）：

```plaintext
1、数据必须使用innodb引擎
2、生产数据库均以 db_ 开头（与测试环境不同），如 db_order、db_cargo
3、表内禁止外键设计
4、禁止触发器、存储过程、自定义函数
5、字符集为：utf8mb4
6、研发操作生产库必须经过评审后方可操作
7、表与字段不允许用关键字  或者  看着像关键字的单词
8、DDL增加字段标注AFTER
9、数字类型已知不存在负数的情况下可以加 UNSIGNED
10、尽自己的能力使用 NOT NULL 或 NOT NULL DEFAULT
11、大表不允许加字段，采用扩展表的方式实现
12、double类型不要用，直接用decimal
13、关联表以r_开
14、对于 TINYINT 类型，统一使用 TINYINT(4)
15、关于建表结尾的字符集要求，由于历史的原故，可以不填，但如果填了必须是符合规范的字符集
```

> 第 6 条（生产库操作需评审）、第 11 条（大表加字段走扩展表）属于**流程性约束**，
> 无法从 DDL 文本静态判定，故不收录为反例，仅在此备注。

---

### D-01 表名未以 `db_` 开头

- **违反条款**：建库规范 2 —— 生产数据库均以 `db_` 开头（如 `db_order`、`db_cargo`）；命名规范 15 —— 库前缀在无特殊情况统一使用 `db_`
- **命中规则**：`建库规范 · 生产库表名 db_ 前缀`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

```sql
CREATE TABLE `order_info` (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单信息表';
```

**整改要点**：`order_info` → `db_order_info`。

> ⚠️ **口径待确认**：规范第 2 条字面说的是「生产**数据库**」以 `db_` 开头，第 15 条说的是「**库前缀**」，
> 严格讲 `db_` 是库名前缀而非表名前缀；但项目内置正例 SQL 使用 `db_order_info` 这类表名。
> 本条按「表名需带 `db_` 前缀」收录，若团队确认 `db_` 只加在库名上，本条应降级为 WARN 或移除。

---

### D-02 存储引擎使用 `MyISAM`

- **违反条款**：建库规范 1 —— 数据必须使用 `innodb` 引擎；建表模板 —— 必须使用 `ENGINE=InnoDB`
- **命中规则**：`建库规范 · 必须使用 InnoDB`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

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
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：`ENGINE=MyISAM` → `ENGINE=InnoDB`（MyISAM 无事务与行锁）。

---

### D-03 表内定义外键约束

- **违反条款**：建库规范 3 —— 表内禁止外键设计（外键关系由业务应用逻辑保证）
- **命中规则**：`建库规范 · 表内禁止外键设计`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

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
  CONSTRAINT `fk_order_user` FOREIGN KEY (`user_id`) REFERENCES `db_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**：删除 `CONSTRAINT ... FOREIGN KEY`，改为普通索引 `KEY idx_user_id (user_id) USING BTREE`，关联完整性由应用层保证。

---

### D-04 外键附带级联删除

- **违反条款**：建库规范 3 —— 表内禁止外键设计
- **命中规则**：`建库规范 · 表内禁止外键设计`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

```sql
CREATE TABLE `db_order_detail` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  order_id    BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '订单标识',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id),
  CONSTRAINT `fk_detail_order` FOREIGN KEY (`order_id`) REFERENCES `db_order` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单明细表';
```

**整改要点**：删除外键与 `ON DELETE CASCADE`。级联删除在分库分表与逻辑删除场景下会造成不可控的数据丢失，必须由应用层显式控制。

---

### D-05 定义触发器

- **违反条款**：建库规范 4 —— 禁止触发器、存储过程、自定义函数
- **命中规则**：`建库规范 · 禁止触发器`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

```sql
-- 前置表（本身合规）
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

-- ❌ 反例：触发器
CREATE TRIGGER `trg_order_after_insert`
AFTER INSERT ON `db_order`
FOR EACH ROW
BEGIN
  INSERT INTO db_order_log(order_id, action) VALUES (NEW.id, 'insert');
END;
```

**整改要点**：删除触发器，改为在应用层 Service 内完成联动写入（便于测试、可控、可回滚）。

---

### D-06 定义存储过程与自定义函数

- **违反条款**：建库规范 4 —— 禁止触发器、存储过程、自定义函数
- **命中规则**：`建库规范 · 禁止存储过程/自定义函数`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

```sql
-- ❌ 反例 1：存储过程
CREATE PROCEDURE `sp_close_expired_order`()
BEGIN
  UPDATE db_order SET status = 9 WHERE expire_time < NOW();
END;

-- ❌ 反例 2：自定义函数
CREATE FUNCTION `fn_order_level`(p_money DECIMAL(20, 6))
RETURNS TINYINT(4)
DETERMINISTIC
BEGIN
  RETURN IF(p_money > 1000, 2, 1);
END;
```

**整改要点**：数据库只承载数据，业务计算下沉到应用层，避免逻辑散落在库内难以版本管理。

---

### D-07 字符集使用 `utf8` 而非 `utf8mb4`

- **违反条款**：建库规范 5 —— 字符集为 `utf8mb4`；第 15 条 —— 建表结尾填了就必须是规范字符集
- **命中规则**：`建库规范 · 字符集必须 utf8mb4`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='订单表';
```

**整改要点**：`DEFAULT CHARSET=utf8` → `DEFAULT CHARSET=utf8mb4`（MySQL 的 `utf8` 最多 3 字节，无法存储 emoji 与部分生僻字）。

---

### D-08 字符集使用 `latin1` 并在字段上重复声明字符集

- **违反条款**：建库规范 5 —— 字符集为 `utf8mb4`；建表规范 —— 字段定义不要手写 `CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci`
- **命中规则**：`建库规范 · 字符集必须 utf8mb4`、`建表规范 · 字段不手写字符集`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`、`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci
                                                            NOT NULL DEFAULT '' COMMENT '订单编号',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COMMENT='订单表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `DEFAULT CHARSET=latin1` | `DEFAULT CHARSET=utf8mb4` |
| 字段上 `CHARACTER SET ... COLLATE ...` | 直接删除，字符集在表级统一声明 |

---

### D-09 表名使用数据库关键字 `order`

- **违反条款**：建库规范 7 —— 表与字段不允许用关键字或者看着像关键字的单词（原文举例 `order`、`select`、`delete`、`desc`）
- **命中规则**：`建库规范 · 表名禁止关键字`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

-- ❌ 反例：去掉 db_ 前缀后表名本身就是关键字
CREATE TABLE `order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
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

**整改要点**：`order` → `db_order` / `db_order_info`。判断口径是**去掉 `db_` 前缀后的纯名称**是否为保留关键字。

---

### D-10 字段名使用关键字或疑似关键字

- **违反条款**：建库规范 7 —— 表与字段不允许用关键字或者看着像关键字的单词
- **命中规则**：`建库规范 · 字段名禁止关键字`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

```sql
CREATE TABLE `db_config` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  `desc`      VARCHAR(255) NOT NULL DEFAULT ''               COMMENT '描述',
  `group`     VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '分组',
  `index`     INT NOT NULL DEFAULT 0                         COMMENT '索引',
  `value`     VARCHAR(255) NOT NULL DEFAULT ''               COMMENT '配置值',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配置表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `desc` | `remark`（推荐词） |
| `group` | `biz_group` |
| `index` | `sort`（推荐词） |
| `value` | `config_value` |

---

### D-11 DDL 增加字段未标注 `AFTER`

- **违反条款**：建库规范 8 —— DDL 增加字段必须标注 `AFTER` 指定位置
- **命中规则**：`建库规范 · 加字段必须标注 AFTER`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

```sql
-- ❌ 反例：新增字段未指定位置
ALTER TABLE `db_order`
  ADD COLUMN `channel_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '渠道编码';

-- ✅ 合规写法
ALTER TABLE `db_order`
  ADD COLUMN `channel_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '渠道编码' AFTER `code`;
```

**整改要点**：新增字段必须用 `AFTER <已存在字段>` 显式指定插入位置，避免因字段顺序不同导致 `SELECT *` 与 ORM 映射错位。

---

### D-12 数字类型未加 `UNSIGNED`

- **违反条款**：建库规范 9 —— 数字类型已知不存在负数的情况下可以加 `UNSIGNED`，可使数值范围扩大一倍
- **命中规则**：`建库规范 · 数字类型加 UNSIGNED`
- **级别**：WARN（推荐性条款）
- **依据切块**：`chunk_database_rules`

```sql
CREATE TABLE `db_stock` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  goods_id    BIGINT NOT NULL DEFAULT 0                      COMMENT '商品标识（未加 UNSIGNED）',
  module      TINYINT(4) NOT NULL DEFAULT 0                  COMMENT '模块（未加 UNSIGNED）',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `goods_id BIGINT` | `goods_id BIGINT UNSIGNED` |
| `module TINYINT(4)` | `module TINYINT(4) UNSIGNED` |
| `version INT` | `version INT`（建表模板原文为 `INT NOT NULL DEFAULT 0`，与第 9 条冲突，**需团队确认**） |

> ⚠️ `version` 是最典型的冲突点：建表模板写的是 `version INT NOT NULL DEFAULT 0`（无 `UNSIGNED`），
> 建库规范第 9 条又要求非负数字加 `UNSIGNED`。本案例按模板原文保留 `INT`，不再单独报错。

---

### D-13 允许 `NULL` 且未设置默认值

- **违反条款**：建库规范 10 —— 尽自己的能力使用 `NOT NULL` 或 `NOT NULL DEFAULT`，避免 `NULL` 带来的索引与逻辑开销
- **命中规则**：`建库规范 · 避免 NULL`
- **级别**：WARN（推荐性条款）
- **依据切块**：`chunk_database_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code        VARCHAR(64) DEFAULT NULL                       COMMENT '订单编号（可空）',
  remark      VARCHAR(255) DEFAULT NULL                      COMMENT '备注（可空）',
  expire_time DATETIME DEFAULT NULL                          COMMENT '过期时间（可空）',
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
| `code VARCHAR(64) DEFAULT NULL` | `code VARCHAR(64) NOT NULL DEFAULT ''` |
| `remark VARCHAR(255) DEFAULT NULL` | `remark VARCHAR(255) NOT NULL DEFAULT ''` |
| `expire_time DATETIME DEFAULT NULL` | `expire_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`（或按业务给业务默认值） |

---

### D-14 使用 `double` 存储金额

- **违反条款**：建库规范 12 —— `double` 类型不要用，直接用 `decimal`；命名规范 17 —— 金额统一 `decimal(20, 6)`
- **命中规则**：`建库规范 · 禁用 double`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

```sql
CREATE TABLE `db_pay_record` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  pay_money   DOUBLE NOT NULL DEFAULT 0                      COMMENT '支付金额',
  fee_rate    DOUBLE NOT NULL DEFAULT 0                      COMMENT '费率',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付记录表';
```

**整改要点**：`pay_money DOUBLE` → `pay_money DECIMAL(20, 6)`；`fee_rate DOUBLE` → `fee_rate DECIMAL(20, 6)`。

---

### D-15 `TINYINT` 使用 `TINYINT(1)`

- **违反条款**：建库规范 14 —— 对于 `TINYINT` 类型，统一使用 `TINYINT(4)`，规避驱动对 `TINYINT(1)` 的特殊处理造成不同业务的语义分歧
- **命中规则**：`建库规范 · TINYINT 统一 TINYINT(4)`
- **级别**：ERROR
- **依据切块**：`chunk_database_rules`

```sql
CREATE TABLE `db_order` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  status      TINYINT(1) NOT NULL DEFAULT 0                  COMMENT '状态，0：初始化 1：成功 2：失败',
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

**整改要点**：所有 `TINYINT(1)` → `TINYINT(4)`。另外 `status` 是「3 个取值」的整数，用 `TINYINT(1)` 会直接被 JDBC 驱动映射成 `boolean`，取值 2 将丢失语义。

---

### D-16 关联表未以 `r_` 开头

- **违反条款**：建库规范 13 —— 关联表以 `r_` 开头
- **命中规则**：`建库规范 · 关联表 r_ 前缀`
- **级别**：WARN
- **依据切块**：`chunk_database_rules`

```sql
CREATE TABLE `db_user_role` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  user_id     BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '用户标识',
  role_id     BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '角色标识',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id),
  UNIQUE KEY `uniq_user_role` (`user_id`, `role_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联表';
```

**整改要点**：`db_user_role` → `r_user_role`（去掉关联语义之外的前缀，统一以 `r_` 标识多对多关联表）。

---

## 本模块合规正例

```sql
CREATE TABLE `db_order` (
  id           BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code         VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  user_id      BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '用户标识',
  status       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '状态，0：初始化 1：成功 2：失败',
  order_money  DECIMAL(20, 6) NOT NULL DEFAULT 0              COMMENT '订单金额',
  remark       VARCHAR(255) NOT NULL DEFAULT ''               COMMENT '备注',
  version      INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id    BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id    BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id),
  KEY `idx_user_id` (`user_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```
