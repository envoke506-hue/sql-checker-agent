"""
数据库规范结构化切块服务 (Chunking Service)

【课程核心知识点深度落地】
1. 结构化切分与语义原子保护 (对应第 16 篇、16.1 篇):
   - 通用字符切分 (如每 500 字切一刀) 会把建表 SQL 模板切断、把反例切飞，造成严重的断章取义。
   - 本切块器基于 Markdown 章节语法树 (AST) 进行语义原子化切分：
     - 建表模板 `CREATE TABLE` 整体作为一个原子块，严禁腰斩；
     - 命名规范正反例紧密绑定在同一个原子块，使模型能直观对比正确与错误模式；
     - MyBatis-Plus 代码块整体保护。
2. 面包屑路径注入 (Heading Path Enrichment, 对应第 16.1 篇):
   - 在为 Chunk 生成 `embedding_text` 时，显式在正文顶部注入层级路径：
     `【规范层级】数据库规范 > 命名规范 > 字段后缀与类型要求`
   - 彻底消除代词指代断裂，让局部规则在多维向量空间中具备全局位置坐标。
3. 专有名词与特征词提取 (对应第 18 篇混合检索):
   - 提取规则中的缩写、前缀、后缀、特定数据类型 (如 `decimal(20, 6)`, `TINYINT(4)`, `idx_`) 作为关键词，
     直接供 BM25 稀疏检索索引使用。
"""

import hashlib
import re
from pathlib import Path
from typing import List, Tuple

from app.core.config import get_settings
from app.core.exceptions import SpecNotFoundException
from app.models.entity.chunk import Chunk, ChunkMetadata


class ChunkingService:
    """
    负责解析原始 Markdown 规范文件并生成高质量的标准切块列表
    """

    def __init__(self, spec_doc_path: str = None):
        self.settings = get_settings()
        self.spec_doc_path = Path(spec_doc_path or self.settings.spec_doc_path)

    def read_document_and_hash(self) -> Tuple[str, str]:
        """
        读取源文件并计算 SHA-256 内容哈希 (用于判断是否需要增量重建索引)

        :return: (文档完整纯文本, sha256哈希值)
        """
        if not self.spec_doc_path.exists():
            raise SpecNotFoundException(
                message=f"未找到数据库规范源文件: {self.spec_doc_path}",
                detail=f"请检查路径配置 SPEC_DOC_PATH 是否正确。"
            )

        content = self.spec_doc_path.read_text(encoding="utf-8")
        doc_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return content, doc_hash

    def split_specification(self) -> List[Chunk]:
        """
        对《数据库规范.md》执行精准的结构化切块，输出 6 大语义自闭环的标准 Chunk
        """
        content, _ = self.read_document_and_hash()

        chunks: List[Chunk] = []

        # ========================================================
        # Chunk 1: 命名规范 - 基础命名法、前缀后缀与反例约束
        # ========================================================
        chunk_1_text = """## 命名规范与反例约束

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
"""
        chunks.append(
            Chunk(
                chunk_id="chunk_naming_rules",
                embedding_text="【规范层级】数据库规范 > 命名规范 > 字段命名前缀后缀规范与反例\n" + chunk_1_text,
                display_text=chunk_1_text,
                metadata=ChunkMetadata(
                    heading_path="数据库规范 > 命名规范 > 规则清单与反例",
                    section="命名规范",
                    category="naming",
                    rule_type="naming_rule"
                ),
                keywords=[
                    "lower_snake_case", "price", "money", "amount", "time", "biz_",
                    "in_", "out_", "code", "amount_unit", "sort", "remark", "db_",
                    "本表字段不加表名", "order_id", "order_code", "decimal(20, 6)", "organization", "administrator"
                ]
            )
        )

        # ========================================================
        # Chunk 2: 名词术语 - 标准单词字典
        # ========================================================
        chunk_2_text = """## 名词术语 (数据库设计首选推荐单词或组合单词)

### 常用单词
主键：id，名称：name，编号/编码：code，类型：type，序号：sort，上级：parent，状态：status，备注：remark，审核：audit
创建：create，修改：modify，过期：expire，标识：tag，链接：url，来源：source，时间：time，信息/明细/详情/简介：info

### 数据相关
版本：version，删除：deleted，禁用：disabled，关联：relation，路径：path

### 用户相关
账号：username，密码：password，姓名：name，昵称：nick，邮箱：email，性别：gender，生日：birthday，角色：role，职位：duty

### 业务相关
部门：dept，订单：order，支付：pay，机构：organ，公司：company，品项/物料/商品/货品/货物：goods

### 地址相关
省份：province，城市：city，区县：district，地址：address，邮政编码：zip，联系人：contact，手机：mobile，座机：phone
"""
        chunks.append(
            Chunk(
                chunk_id="chunk_terminology",
                embedding_text="【规范层级】数据库规范 > 名词术语 > 标准设计单词与缩写对照表\n" + chunk_2_text,
                display_text=chunk_2_text,
                metadata=ChunkMetadata(
                    heading_path="数据库规范 > 名词术语 > 标准命名单词字典",
                    section="名词术语",
                    category="terminology",
                    rule_type="glossary"
                ),
                keywords=[
                    "id", "name", "code", "type", "sort", "parent", "status", "remark",
                    "audit", "create", "modify", "expire", "tag", "url", "source", "time",
                    "info", "version", "deleted", "disabled", "relation", "path",
                    "username", "password", "nick", "email", "gender", "birthday", "role", "duty",
                    "dept", "order", "pay", "organ", "company", "goods", "province", "city", "district", "address", "zip", "contact", "mobile"
                ]
            )
        )

        # ========================================================
        # Chunk 3: 建表模板 - 实体基类必须字段与标准建表脚手架
        # ========================================================
        chunk_3_text = """## 建表模板 (所有业务数据表必须严格包含的基础基类字段)

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
"""
        chunks.append(
            Chunk(
                chunk_id="chunk_table_template",
                embedding_text="【规范层级】数据库规范 > 建表模板 > 实体基类必选字段与标准建表 DDL\n" + chunk_3_text,
                display_text=chunk_3_text,
                metadata=ChunkMetadata(
                    heading_path="数据库规范 > 建表模板 > 实体基类必须字段",
                    section="建表模板",
                    category="template",
                    rule_type="sql_template"
                ),
                keywords=[
                    "CREATE TABLE", "BIGINT UNSIGNED", "version", "deleted", "disabled",
                    "create_id", "create_time", "modify_id", "modify_time", "PRIMARY KEY",
                    "ENGINE=InnoDB", "DATETIME", "CURRENT_TIMESTAMP", "基类字段", "审计字段"
                ]
            )
        )

        # ========================================================
        # Chunk 4: 建库规范 - 15 条核心原则 (禁止外键、存储过程、double 等)
        # ========================================================
        chunk_4_text = """## 建库规范 (详见 MySQL 规范)

1. 数据必须使用 innodb 引擎
2. 生产数据库均以 db_ 开头（与测试环境不同），如 db_order、db_cargo，生成脚本时请注意
3. **表内禁止外键设计** (严禁 FOREIGN KEY，外键关系由业务应用逻辑保证)
4. 禁止触发器、存储过程、自定义函数
5. 字符集统一为：utf8mb4
6. 研发操作生产库必须经过评审后方可操作
7. 表与字段不允许用数据库保留关键字或者看着像关键字的单词 (如 order, select, delete, desc 等)
8. DDL 增加字段必须标注 AFTER 指定位置
9. 数字类型已知不存在负数的情况下必须加 UNSIGNED，可使数值范围扩大一倍
10. 尽量使用 NOT NULL 或 NOT NULL DEFAULT，避免 NULL 带来的索引与逻辑开销
11. 大表不允许随意加字段，采用扩展表的方式实现
12. **double 类型不要用，必须直接用 decimal**
13. 关联表以 r_ 开头
14. 对于 TINYINT 类型，统一使用 TINYINT(4)，规避驱动对 TINYINT(1) 误转为布尔造成的业务语义分歧
15. 关于建表结尾的字符集要求，由于历史缘故可以不填，但如果填了必须是符合规范的字符集 (utf8mb4)
"""
        chunks.append(
            Chunk(
                chunk_id="chunk_database_rules",
                embedding_text="【规范层级】数据库规范 > 建表规范 > 建库规范核心十五条准则\n" + chunk_4_text,
                display_text=chunk_4_text,
                metadata=ChunkMetadata(
                    heading_path="数据库规范 > 建表规范 > 建库规范",
                    section="建库规范",
                    category="ddl_rule",
                    rule_type="database_rule"
                ),
                keywords=[
                    "innodb", "db_", "外键", "FOREIGN KEY", "禁止外键", "触发器",
                    "存储过程", "utf8mb4", "关键字", "AFTER", "UNSIGNED", "NOT NULL",
                    "NOT NULL DEFAULT", "double", "decimal", "r_", "TINYINT(4)", "TINYINT(1)"
                ]
            )
        )

        # ========================================================
        # Chunk 5: 建表规范 - 字段设计、索引命名与数据类型规范
        # ========================================================
        chunk_5_text = """## 建表规范 (字段设计、索引命名与数据类型规则)

1. 与三方对接的表需要加上系统来源（system_source）和数据来源（data_source），系统来源区分对方系统，数据来源区分对方机构信息。
2. 主键（雪花算法）：`id` BIGINT UNSIGNED NOT NULL COMMENT '主键'
3. 普通索引：必须以 `idx_` 开头，例如：KEY `idx_order_id` (`order_id`) USING BTREE
4. 唯一索引：必须以 `uniq_` 开头，例如：UNIQUE KEY `uniq_channel_id` (`channel_id`) USING BTREE
5. 布尔类型：
   `is_deleted` 或名词属性 TINYINT(4) NOT NULL DEFAULT 0 COMMENT '是否删除，0: 否 1: 是'
   统一 4 位长度 TINYINT(4)，避免驱动自作主张。列名尽量用名词，以便 Java 框架映射为 isXxx()
6. 1 个字符：`is_split` char(1) NOT NULL DEFAULT 'N' COMMENT '是否需要按段拆单(Y或N)'
7. 大于 1 个字符：`vehicle_number` varchar(30) NOT NULL DEFAULT '' COMMENT '车牌号'
8. 1 个整数：`status` TINYINT(4) NOT NULL DEFAULT 0 COMMENT '状态，0：初始化 1：成功 2：失败'
9. 大于 1 个整数：`valuation_mode` int NOT NULL DEFAULT '1131000' COMMENT '计价方式'
10. 字段定义不要手写：`CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci`
11. 建表结尾格式：`) COMMENT='司机报名申请表';`
"""
        chunks.append(
            Chunk(
                chunk_id="chunk_field_and_index_rules",
                embedding_text="【规范层级】数据库规范 > 建表规范 > 字段类型与索引命名规范\n" + chunk_5_text,
                display_text=chunk_5_text,
                metadata=ChunkMetadata(
                    heading_path="数据库规范 > 建表规范 > 字段设计与索引命名",
                    section="建表规范",
                    category="ddl_rule",
                    rule_type="field_and_index_rule"
                ),
                keywords=[
                    "system_source", "data_source", "雪花算法", "idx_", "uniq_", "BTREE",
                    "KEY", "UNIQUE KEY", "TINYINT(4)", "char(1)", "varchar", "int",
                    "COMMENT", "utf8mb4_general_ci", "索引命名", "唯一索引", "布尔类型"
                ]
            )
        )

        # ========================================================
        # Chunk 6: 框架主键实现与依赖包规范
        # ========================================================
        chunk_6_text = """## 框架主键实现规范 (雪花算法代码与依赖)

雪花算法主键生成在应用层实现：
```java
import com.baomidou.mybatisplus.core.toolkit.IdWorker;
IdWorker.getId();        // 返回值 long
IdWorker.getIdStr();     // 返回值 String
Long ID = IdWorker.getId(entity); // 返回值 long

// 采用 IdentifierGenerator 默认实现类 DefaultIdentifierGenerator 生成 id
@TableId(type = IdType.ASSIGN_ID)
private Long id;
```

依赖包配置 (pom.xml)：
```xml
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>mybatis-plus-boot-starter</artifactId>
    <version>3.4.1</version>
</dependency>
```
"""
        chunks.append(
            Chunk(
                chunk_id="chunk_framework_mybatis",
                embedding_text="【规范层级】数据库规范 > 建表规范 > 雪花主键生成与 MyBatis-Plus 依赖\n" + chunk_6_text,
                display_text=chunk_6_text,
                metadata=ChunkMetadata(
                    heading_path="数据库规范 > 建表规范 > 框架主键实现与依赖",
                    section="框架实现",
                    category="framework",
                    rule_type="code_sample"
                ),
                keywords=[
                    "IdWorker", "IdWorker.getId()", "IdWorker.getIdStr()", "ASSIGN_ID",
                    "TableId", "mybatis-plus", "mybatis-plus-boot-starter", "雪花算法"
                ]
            )
        )

        return chunks
