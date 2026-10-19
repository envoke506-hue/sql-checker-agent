# 反向案例 · 名词术语

> **依据**：《数据库规范》> 名词术语（标准命名单词字典）
> **知识库切块**：`chunk_terminology`、`chunk_naming_rules`
> **案例数**：12

规范要求「作为数据设计的首选单词或组合单词来使用」。本模块的反例全部使用**同义但非推荐**的英文单词，
命名风格与数据类型本身合法，仅「选词」违反规范。

---

### T-01 主键未使用推荐词 `id`

- **违反条款**：名词术语 > 常用单词 —— 主键：`id`；建表规范 —— 主键（雪花）：`id BIGINT UNSIGNED NOT NULL`
- **命中规则**：`名词术语 · 主键命名`
- **级别**：ERROR
- **依据切块**：`chunk_terminology`

```sql
CREATE TABLE `db_order` (
  pk_id       BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  sid         BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '业务主键（同义替代表述）',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (pk_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `pk_id` | `id` |
| `sid` | 业务主键改用 `code` 等规范后缀，不要另起主键别名 |

---

### T-02 名称未使用推荐词 `name`

- **违反条款**：名词术语 > 常用单词 —— 名称：`name`
- **命中规则**：`名词术语 · 名称命名`
- **级别**：WARN
- **依据切块**：`chunk_terminology`

```sql
CREATE TABLE `db_goods` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  title       VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '商品名称',
  goods_title VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '商品标题',
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
| `title` | `name` |
| `goods_title` | `name`（本表字段不加表名） |

---

### T-03 类型未使用推荐词 `type`

- **违反条款**：名词术语 > 常用单词 —— 类型：`type`
- **命中规则**：`名词术语 · 类型命名`
- **级别**：WARN
- **依据切块**：`chunk_terminology`

```sql
CREATE TABLE `db_config` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  category    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '分类',
  kind        TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '种类',
  class       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '类别',
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
| `category` | `biz_type` 或 `type` |
| `kind` | `biz_type` 或 `type` |
| `class` | `biz_type` 或 `type` |

> 业务类字段还须同时满足命名规范 8 的 `biz_` 前缀要求，参见 N-08。

---

### T-04 上级未使用推荐词 `parent`

- **违反条款**：名词术语 > 常用单词 —— 上级：`parent`
- **命中规则**：`名词术语 · 上级命名`
- **级别**：WARN
- **依据切块**：`chunk_terminology`

```sql
CREATE TABLE `db_dept` (
  id           BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  superior_id  BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '上级部门',
  parentCode   VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '父级编码',
  version      INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id    BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id    BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='部门表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `superior_id` | `parent_id` |
| `parentCode` | `parent_code`（推荐词 `parent` + 规范后缀 `code`） |

---

### T-05 状态未使用推荐词 `status`

- **违反条款**：名词术语 > 常用单词 —— 状态：`status`；1 个整数：`status TINYINT(4) NOT NULL DEFAULT 0`
- **命中规则**：`名词术语 · 状态命名`
- **级别**：WARN
- **依据切块**：`chunk_terminology`、`chunk_field_and_index_rules`

```sql
CREATE TABLE `db_bill` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  state       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '状态',
  stat        TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '单据状态',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单据表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `state` | `status` |
| `stat` | `status` |

---

### T-06 审核与标识未使用推荐词 `audit` / `tag`

- **违反条款**：名词术语 > 常用单词 —— 审核：`audit`，标识：`tag`
- **命中规则**：`名词术语 · 审核/标识命名`
- **级别**：WARN
- **依据切块**：`chunk_terminology`

```sql
CREATE TABLE `db_apply` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  review      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '审核状态',
  check_flag  TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '审核标记',
  mark_no     VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '标识编码',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='申请单表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `review` | `audit` |
| `check_flag` | `audit`（同时 `flag` 非推荐词，且布尔字段名应尽量用名词） |
| `mark_no` | `tag`（推荐词 `tag`，若为编码则用 `tag_code`） |

---

### T-07 链接与来源未使用推荐词 `url` / `source`

- **违反条款**：名词术语 > 常用单词 —— 链接：`url`，来源：`source`
- **命中规则**：`名词术语 · 链接/来源命名`
- **级别**：WARN
- **依据切块**：`chunk_terminology`

```sql
CREATE TABLE `db_file` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  link        VARCHAR(512) NOT NULL DEFAULT ''               COMMENT '文件链接',
  href        VARCHAR(512) NOT NULL DEFAULT ''               COMMENT '下载地址',
  origin      VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '数据来源',
  src         VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '文件来源',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `link` | `url` |
| `href` | `url` |
| `origin` | `source` |
| `src` | `source` |

---

### T-08 版本未使用推荐词 `version`

- **违反条款**：名词术语 > 数据相关 —— 版本：`version`；建表模板 —— `version INT NOT NULL DEFAULT 0`
- **命中规则**：`名词术语 · 版本命名`
- **级别**：ERROR
- **依据切块**：`chunk_terminology`、`chunk_table_template`

```sql
CREATE TABLE `db_contract` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  ver         INT NOT NULL DEFAULT 0                         COMMENT '版本',
  revision    INT NOT NULL DEFAULT 0                         COMMENT '修订版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合同表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `ver` | `version` |
| `revision` | `version` |
| 缺少 `version` 字段 | 必须补齐模板要求的 `version INT NOT NULL DEFAULT 0` |

---

### T-09 删除与禁用标记未使用推荐词 `deleted` / `disabled`

- **违反条款**：名词术语 > 数据相关 —— 删除：`deleted`，禁用：`disabled`；建表模板 —— 两者为必备基类字段
- **命中规则**：`名词术语 · 删除/禁用命名`
- **级别**：ERROR
- **依据切块**：`chunk_terminology`、`chunk_table_template`

```sql
CREATE TABLE `db_notice` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  del_flag    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记',
  is_delete   TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '是否删除',
  enable_flag TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '启用标记',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='公告表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `del_flag` | `deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0` |
| `is_delete` | `deleted`（消除 `isXxx` 动词式命名） |
| `enable_flag` | `disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0`（语义相反需一并调整取值口径） |

---

### T-10 关联与路径未使用推荐词 `relation` / `path`

- **违反条款**：名词术语 > 数据相关 —— 关联：`relation`，路径：`path`
- **命中规则**：`名词术语 · 关联/路径命名`
- **级别**：WARN
- **依据切块**：`chunk_terminology`

```sql
CREATE TABLE `db_menu` (
  id             BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  rel_id         BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '关联标识',
  relation_code  VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '关联编码',
  file_url_path  VARCHAR(512) NOT NULL DEFAULT ''               COMMENT '文件路径',
  version        INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted        TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id      BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id      BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='菜单表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `rel_id` | `relation_id` |
| `relation_code` | `relation_id` 或 `relation_code`（推荐词 `relation` 保留） |
| `file_url_path` | `path`（路径与链接是两种语义，不要用下划线堆叠表达） |

---

### T-11 用户相关字段未使用推荐词

- **违反条款**：名词术语 > 用户相关 —— 账号 `username`、密码 `password`、姓名 `name`、昵称 `nick`、邮箱 `email`、性别 `gender`、生日 `birthday`、角色 `role`、职位 `duty`
- **命中规则**：`名词术语 · 用户字段命名`
- **级别**：WARN
- **依据切块**：`chunk_terminology`

```sql
CREATE TABLE `db_user` (
  id           BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  account      VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '登录账号',
  pwd          VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '登录密码',
  nick_name    VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '昵称',
  mail         VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '邮箱',
  sex          TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '性别',
  birth_date   DATE NOT NULL                                  COMMENT '生日',
  role_no      VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '角色',
  position     VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '职位',
  version      INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id    BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id    BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `account` | `username` |
| `pwd` | `password` |
| `nick_name` | `nick`（推荐词本身即 `nick`） |
| `mail` | `email` |
| `sex` | `gender` |
| `birth_date` | `birthday` |
| `role_no` | `role` |
| `position` | `duty` |

---

### T-12 业务与地址相关字段未使用推荐词

- **违反条款**：名词术语 > 业务相关（部门 `dept`、机构 `organ`、公司 `company`、品项/物料/商品/货物 `goods`）；地址相关（地址 `address`、邮政编码 `zip`、座机 `phone`、联系人 `contact`）
- **命中规则**：`名词术语 · 业务/地址字段命名`
- **级别**：WARN
- **依据切块**：`chunk_terminology`

```sql
CREATE TABLE `db_receiver` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  department  BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '部门',
  organization BIGINT UNSIGNED NOT NULL DEFAULT 0            COMMENT '机构',
  corp        BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '公司',
  product_id  BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '商品',
  addr        VARCHAR(255) NOT NULL DEFAULT ''               COMMENT '收货地址',
  postcode    VARCHAR(10) NOT NULL DEFAULT ''                COMMENT '邮政编码',
  tel         VARCHAR(20) NOT NULL DEFAULT ''                COMMENT '座机',
  contactor   VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '联系人',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收货人表';
```

**整改要点**

| 违规片段 | 合规写法 |
| --- | --- |
| `department` | `dept` |
| `organization` | `organ` |
| `corp` | `company` |
| `product_id` | `goods_id` |
| `addr` | `address` |
| `postcode` | `zip` |
| `tel` | `phone` |
| `contactor` | `contact` |

---

## 本模块合规正例

规范推荐词的完整取用示例，可直接作为字段取名速查表：

```sql
CREATE TABLE `db_user` (
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  username    VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '账号',
  password    VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '密码',
  name        VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '姓名',
  nick        VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '昵称',
  email       VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '邮箱',
  gender      TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '性别',
  birthday    DATE NOT NULL                                  COMMENT '生日',
  role        VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '角色',
  duty        VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '职位',
  dept_id     BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '部门',
  company_id  BIGINT UNSIGNED NOT NULL DEFAULT 0             COMMENT '公司',
  mobile      VARCHAR(20) NOT NULL DEFAULT ''                COMMENT '手机',
  phone       VARCHAR(20) NOT NULL DEFAULT ''                COMMENT '座机',
  address     VARCHAR(255) NOT NULL DEFAULT ''               COMMENT '地址',
  zip         VARCHAR(10) NOT NULL DEFAULT ''                COMMENT '邮政编码',
  contact     VARCHAR(32) NOT NULL DEFAULT ''                COMMENT '联系人',
  url         VARCHAR(512) NOT NULL DEFAULT ''               COMMENT '链接',
  source      VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '来源',
  path        VARCHAR(512) NOT NULL DEFAULT ''               COMMENT '路径',
  tag         VARCHAR(64) NOT NULL DEFAULT ''                COMMENT '标识',
  remark      VARCHAR(255) NOT NULL DEFAULT ''               COMMENT '备注',
  sort        INT NOT NULL DEFAULT 0                         COMMENT '排序',
  audit       TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '审核',
  expire      DATETIME NOT NULL                              COMMENT '过期时间',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
```
