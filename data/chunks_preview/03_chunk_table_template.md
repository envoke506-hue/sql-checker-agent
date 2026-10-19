# 切块详情: chunk_table_template

## 一、元数据 (Metadata)
- **切块 ID**: chunk_table_template
- **面包屑层级路径**: 数据库规范 > 建表模板 > 实体基类必须字段
- **所属小节**: 建表模板
- **规则分类**: template
- **细分类型**: sql_template
- **ACL 访问控制**: ['all_staff']

## 二、专有名词与关键词 (Keywords - 供 BM25 稀疏检索)
[
  "CREATE TABLE",
  "BIGINT UNSIGNED",
  "version",
  "deleted",
  "disabled",
  "create_id",
  "create_time",
  "modify_id",
  "modify_time",
  "PRIMARY KEY",
  "ENGINE=InnoDB",
  "DATETIME",
  "CURRENT_TIMESTAMP",
  "基类字段",
  "审计字段",
  "id BIGINT UNSIGNED NOT NULL",
  "COMMENT='...'"
]

## 三、供大模型与前端阅读的纯净正文 (display_text)
`markdown
## 建表模板 (所有业务数据表必须严格包含的基础基类字段)

```sql
CREATE TABLE db_table (
  id BIGINT UNSIGNED NOT NULL COMMENT '主键',
  -- ... 其它业务字段定义
  version INT NOT NULL DEFAULT 0 COMMENT '数据版本',
  deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0 COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0 COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id BIGINT UNSIGNED NOT NULL COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  modify_id BIGINT UNSIGNED NOT NULL COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY(id)
) ENGINE=InnoDB COMMENT='这张表的功能说明';
```
要求说明：
- 每一张业务表必须包含上述 7 个基础字段：`version`, `deleted`, `disabled`, `create_id`, `create_time`, `modify_id`, `modify_time`。
- 主键必须为 `id BIGINT UNSIGNED NOT NULL`。
- 必须使用 `ENGINE=InnoDB`。
- 必须包含表级注释 `COMMENT='...'`。
`

## 四、供向量模型计算的增强文本 (embedding_text)
`	ext
【规范层级】数据库规范 > 建表模板 > 实体基类必须字段
## 建表模板 (所有业务数据表必须严格包含的基础基类字段)

```sql
CREATE TABLE db_table (
  id BIGINT UNSIGNED NOT NULL COMMENT '主键',
  -- ... 其它业务字段定义
  version INT NOT NULL DEFAULT 0 COMMENT '数据版本',
  deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0 COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0 COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id BIGINT UNSIGNED NOT NULL COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  modify_id BIGINT UNSIGNED NOT NULL COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY(id)
) ENGINE=InnoDB COMMENT='这张表的功能说明';
```
要求说明：
- 每一张业务表必须包含上述 7 个基础字段：`version`, `deleted`, `disabled`, `create_id`, `create_time`, `modify_id`, `modify_time`。
- 主键必须为 `id BIGINT UNSIGNED NOT NULL`。
- 必须使用 `ENGINE=InnoDB`。
- 必须包含表级注释 `COMMENT='...'`。
`
