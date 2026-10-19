# 切块详情: chunk_database_rules

## 一、元数据 (Metadata)
- **切块 ID**: chunk_database_rules
- **面包屑层级路径**: 数据库规范 > 建表规范 > 建库规范
- **所属小节**: 建库规范
- **规则分类**: ddl_rule
- **细分类型**: database_rule
- **ACL 访问控制**: ['all_staff']

## 二、专有名词与关键词 (Keywords - 供 BM25 稀疏检索)
[
  "innodb",
  "外键",
  "FOREIGN KEY",
  "禁止外键",
  "触发器",
  "存储过程",
  "utf8mb4",
  "关键字",
  "AFTER",
  "UNSIGNED",
  "NOT NULL",
  "NOT NULL DEFAULT",
  "double",
  "decimal",
  "r_",
  "TINYINT(4)",
  "TINYINT(1)"
]

## 三、供大模型与前端阅读的纯净正文 (display_text)
`markdown
## 建库规范 (详见 MySQL 规范)

1. 数据必须使用 innodb 引擎
2. **表内禁止外键设计** (严禁 FOREIGN KEY，外键关系由业务应用逻辑保证)
3. 禁止触发器、存储过程、自定义函数
4. 字符集统一为：utf8mb4
5. 研发操作生产库必须经过评审后方可操作
6. 表与字段不允许用数据库保留关键字或者看着像关键字的单词 (如 order, select, delete, desc 等)
7. DDL 增加字段必须标注 AFTER 指定位置
8. 数字类型已知不存在负数的情况下可以加 UNSIGNED (推荐性建议，非强制要求)
9. 尽量使用 NOT NULL 或 NOT NULL DEFAULT，避免 NULL 带来的索引与逻辑开销
10. 大表不允许随意加字段，采用扩展表的方式实现
11. **double 类型不要用，必须直接用 decimal**
12. 关联表以 r_ 开头
13. 对于 TINYINT 类型，统一使用 TINYINT(4)，规避驱动对 TINYINT(1) 误转为布尔造成的业务语义分歧
14. 关于建表结尾的字符集要求，由于历史缘故可以不填，但如果填了必须是符合规范的字符集 (utf8mb4)
`

## 四、供向量模型计算的增强文本 (embedding_text)
`	ext
【规范层级】数据库规范 > 建表规范 > 建库规范
## 建库规范 (详见 MySQL 规范)

1. 数据必须使用 innodb 引擎
2. **表内禁止外键设计** (严禁 FOREIGN KEY，外键关系由业务应用逻辑保证)
3. 禁止触发器、存储过程、自定义函数
4. 字符集统一为：utf8mb4
5. 研发操作生产库必须经过评审后方可操作
6. 表与字段不允许用数据库保留关键字或者看着像关键字的单词 (如 order, select, delete, desc 等)
7. DDL 增加字段必须标注 AFTER 指定位置
8. 数字类型已知不存在负数的情况下可以加 UNSIGNED (推荐性建议，非强制要求)
9. 尽量使用 NOT NULL 或 NOT NULL DEFAULT，避免 NULL 带来的索引与逻辑开销
10. 大表不允许随意加字段，采用扩展表的方式实现
11. **double 类型不要用，必须直接用 decimal**
12. 关联表以 r_ 开头
13. 对于 TINYINT 类型，统一使用 TINYINT(4)，规避驱动对 TINYINT(1) 误转为布尔造成的业务语义分歧
14. 关于建表结尾的字符集要求，由于历史缘故可以不填，但如果填了必须是符合规范的字符集 (utf8mb4)
`
