# 切块详情: chunk_field_and_index_rules

## 一、元数据 (Metadata)
- **切块 ID**: chunk_field_and_index_rules
- **面包屑层级路径**: 数据库规范 > 建表规范 > 字段设计与索引命名
- **所属小节**: 建表规范
- **规则分类**: ddl_rule
- **细分类型**: field_and_index_rule
- **ACL 访问控制**: ['all_staff']

## 二、专有名词与关键词 (Keywords - 供 BM25 稀疏检索)
[
  "system_source",
  "data_source",
  "雪花算法",
  "idx_",
  "uniq_",
  "BTREE",
  "KEY",
  "UNIQUE KEY",
  "TINYINT(4)",
  "1个字符",
  "varchar",
  "int",
  "COMMENT",
  "utf8mb4_general_ci",
  "索引命名",
  "唯一索引",
  "布尔类型",
  "id",
  "idx_order_id",
  "order_id",
  "uniq_channel_id",
  "channel_id",
  "is_deleted",
  "is_split",
  "vehicle_number",
  "status",
  "valuation_mode",
  "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci",
  ") COMMENT='司机报名申请表';"
]

## 三、供大模型与前端阅读的纯净正文 (display_text)
`markdown
## 建表规范 (字段设计、索引命名与数据类型规则)

1. 与三方对接的表需要加上系统来源（system_source）和数据来源（data_source），系统来源区分对方系统，数据来源区分对方机构信息。
2. 主键（雪花算法）：`id` BIGINT UNSIGNED NOT NULL COMMENT '主键'
3. 普通索引：必须以 `idx_` 开头，例如：KEY `idx_order_id` (`order_id`) USING BTREE
4. 唯一索引：必须以 `uniq_` 开头，例如：UNIQUE KEY `uniq_channel_id` (`channel_id`) USING BTREE
5. 布尔类型：
   `is_deleted` 或名词属性 TINYINT(4) NOT NULL DEFAULT 0 COMMENT '是否删除，0: 否 1: 是'
   统一 4 位长度 TINYINT(4)，避免驱动自作主张。列名尽量用名词，以便 Java 框架映射为 isXxx()
6. 1 个字符：`is_split` TINYINT(4) NOT NULL DEFAULT 'N' COMMENT '是否需要按段拆单(Y或N)' (统一 4 位 TINYINT(4))
7. 大于 1 个字符：`vehicle_number` varchar(30) NOT NULL DEFAULT '' COMMENT '车牌号'
8. 1 个整数：`status` TINYINT(4) NOT NULL DEFAULT 0 COMMENT '状态，0：初始化 1：成功 2：失败'
9. 大于 1 个整数：`valuation_mode` int NOT NULL DEFAULT '1131000' COMMENT '计价方式'
10. 字段定义不要手写：`CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci`
11. 建表结尾格式：`) COMMENT='司机报名申请表';`
`

## 四、供向量模型计算的增强文本 (embedding_text)
`	ext
【规范层级】数据库规范 > 建表规范 > 字段设计与索引命名
## 建表规范 (字段设计、索引命名与数据类型规则)

1. 与三方对接的表需要加上系统来源（system_source）和数据来源（data_source），系统来源区分对方系统，数据来源区分对方机构信息。
2. 主键（雪花算法）：`id` BIGINT UNSIGNED NOT NULL COMMENT '主键'
3. 普通索引：必须以 `idx_` 开头，例如：KEY `idx_order_id` (`order_id`) USING BTREE
4. 唯一索引：必须以 `uniq_` 开头，例如：UNIQUE KEY `uniq_channel_id` (`channel_id`) USING BTREE
5. 布尔类型：
   `is_deleted` 或名词属性 TINYINT(4) NOT NULL DEFAULT 0 COMMENT '是否删除，0: 否 1: 是'
   统一 4 位长度 TINYINT(4)，避免驱动自作主张。列名尽量用名词，以便 Java 框架映射为 isXxx()
6. 1 个字符：`is_split` TINYINT(4) NOT NULL DEFAULT 'N' COMMENT '是否需要按段拆单(Y或N)' (统一 4 位 TINYINT(4))
7. 大于 1 个字符：`vehicle_number` varchar(30) NOT NULL DEFAULT '' COMMENT '车牌号'
8. 1 个整数：`status` TINYINT(4) NOT NULL DEFAULT 0 COMMENT '状态，0：初始化 1：成功 2：失败'
9. 大于 1 个整数：`valuation_mode` int NOT NULL DEFAULT '1131000' COMMENT '计价方式'
10. 字段定义不要手写：`CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci`
11. 建表结尾格式：`) COMMENT='司机报名申请表';`
`
