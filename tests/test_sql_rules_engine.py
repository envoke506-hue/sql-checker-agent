"""
SQL 静态规则校验引擎完整单元测试集
覆盖第一阶段与第二阶段所有规则及多语句切分、RESTful 接口测试
"""

import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.sql_rule.engine import SqlRuleEngine


@pytest.fixture
def engine():
    return SqlRuleEngine()


@pytest.fixture
def client():
    return TestClient(app)


# 标准完全合规的建表模板 SQL (基准用例)
COMPLIANT_CREATE_TABLE = """
CREATE TABLE db_trade.t_order (
  id BIGINT UNSIGNED NOT NULL COMMENT '主键',
  code VARCHAR(32) NOT NULL COMMENT '订单编码',
  pay_money DECIMAL(20, 6) NOT NULL COMMENT '支付金额',
  goods_amount DECIMAL(20, 6) NOT NULL COMMENT '商品数量',
  unit_price DECIMAL(20, 6) NOT NULL COMMENT '单价',
  sort INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '排序',
  remark VARCHAR(255) NOT NULL DEFAULT '' COMMENT '备注',
  version INT NOT NULL DEFAULT 0 COMMENT '数据版本',
  deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0 COMMENT '删除标记 0: 未删除 1: 已删除',
  disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0 COMMENT '停用标记 0: 未停用 1: 已停用',
  create_id BIGINT UNSIGNED NOT NULL COMMENT '创建人标识',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  modify_id BIGINT UNSIGNED NOT NULL COMMENT '修改人标识',
  modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='这张表的功能说明';
"""


def test_fully_compliant_sql(engine):
    """测试完全合规的建表 SQL，无任何 ERROR 违规"""
    res = engine.validate(COMPLIANT_CREATE_TABLE)
    assert res.is_compliant is True
    assert res.error_count == 0
    assert len(res.results) == 1
    assert res.results[0].target_table == "db_trade.t_order"


def test_table_meta_rules(engine):
    """测试建表元数据规则: 表名保留字、InnoDB引擎、utf8mb4字符集"""
    # 1. 表名是保留关键字 order, 引擎 MyISAM, 字符集 latin1
    bad_sql = """
    CREATE TABLE db_trade.order (
      id BIGINT UNSIGNED NOT NULL,
      version INT NOT NULL DEFAULT 0,
      deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      create_id BIGINT UNSIGNED NOT NULL,
      create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      modify_id BIGINT UNSIGNED NOT NULL,
      modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY(id)
    ) ENGINE=MyISAM DEFAULT CHARSET=latin1;
    """
    res = engine.validate(bad_sql)
    assert res.is_compliant is False
    rule_ids = [v.rule_id for v in res.results[0].violations]
    assert "RULE_TABLE_KEYWORD" in rule_ids
    assert "RULE_TABLE_ENGINE" in rule_ids
    assert "RULE_TABLE_CHARSET" in rule_ids


def test_schema_prefix_ddl_and_dml(engine):
    """测试 DDL 和 DML 必须有库名前缀且前缀为 db_"""
    # 1. DDL 缺少库名
    ddl_no_db = "CREATE TABLE t_user (id BIGINT UNSIGNED NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    res1 = engine.validate(ddl_no_db)
    assert any(v.rule_id == "RULE_SCHEMA_PREFIX" for v in res1.results[0].violations)

    # 2. DDL 库名非 db_ 开头
    ddl_bad_db = "CREATE TABLE trade.t_user (id BIGINT UNSIGNED NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    res2 = engine.validate(ddl_bad_db)
    assert any(v.rule_id == "RULE_SCHEMA_PREFIX" for v in res2.results[0].violations)

    # 3. DML 包含未加库名的表
    dml_sql = "SELECT a.id, b.name FROM user_info a JOIN db_user.dept b ON a.dept_id = b.id;"
    res3 = engine.validate(dml_sql)
    assert res3.is_compliant is False
    assert any(v.rule_id == "RULE_SCHEMA_PREFIX" for v in res3.results[0].violations)

    # 4. DML 全量合规库名
    dml_ok = "SELECT a.id, b.name FROM db_user.user_info a JOIN db_user.dept b ON a.dept_id = b.id WHERE a.id = 1;"
    res4 = engine.validate(dml_ok)
    assert res4.is_compliant is True


def test_column_naming_and_keywords(engine):
    """测试字段 lower_snake_case 命名法与禁用保留关键字"""
    bad_sql = """
    CREATE TABLE db_trade.t_test (
      id BIGINT UNSIGNED NOT NULL,
      userId BIGINT UNSIGNED NOT NULL,
      user_name_test VARCHAR(32) NOT NULL,
      `select` INT NOT NULL,
      version INT NOT NULL DEFAULT 0,
      deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      create_id BIGINT UNSIGNED NOT NULL,
      create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      modify_id BIGINT UNSIGNED NOT NULL,
      modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    res = engine.validate(bad_sql)
    assert res.is_compliant is False
    rule_ids = [v.rule_id for v in res.results[0].violations]
    assert "RULE_COL_SNAKE_CASE" in rule_ids  # userId
    assert "RULE_COL_KEYWORD" in rule_ids     # select


def test_column_type_and_precision_rules(engine):
    """测试禁止 float/double、TINYINT(4)、decimal(20,6)、禁止字段级字符集"""
    bad_sql = """
    CREATE TABLE db_trade.t_types (
      id BIGINT UNSIGNED NOT NULL,
      rate_val DOUBLE NOT NULL,
      float_val FLOAT NOT NULL,
      status_flag TINYINT(1) NOT NULL,
      status_raw TINYINT NOT NULL,
      bad_money DECIMAL(10, 2) NOT NULL,
      raw_dec DECIMAL NOT NULL,
      bad_collate VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
      version INT NOT NULL DEFAULT 0,
      deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      create_id BIGINT UNSIGNED NOT NULL,
      create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      modify_id BIGINT UNSIGNED NOT NULL,
      modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    res = engine.validate(bad_sql)
    assert res.is_compliant is False
    violations = res.results[0].violations
    rule_ids = [v.rule_id for v in violations]

    assert "RULE_NO_FLOAT_DOUBLE" in rule_ids
    assert "RULE_TINYINT_4" in rule_ids
    assert "RULE_DECIMAL_PRECISION" in rule_ids
    assert "RULE_NO_FIELD_CHARSET" in rule_ids


def test_base_template_fields_check(engine):
    """测试 8 大基类字段缺失及类型不一致检查 (注释豁免)"""
    # 缺少 deleted, disabled, modify_time，且 version 类型为 BIGINT，id 缺少 unsigned
    bad_sql = """
    CREATE TABLE db_trade.t_demo (
      id BIGINT NOT NULL,
      version BIGINT NOT NULL DEFAULT 0,
      create_id BIGINT UNSIGNED NOT NULL,
      create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      modify_id BIGINT UNSIGNED NOT NULL,
      PRIMARY KEY(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试注释不同';
    """
    res = engine.validate(bad_sql)
    assert res.is_compliant is False
    violations = res.results[0].violations
    msgs = " ".join(v.message for v in violations)
    assert "缺少必需的基类审计字段" in msgs
    assert "deleted" in msgs
    assert "disabled" in msgs
    assert "modify_time" in msgs
    assert any("BIGINT UNSIGNED" in v.message for v in violations)


def test_prohibited_objects_and_fk(engine):
    """测试禁止外键、存储过程、触发器、自定义函数"""
    # 1. 外键
    fk_sql = """
    CREATE TABLE db_trade.t_fk (
      id BIGINT UNSIGNED NOT NULL,
      user_id BIGINT UNSIGNED NOT NULL,
      PRIMARY KEY(id),
      FOREIGN KEY (user_id) REFERENCES db_user.t_user(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    res1 = engine.validate(fk_sql)
    assert any(v.rule_id == "RULE_NO_FOREIGN_KEY" for v in res1.results[0].violations)

    # 2. 存储过程
    proc_sql = "CREATE PROCEDURE db_trade.proc_test() BEGIN SELECT 1; END;"
    res2 = engine.validate(proc_sql)
    assert any(v.rule_id == "RULE_NO_TRIGGER_PROCEDURE" for v in res2.results[0].violations)

    # 3. 触发器
    trg_sql = "CREATE TRIGGER db_trade.trg_test BEFORE INSERT ON db_trade.t_order FOR EACH ROW BEGIN END;"
    res3 = engine.validate(trg_sql)
    assert any(v.rule_id == "RULE_NO_TRIGGER_PROCEDURE" for v in res3.results[0].violations)


def test_alter_table_after_rule(engine):
    """测试 ALTER TABLE 增加字段必须标注 AFTER"""
    # 1. 缺少 AFTER
    bad_alter = "ALTER TABLE db_trade.t_order ADD COLUMN extra_info VARCHAR(64);"
    res1 = engine.validate(bad_alter)
    assert res1.is_compliant is False
    assert any(v.rule_id == "RULE_ALTER_TABLE_AFTER" for v in res1.results[0].violations)

    # 2. 带有 AFTER
    ok_alter = "ALTER TABLE db_trade.t_order ADD COLUMN extra_info VARCHAR(64) AFTER remark;"
    res2 = engine.validate(ok_alter)
    assert res2.is_compliant is True


def test_multi_statement_batch_validation(engine):
    """测试多条 SQL 语句切分解析与逐条汇总"""
    batch_sql = f"""
    {COMPLIANT_CREATE_TABLE}
    ALTER TABLE db_trade.t_order ADD COLUMN tag_info VARCHAR(32) AFTER remark;
    SELECT id, code FROM db_trade.t_order WHERE id = 100;
    CREATE TABLE db_trade.bad_table (id INT) ENGINE=MyISAM;
    """
    res = engine.validate(batch_sql)
    assert res.total_statements == 4
    # 前三条合规，第四条有违规
    assert res.results[0].is_compliant is True
    assert res.results[1].is_compliant is True
    assert res.results[2].is_compliant is True
    assert res.results[3].is_compliant is False
    assert res.is_compliant is False


def test_semantic_redundant_table_prefix(engine):
    """测试第二阶段: 本表自己的字段前不需要加表名 (如 order 表的 order_code -> code)"""
    bad_sql = """
    CREATE TABLE db_trade.order_info (
      id BIGINT UNSIGNED NOT NULL,
      order_code VARCHAR(32) NOT NULL COMMENT '订单编号',
      order_money DECIMAL(20, 6) NOT NULL COMMENT '订单金额',
      version INT NOT NULL DEFAULT 0,
      deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      create_id BIGINT UNSIGNED NOT NULL,
      create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      modify_id BIGINT UNSIGNED NOT NULL,
      modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    res = engine.validate(bad_sql)
    assert res.is_compliant is False
    violations = res.results[0].violations
    prefix_violations = [v for v in violations if v.rule_id == "RULE_NO_TABLE_PREFIX_IN_COLUMN"]
    assert len(prefix_violations) == 1
    # 验证降噪聚合: 同规则多字段合并为一条
    aggregated_v = prefix_violations[0]
    assert "order_code" in aggregated_v.target_object
    assert "order_money" in aggregated_v.target_object
    assert "code" in aggregated_v.suggested_fix
    assert "money" in aggregated_v.suggested_fix


def test_semantic_r_relation_and_third_party(engine):
    """测试第二阶段: 关联表 r_ 开头与三方对接表来源字段"""
    # 1. 关联表未以 r_ 开头
    bad_rel = """
    CREATE TABLE db_user.user_role_relation (
      id BIGINT UNSIGNED NOT NULL,
      user_id BIGINT UNSIGNED NOT NULL,
      role_id BIGINT UNSIGNED NOT NULL,
      version INT NOT NULL DEFAULT 0,
      deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      create_id BIGINT UNSIGNED NOT NULL,
      create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      modify_id BIGINT UNSIGNED NOT NULL,
      modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    res1 = engine.validate(bad_rel)
    assert any(v.rule_id == "RULE_RELATION_TABLE_R" for v in res1.results[0].violations)

    # 2. 三方对接表缺失 system_source 和 data_source
    bad_third = """
    CREATE TABLE db_trade.third_order (
      id BIGINT UNSIGNED NOT NULL,
      code VARCHAR(32) NOT NULL,
      version INT NOT NULL DEFAULT 0,
      deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      create_id BIGINT UNSIGNED NOT NULL,
      create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      modify_id BIGINT UNSIGNED NOT NULL,
      modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='第三方同步订单';
    """
    res2 = engine.validate(bad_third)
    assert any(v.rule_id == "RULE_THIRD_PARTY_TABLE" for v in res2.results[0].violations)


def test_semantic_terminology_and_warns(engine):
    """测试第二阶段: 名词术语替换字典与建议项 WARN"""
    sql_with_anti_pattern = """
    CREATE TABLE db_user.t_employee (
      id BIGINT UNSIGNED NOT NULL,
      organization_id BIGINT UNSIGNED NOT NULL,
      state TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      age INT NOT NULL,
      version INT NOT NULL DEFAULT 0,
      deleted TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      disabled TINYINT(4) UNSIGNED NOT NULL DEFAULT 0,
      create_id BIGINT UNSIGNED NOT NULL,
      create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      modify_id BIGINT UNSIGNED NOT NULL,
      modify_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    res = engine.validate(sql_with_anti_pattern)
    violations = res.results[0].violations
    rule_ids = [v.rule_id for v in violations]
    # 命中术语反例 organization -> organ, state -> status
    assert "RULE_TERMINOLOGY" in rule_ids
    # 命中建议性条款 WARN: age 未加 unsigned
    assert any(v.severity == "WARN" and v.rule_id == "WARN_UNSIGNED_NUMBER" for v in violations)


@pytest.mark.anyio
async def test_audit_sql_service_pipeline():
    """测试 SqlAuditService: 先执行代码静态规则判断，后续再走大模型判断与合并"""
    from app.models.dto.sql_audit import SqlAuditRequest
    from app.models.entity.chunk import Chunk, ChunkMetadata
    from tests.test_sql_audit_service_offline import ScriptedRelayRepository, StaticRetrievalService
    from app.services.sql_audit_service import SqlAuditService

    # 模拟大模型返回 JSON
    llm_output = json.dumps({
        "is_compliant": False,
        "summary": "检测到金额字段与表名规范违规",
        "violations": [
            {
                "rule_id": "RULE_SEMANTIC_NAMING",
                "rule_name": "语义与命名规范",
                "severity": "ERROR",
                "target_object": "total_money double",
                "description": "金额字段类型不符合 decimal 规范",
                "suggested_fix": "修改为 decimal(20, 6)",
                "citation_index": 1
            }
        ],
        "suggested_sql": "CREATE TABLE db_trade.t_order (id BIGINT UNSIGNED NOT NULL, total_money DECIMAL(20, 6) NOT NULL);"
    })

    audit_service = SqlAuditService(
        retrieval_svc=StaticRetrievalService(),
        relay_repo=ScriptedRelayRepository([llm_output])
    )

    # 待审 SQL 包含: 无 db_ 库名前缀、使用了 DOUBLE
    raw_sql = """
    CREATE TABLE t_order (
      id BIGINT UNSIGNED NOT NULL,
      total_money DOUBLE NOT NULL,
      PRIMARY KEY(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    res = await audit_service.audit_sql(SqlAuditRequest(sql_text=raw_sql))
    assert res.is_compliant is False
    # 验证代码静态规则已先行捕获并与大模型输出合并
    rule_ids = [v.rule_id for v in res.violations]
    assert "RULE_SCHEMA_PREFIX" in rule_ids     # 静态规则: 缺少 db_ 前缀
    assert "RULE_NO_FLOAT_DOUBLE" in rule_ids   # 静态规则: 禁止 double
    assert res.score < 100
    assert "Markdown" in str(type(res.markdown_report)) or len(res.markdown_report) > 0


def test_restful_audit_controller_endpoint(client):
    """测试统一审核接口 POST /api/v1/sql/audits 正常挂载与入参校验"""
    # 测试空入参触发 422 参数校验拦截
    resp = client.post("/api/v1/sql/audits", json={"sql_text": ""})
    assert resp.status_code == 422

