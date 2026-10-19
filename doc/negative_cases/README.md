# 数据库规范 · 反向案例库 (Negative Cases)

本目录收录**故意违反《数据库规范》的建表 DDL 反例**，按规范章节分模块组织，用于：

1. 人工培训与自查对照（写 DDL 前先看反例）；
2. 作为 SQL 审查系统的回归测试输入（每条反例的「命中规则」即期望输出）；
3. 作为评测集语料，直接 POST 给 `POST /api/v1/sql/audits` 验证检出率与误报率。

## 目录结构

| 文件 | 对应规范章节 | 案例数 |
| --- | --- | --- |
| [01_naming.md](./01_naming.md) | 命名规范（1~17 条） | 16 |
| [02_terminology.md](./02_terminology.md) | 名词术语（标准命名单词字典） | 12 |
| [03_table_template.md](./03_table_template.md) | 建表模板（实体基类必须字段） | 20 |
| [04_database_rules.md](./04_database_rules.md) | 建表规范 > 建库规范（1~15 条） | 16 |
| [05_field_and_index.md](./05_field_and_index.md) | 建表规范 > 字段设计与索引命名 | 12 |

案例编号前缀与模块一一对应：`N-` 命名、`T-` 术语、`M-` 模板、`D-` 建库、`F-` 字段与索引。
**合计 76 条反例**，覆盖规范全部可静态判定的条款。

## 案例字段说明

每条案例包含以下信息：

| 字段 | 含义 |
| --- | --- |
| **违反条款** | 规范原文的条款出处与文字，便于溯源 |
| **命中规则** | 期望审查系统报出的 `rule_name` |
| **级别** | `ERROR` = 强制阻断、`WARN` = 建议优化 |
| **依据切块** | 对应 RAG 知识库中的 chunk_id，用于校验检索召回 |
| **反例** | 可直接提交给审查接口的**完整 DDL** |
| **整改要点** | `违规片段` → `合规写法` |

## 标准基线段

为了让每条案例**只破坏一个目标规则**，除目标规则外的其它字段一律使用下列合规写法（建表模板要求）。
各案例的 DDL 都已经内联了这一段，可直接复制执行；这里单独列出便于对照。

```sql
  id          BIGINT UNSIGNED NOT NULL                       COMMENT '主键',
  version     INT NOT NULL DEFAULT 0                         COMMENT '数据版本',
  deleted     TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled    TINYINT(4) UNSIGNED NOT NULL DEFAULT 0         COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id   BIGINT UNSIGNED NOT NULL                       COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
  modify_id   BIGINT UNSIGNED NOT NULL                       COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP    COMMENT '修改时间',
  PRIMARY KEY (id)
```

## 知识库切块对照

| chunk_id | 章节路径 |
| --- | --- |
| `chunk_naming_rules` | 数据库规范 > 命名规范 > 规则清单与反例 |
| `chunk_terminology` | 数据库规范 > 名词术语 > 标准命名单词字典 |
| `chunk_table_template` | 数据库规范 > 建表模板 > 实体基类必须字段 |
| `chunk_database_rules` | 数据库规范 > 建表规范 > 建库规范 |
| `chunk_field_and_index_rules` | 数据库规范 > 建表规范 > 字段设计与索引命名 |
| `chunk_framework_mybatis` | 数据库规范 > 建表规范 > 框架主键实现与依赖 |

## 规范条款覆盖矩阵

| 规范条款 | 案例 |
| --- | --- |
| 命名规范 1 lower_snake_case | N-01 |
| 命名规范 2 语义明确尽量简短 | N-02 |
| 命名规范 3 外键关系 表名_字段 | N-03 |
| 命名规范 4 单价后缀 price | N-04 |
| 命名规范 5 金额后缀 money | N-05 |
| 命名规范 6 数量后缀 amount | N-06 |
| 命名规范 7 时间后缀 time | N-07 |
| 命名规范 8 业务类前缀 biz_ | N-08 |
| 命名规范 9 入口类前缀 in_ | N-09 |
| 命名规范 10 出口类前缀 out_ | N-10 |
| 命名规范 11 编号编码后缀 code | N-11 |
| 命名规范 12 单位字段后缀 amount_unit | N-12 |
| 命名规范 13 排序统一 sort | N-13 |
| 命名规范 14 备注统一 remark | N-14 |
| 命名规范 15 库前缀统一 db_ | D-01 |
| 命名规范 16 本表字段不加表名 | N-15 |
| 命名规范 17 数量金额 decimal(20, 6) | N-16 |
| 名词术语 常用单词（id/name/type/parent/status/audit/tag/url/source） | T-01 ~ T-07 |
| 名词术语 数据相关（version/deleted/disabled/relation/path） | T-08 ~ T-10 |
| 名词术语 用户相关 | T-11 |
| 名词术语 业务与地址相关 | T-12 |
| 建表模板 7 大基类字段缺失 | M-01 ~ M-08 |
| 建表模板 主键定义（名称/类型/NOT NULL/雪花算法/表级约束） | M-09 ~ M-12、M-19 |
| 建表模板 基类字段类型不符 | M-13、M-14、M-16 |
| 建表模板 TINYINT(1) | M-15（另见 D-15、F-05） |
| 建表模板 ENGINE / 表注释 | M-17、M-18 |
| 建表模板 字段注释（模板推断条款） | M-20 |
| 建库规范 1 必须 innodb | D-02 |
| 建库规范 2 生产库 db_ 前缀 | D-01 |
| 建库规范 3 禁止外键（含级联删除） | D-03、D-04 |
| 建库规范 4 禁止触发器/存储过程/函数 | D-05、D-06 |
| 建库规范 5/15 字符集 utf8mb4 | D-07、D-08 |
| 建库规范 7 禁止关键字 | D-09、D-10 |
| 建库规范 8 DDL 加字段标 AFTER | D-11 |
| 建库规范 9 数字加 UNSIGNED | D-12 |
| 建库规范 10 尽量 NOT NULL DEFAULT | D-13 |
| 建库规范 12 禁用 double | D-14（另见 N-16） |
| 建库规范 13 关联表 r_ 前缀 | D-16 |
| 建库规范 14 TINYINT 统一 TINYINT(4) | D-15、F-05、M-15 |
| 建库规范 6/11 评审流程与大表扩展 | 无（流程性约束，DDL 无法静态判定） |
| 建表规范 1 三方对接表 system_source/data_source | F-01、F-02 |
| 建表规范 普通索引 idx_ / 唯一索引 uniq_ | F-03、F-04 |
| 建表规范 5 布尔类型（类型 + 命名） | F-05、F-06 |
| 建表规范 6 1 个字符 char(1)（类型 + 默认值） | F-07、F-08 |
| 建表规范 7 大于 1 个字符 varchar | F-09 |
| 建表规范 8 1 个整数 TINYINT(4) | F-10 |
| 建表规范 9 大于 1 个整数 int | F-11 |
| 建表规范 10 字段不手写 CHARACTER SET | F-12 |
| 建表规范 11 建表结尾表注释 | M-18 |
| 建表规范 主键雪花算法（IdWorker / ASSIGN_ID） | M-12 |

## 严重级别判定口径

- **ERROR**：规范使用「必须 / 禁止 / 不得 / 统一使用」等强制措辞的条款，命中即阻断。
- **WARN**：规范使用「尽量 / 可以 / 建议」等推荐措辞的条款，命中仅提示优化。

其中以下两条为推荐性条款，本案例库标记为 `WARN`：建库规范 9（数字类型**可以**加 UNSIGNED）、
建库规范 10（**尽自己的能力**使用 NOT NULL DEFAULT）。

## 已知口径待确认项

1. **表名前缀 `db_`**：规范原文第 2 条描述的是「生产**数据库**均以 `db_` 开头」，示例为 `db_order`、
   `db_cargo`；而命名规范第 15 条说的是「**库前缀**统一使用 `db_`」。字面上 `db_` 是库名前缀而非表名前缀，
   但项目内置正例 SQL 使用 `db_order_info` 这类带前缀表名。D-01 按「表名需带 `db_`」收录，团队需确认最终口径。
2. **布尔字段命名**：规范原文写的是布尔类型 `delete` + 「列名尽量用名词」，而知识库切块中写的是 `is_deleted`。
   F-06 按**原文**（名词式）收录，并在此标注该冲突。
3. **表名关键字判定**：内置 `SqlFeatureExtractor` 会把 `db_` 前缀剥离后再比对保留字，因此 `db_order`
   会被判定命中 `order` 关键字；但规范自身的示例（建库规范 2 的 `db_order`、建表规范的 `idx_order_id`）
   都在正常使用 `order`。D-09 使用的表名是无前缀的 `order`，与该项目内示例的口径差异需要团队确认。

## 使用示例

```bash
# 单条反例直接提交审查（以 N-01 为例）
curl -X POST http://127.0.0.1:8000/api/v1/sql/audits \
  -H "Content-Type: application/json" \
  -d '{"sql_text": "CREATE TABLE `db_OrderInfo` ( ... );"}'
```

期望结果：

- `is_compliant` 为 `false`；
- `violations[].rule_name` 命中该案例标注的「命中规则」；
- `violations[].citation_index` 指向「依据切块」对应的引用编号；
- `markdown_report` 中给出该规则的整改方案与修改后的 SQL。

## 反例 SQL 的语法约定

- 所有反例均为**语法合法**的 MySQL DDL，可以直接在测试库执行，**仅违反规范而非违反语法**；
- 数据库引擎统一使用 `InnoDB`（D-02 除外）、字符集统一 `utf8mb4`（D-07、D-08 除外）；
- 表名默认使用 `db_` 前缀（D-01 除外），以避免触发无关规则；
- 每条案例只故意破坏**一个**目标规则，保证「一条反例 ↔ 一条期望违规」可单点验证。

## 结构与检出率校验

```bash
python doc/negative_cases/validate_cases.py
```

脚本会逐条校验元信息完整性（违反条款 / 命中规则 / 级别 / 依据切块）、`sql` 代码块数量、
括号配对与语句完整性（按 `BEGIN...END` 感知切分，触发器与存储过程反例不会被误报），
并在可加载 `SqlFeatureExtractor` 时统计静态检出覆盖率。

当前基线输出：

```text
案例总数: 76
结构问题: 0
可被提取器特征覆盖的规则域: 23/76
需大模型语义判定: 53/76
```

脚本会按案例的「命中规则」推断其对应的特征槽位（`double` / `tinyint(1)` / 外键 / `db_` 前缀 /
关键字 / 基类字段缺失或类型不符 / 表名冗余前缀），只有槽位与提取器输出对应上的案例才算被静态规则覆盖。
其余 53 条属于命名、术语、索引与注释类反例，需要依赖 RAG 检索到的规范原文由大模型判定，
不适用于正则级静态断言。
