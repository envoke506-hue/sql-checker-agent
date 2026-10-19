# 反向案例 · 命名规范

> **依据**：《数据库规范》> 命名规范（第 1 ~ 17 条）
> **知识库切块**：`chunk_naming_rules`、`chunk_terminology`
> **案例数**：16

所有案例均内联「标准基线段」（见 [README](./README.md#标准基线段)），仅破坏目标规则。

---

### N-01 表名与字段名使用驼峰命名

- **违反条款**：命名规范 1 —— 采用 `lower_snake_case` 命名法
- **命中规则**：`命名规范 · lower_snake_case`
- **级别**：ERROR
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_OrderInfo` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  userName    VARCHAR(30) NOT NULL DEFAULT ''                COMMENT '用户姓名',
  OrderStatus TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '订单状态',
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

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `db_OrderInfo` | `db_order_info` |
| `userName` | `user_name` |
| `OrderStatus` | `order_status` |

---

### N-02 使用冗长词而非规范推荐缩写

- **违反条款**：命名规范 2 —— 在语义明确的情况下尽量简短（原文反例：`organization`、`administrator`）
- **命中规则**：`命名规范 · 语义尽量简短`
- **级别**：WARN
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_organization_info` (
  id            BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  administrator VARCHAR(30) NOT NULL DEFAULT ''                COMMENT '管理员姓名',
  organization  VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '所属机构',
  version       INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id     BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id     BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='机构信息表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `db_organization_info` | `db_organ_info` |
| `administrator` | `admin` |
| `organization` | `organ` |

---

### N-03 关联字段未采用「表名_字段」命名

- **违反条款**：命名规范 3 —— 外键关系采用 `表名_字段` 的命名方式
- **命中规则**：`命名规范 · 关联字段命名`
- **级别**：WARN
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_order_relation` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  uid         BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '用户标识',
  dept        BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '部门标识',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单关联表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `uid` | `user_id` |
| `dept` | `dept_id` |

---

### N-04 单价字段未使用 `price` 后缀

- **违反条款**：命名规范 4 —— 单价的统一命名后缀为 `[xxxx_]price`
- **命中规则**：`命名规范 · 单价后缀 price`
- **级别**：ERROR
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_goods` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  unit_amount DECIMAL(20, 6) NOT NULL DEFAULT 0              COMMENT '单价',
  sale_sum    DECIMAL(20, 6) NOT NULL DEFAULT 0              COMMENT '销售单价',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `unit_amount` | `unit_price` |
| `sale_sum` | `sale_price` |

---

### N-05 金额字段未使用 `money` 后缀

- **违反条款**：命名规范 5 —— 金额的统一命名后缀为 `[xxxx_]money`
- **命中规则**：`命名规范 · 金额后缀 money`
- **级别**：ERROR
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_pay_record` (
  id           BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  pay_sum      DECIMAL(20, 6) NOT NULL DEFAULT 0              COMMENT '支付金额',
  order_total  DECIMAL(20, 6) NOT NULL DEFAULT 0              COMMENT '订单总金额',
  version      INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id    BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id    BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付记录表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `pay_sum` | `pay_money` |
| `order_total` | `order_money` |

---

### N-06 数量字段未使用 `amount` 后缀

- **违反条款**：命名规范 6 —— 数量的统一命名后缀为 `[xxxx_]amount`
- **命中规则**：`命名规范 · 数量后缀 amount`
- **级别**：ERROR
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_stock` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  goods_count INT NOT NULL DEFAULT 0                         COMMENT '商品数量',
  stock_qty   INT NOT NULL DEFAULT 0                         COMMENT '库存数量',
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
| `goods_count` | `goods_amount` |
| `stock_qty` | `stock_amount` |

---

### N-07 时间字段未使用 `time` 后缀

- **违反条款**：命名规范 7 —— 时间的统一命名后缀为 `[xxxx_]time`
- **命中规则**：`命名规范 · 时间后缀 time`
- **级别**：ERROR
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_bill` (
  id           BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  receive_date DATE NOT NULL                                  COMMENT '收货日期',
  send_ts      DATETIME NOT NULL                              COMMENT '发货时间',
  version      INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id    BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id    BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单据表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `receive_date` | `receive_time` |
| `send_ts` | `send_time` |

---

### N-08 业务类字段未使用 `biz_` 前缀

- **违反条款**：命名规范 8 —— 业务类统一命名前缀为 `biz_[xxxx]`
- **命中规则**：`命名规范 · 业务类前缀 biz_`
- **级别**：WARN
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_config` (
  id            BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  business_type TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '业务类型',
  trade_id      BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '业务标识',
  version       INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id     BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id     BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配置表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `business_type` | `biz_type` |
| `trade_id` | `biz_id` |

---

### N-09 入口类字段未使用 `in_` 前缀

- **违反条款**：命名规范 9 —— 入口类统一命名前缀为 `in_[xxxx]`
- **命中规则**：`命名规范 · 入口类前缀 in_`
- **级别**：WARN
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_store_record` (
  id            BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  enter_store   BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '入库仓库',
  inbound_bill  BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '入库单',
  version       INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id     BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id     BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='入库记录表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `enter_store` | `in_store` |
| `inbound_bill` | `in_bill` |

---

### N-10 出口类字段未使用 `out_` 前缀

- **违反条款**：命名规范 10 —— 出口类统一命名前缀为 `out_[xxxx]`
- **命中规则**：`命名规范 · 出口类前缀 out_`
- **级别**：WARN
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_outbound_record` (
  id             BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  export_store   BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '出库仓库',
  outbound_bill  BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '出库单',
  version        INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted        TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id      BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id      BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='出库记录表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `export_store` | `out_store` |
| `outbound_bill` | `out_bill` |

---

### N-11 编号/编码字段未使用 `code` 后缀

- **违反条款**：命名规范 11 —— 编号、编码相关的统一命名后缀为 `[xxxx_]code`
- **命中规则**：`命名规范 · 编号后缀 code`
- **级别**：ERROR
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_vehicle` (
  id            BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  vehicle_no    VARCHAR(30) NOT NULL DEFAULT ''                COMMENT '车牌号',
  user_number   VARCHAR(30) NOT NULL DEFAULT ''                COMMENT '用户编号',
  version       INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id     BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id     BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='车辆表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `vehicle_no` | `vehicle_code` |
| `user_number` | `user_code` |

---

### N-12 数量含单位字段未使用 `amount_unit` 后缀

- **违反条款**：命名规范 12 —— 数量含单位的字符字段后缀为 `[xxxx_]amount_unit`（仅展示不参与计算）
- **命中规则**：`命名规范 · 单位字段后缀 amount_unit`
- **级别**：WARN
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_order_detail` (
  id                BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  order_amount_unit VARCHAR(10) NOT NULL DEFAULT ''                COMMENT '订单数量单位',
  goods_unit        VARCHAR(10) NOT NULL DEFAULT ''                COMMENT '商品数量单位',
  version           INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted           TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled          TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id         BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id         BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单明细表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `goods_unit` | `goods_amount_unit` |

> `order_amount_unit` 本身合规，作为正确写法对照保留在反例中。

---

### N-13 排序字段未统一使用 `sort`

- **违反条款**：命名规范 13 —— 排序的统一命名 `sort`
- **命中规则**：`命名规范 · 排序字段命名`
- **级别**：ERROR
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_dict_item` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  seq         INT NOT NULL DEFAULT 0                         COMMENT '序号',
  sort_no     INT NOT NULL DEFAULT 0                         COMMENT '排序号',
  sortIndex   INT NOT NULL DEFAULT 0                         COMMENT '排序索引',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='字典项表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `seq` | `sort` |
| `sort_no` | `sort` |
| `sortIndex` | `sort`（同时违反 lower_snake_case） |

---

### N-14 备注字段未统一使用 `remark`

- **违反条款**：命名规范 14 —— 备注的统一全名 `remark`
- **命中规则**：`命名规范 · 备注字段命名`
- **级别**：ERROR
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_dept` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  comment     VARCHAR(255) NOT NULL DEFAULT ''               COMMENT '备注说明',
  note        VARCHAR(255) NOT NULL DEFAULT ''               COMMENT '注意事项',
  memo        VARCHAR(255) NOT NULL DEFAULT ''               COMMENT '备忘',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='部门表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `comment` | `remark`（同时 `comment` 属于疑似关键字） |
| `note` | `remark` |
| `memo` | `remark` |

---

### N-15 本表字段加了表名前缀

- **违反条款**：命名规范 16 —— 若是本表自己的字段，字段前不需要加表名（原文反例：`db_order.order.order_id` 应直接写 `id`）
- **命中规则**：`命名规范 · 本表字段不加表名前缀`
- **级别**：ERROR
- **依据切块**：`chunk_naming_rules`

```sql
CREATE TABLE `db_order` (
  id           BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  order_id     BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '订单标识（冗余前缀）',
  order_code   VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号（冗余前缀）',
  order_name   VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单名称（冗余前缀）',
  version      INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id    BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id    BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `order_id` | `id` |
| `order_code` | `code` |
| `order_name` | `name` |

> 注意区分：**外键关联到别的表**时仍应写 `表名_字段`（如 `user_id`），禁止的只是「本表自己的字段」加本表名。

---

### N-16 数量金额使用 double / 低精度 decimal

- **违反条款**：命名规范 17 —— 数量、金额类统一使用 `decimal`，无特殊需求统一 `decimal(20, 6)`；建库规范 12 —— `double` 类型不要用
- **命中规则**：`命名规范 · 金额数量精度`、`建库规范 · 禁用 double`
- **级别**：ERROR
- **依据切块**：`chunk_naming_rules`、`chunk_database_rules`

```sql
CREATE TABLE `db_order` (
  id           BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  order_money  DOUBLE NOT NULL DEFAULT 0                      COMMENT '订单金额（double 精度丢失）',
  goods_amount DECIMAL(10, 2) NOT NULL DEFAULT 0              COMMENT '商品数量（精度不足）',
  unit_price   FLOAT NOT NULL DEFAULT 0                       COMMENT '单价（浮点精度丢失）',
  version      INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id    BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id    BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `order_money DOUBLE` | `order_money DECIMAL(20, 6)` |
| `goods_amount DECIMAL(10, 2)` | `goods_amount DECIMAL(20, 6)` |
| `unit_price FLOAT` | `unit_price DECIMAL(20, 6)` |

---

## 本模块合规正例

```sql
CREATE TABLE `db_order` (
  id           BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  code         VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单编号',
  name         VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '订单名称',
  user_id      BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '用户标识',
  biz_type     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '业务类型',
  order_money  DECIMAL(20, 6) NOT NULL DEFAULT 0              COMMENT '订单金额',
  order_amount_unit VARCHAR(10) NOT NULL DEFAULT ''           COMMENT '订单数量单位',
  receive_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '收货时间',
  sort         INT NOT NULL DEFAULT 0                         COMMENT '排序',
  remark       VARCHAR(255) NOT NULL DEFAULT ''               COMMENT '备注',
  version      INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id    BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id    BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```
