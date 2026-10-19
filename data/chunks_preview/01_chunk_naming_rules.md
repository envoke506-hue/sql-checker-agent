# 切块详情: chunk_naming_rules

## 一、元数据 (Metadata)
- **切块 ID**: chunk_naming_rules
- **面包屑层级路径**: 数据库规范 > 命名规范 > 规则清单与反例
- **所属小节**: 命名规范
- **规则分类**: naming
- **细分类型**: naming_rule
- **ACL 访问控制**: ['all_staff']

## 二、专有名词与关键词 (Keywords - 供 BM25 稀疏检索)
[
  "lower_snake_case",
  "price",
  "money",
  "amount",
  "time",
  "biz_",
  "in_",
  "out_",
  "code",
  "amount_unit",
  "sort",
  "remark",
  "db_",
  "本表字段不加表名",
  "order_id",
  "order_code",
  "decimal(20, 6)",
  "organization",
  "administrator"
]

## 三、供大模型与前端阅读的纯净正文 (display_text)
`markdown
## 命名规范与反例约束

1. 采用 lower_snake_case 命名法
2. 在语义明确的情况下尽量简短
3. 外键关系采用 表名_字段 的命名方式
4. 单价的统一命名后缀为 [xxxx_]price，如：price, order_price
5. 金额的统一命名后缀为 [xxxx_]money，如：money, order_money，remain_money
6. 数量的统一命名后缀为 [xxxx_]amount，如：amount, order_amount，user_amount
7. 时间的统一命名后缀为 [xxxx_]time，如：update_time，receive_time，send_time
8. 业务类统一命名前缀为 biz_[xxxx]，如：biz_type，biz_id
9. 入口类统一命名前缀为 in_[xxxx]，如：in_store，in_bill
10. 出口类统一命名前缀为 out_[xxxx]，如：out_store，out_bill
11. 编号、编码相关的统一命名后缀为 [xxxx_]code，如：vehicle_code，user_code
12. 数量含单位的字符字段统一命名后缀为 [xxxx_]amount_unit，该类字段仅作展示，不参与计算，如：order_amount_unit
13. 排序的统一命名 sort
14. 备注的统一全名 remark
15. 库前缀在无特殊情况统一使用 db_
16. **若是本表自己的字段，字段前不需要加表名 如：order 表 order_code, order_name 应直接写 code, name**
17. 数量、金额类统一使用 decimal 类型，精确如无特殊需求统一使用 decimal(20, 6)，针对老系统在风险不可预知的情况下保持与原系统一致

### 反例与错误示范：
- 错误示例：organization（应为 organ），administrator（应为 admin），db_order.order.order_id（本表字段不加表名，应为 id）
`

## 四、供向量模型计算的增强文本 (embedding_text)
`	ext
【规范层级】数据库规范 > 命名规范 > 规则清单与反例
## 命名规范与反例约束

1. 采用 lower_snake_case 命名法
2. 在语义明确的情况下尽量简短
3. 外键关系采用 表名_字段 的命名方式
4. 单价的统一命名后缀为 [xxxx_]price，如：price, order_price
5. 金额的统一命名后缀为 [xxxx_]money，如：money, order_money，remain_money
6. 数量的统一命名后缀为 [xxxx_]amount，如：amount, order_amount，user_amount
7. 时间的统一命名后缀为 [xxxx_]time，如：update_time，receive_time，send_time
8. 业务类统一命名前缀为 biz_[xxxx]，如：biz_type，biz_id
9. 入口类统一命名前缀为 in_[xxxx]，如：in_store，in_bill
10. 出口类统一命名前缀为 out_[xxxx]，如：out_store，out_bill
11. 编号、编码相关的统一命名后缀为 [xxxx_]code，如：vehicle_code，user_code
12. 数量含单位的字符字段统一命名后缀为 [xxxx_]amount_unit，该类字段仅作展示，不参与计算，如：order_amount_unit
13. 排序的统一命名 sort
14. 备注的统一全名 remark
15. 库前缀在无特殊情况统一使用 db_
16. **若是本表自己的字段，字段前不需要加表名 如：order 表 order_code, order_name 应直接写 code, name**
17. 数量、金额类统一使用 decimal 类型，精确如无特殊需求统一使用 decimal(20, 6)，针对老系统在风险不可预知的情况下保持与原系统一致

### 反例与错误示范：
- 错误示例：organization（应为 organ），administrator（应为 admin），db_order.order.order_id（本表字段不加表名，应为 id）
`
