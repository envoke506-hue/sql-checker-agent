"""
第四阶段测试：上下文编排 (Lost-in-the-Middle)、Double Check 二次核验与端到端智能审查
测试内容包括：
1. ContextOrchestrator: Lost-in-the-Middle 排序算法与引用编号分配
2. DoubleCheckVerifier: 序号越界与正文无依据的幻觉拦截
3. SpecQueryService: 端到端自然语言问答与 Markdown 格式输出
4. SqlAuditService: 真实违规 SQL 审查、防幻觉核验、重构 DDL 与 Markdown 报告生成
5. FastAPI Controller: 端到端 HTTP POST /api/v1/sql/audits 与 /api/v1/spec/queries
"""

import sys
import asyncio
from pathlib import Path

# 保证 Windows 命令行控制台输出中文不乱码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# 将项目根目录加入 sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from app.main import app
from app.models.dto.sql_audit import SqlAuditRequest, ViolationDetail
from app.models.dto.spec_query import SpecQueryRequest
from app.models.entity.chunk import Chunk, ChunkMetadata
from app.services.context_orchestrator import ContextOrchestrator
from app.services.double_check_verifier import DoubleCheckVerifier
from app.services.sql_audit_service import SqlAuditService
from app.services.spec_query_service import SpecQueryService
from app.core.dependencies import get_sql_audit_service, get_spec_query_service


def test_1_lost_in_the_middle_orchestration():
    """测试 1: Lost-in-the-Middle 头尾交叉重排与编号映射"""
    print("\n--- [测试 1: Lost-in-the-Middle 头尾编排算法] ---")
    orchestrator = ContextOrchestrator()

    # 构造 5 个模拟规范切块
    dummy_chunks = []
    for char in ["A", "B", "C", "D", "E"]:
        c = Chunk(
            chunk_id=f"chunk_{char}",
            embedding_text=f"Embedding text {char}",
            display_text=f"规范正文内容 {char}",
            metadata=ChunkMetadata(
                doc_title="数据库规范",
                heading_path=f"数据库规范 > 小节 {char}",
                section=f"小节 {char}",
                category="naming",
                rule_type="test"
            )
        )
        dummy_chunks.append((c, 0.9 - len(dummy_chunks) * 0.1))

    # 执行重排：输入顺序为 [A(0), B(1), C(2), D(3), E(4)]
    # 理论预期：A 在最前，B 在最后，C 在前二，D 在倒数第二，E 在中间 -> [A, C, E, D, B]
    reordered = orchestrator.reorder_lost_in_the_middle(dummy_chunks)
    reordered_ids = [item[0].chunk_id for item in reordered]
    assert reordered_ids == ["chunk_A", "chunk_C", "chunk_E", "chunk_D", "chunk_B"], f"重排顺序不符预期: {reordered_ids}"
    print(f"[PASS] Lost-in-the-Middle 头尾重排逻辑验证成功: 输入=[A, B, C, D, E] -> 重排后={reordered_ids}")

    # 编排完整上下文并验证编号分配
    ctx = orchestrator.orchestrate(dummy_chunks, enable_reorder=True)
    assert len(ctx.citations) == 5, f"引用明细数量不符: {len(ctx.citations)}"
    assert ctx.citations[0].index == 1
    assert "【规范依据 [1]】" in ctx.formatted_context_text
    assert "【规范依据 [5]】" in ctx.formatted_context_text
    assert 1 in ctx.chunk_index_map and 5 in ctx.chunk_index_map
    print("[PASS] 动态引用编号 [1]~[5] 与 Citation 实体组装成功！")


def test_2_double_check_anti_hallucination():
    """测试 2: Double Check 规则断言与防幻觉二次核验"""
    print("\n--- [测试 2: Double Check 防幻觉二次核验] ---")
    verifier = DoubleCheckVerifier()

    # 准备一个包含真实外键规范的 Chunk 实体
    real_chunk = Chunk(
        chunk_id="chunk_database_rules",
        embedding_text="建库规范 表内禁止外键设计",
        display_text="### 建库规范\n1. 表内禁止外键设计，严禁使用 FOREIGN KEY 约束，关联关系应在应用层维护。",
        metadata=ChunkMetadata(
            heading_path="数据库规范 > 建库规范",
            section="建库规范",
            category="ddl_rule"
        )
    )
    chunk_index_map = {1: real_chunk}

    # 构造待核验的 3 个违规项：
    # 1. 真实违规：外键违规，引用有效 [1]，正文存在对应依据
    valid_violation = ViolationDetail(
        rule_id="rule_foreign_key",
        rule_name="禁止外键设计",
        severity="ERROR",
        target_object="CONSTRAINT fk_user FOREIGN KEY",
        description="建库规范严禁使用 FOREIGN KEY 外键约束",
        suggested_fix="删除 FOREIGN KEY 约束",
        citation_index=1
    )

    # 2. 幻觉 1：引用了不存在的序号 [99]
    out_of_bound_violation = ViolationDetail(
        rule_id="rule_fake_1",
        rule_name="字段长度超限",
        severity="WARN",
        target_object="remark",
        description="模型自行臆造的规则",
        suggested_fix="缩短字段",
        citation_index=99
    )

    # 3. 幻觉 2：引用序号有效 [1]，但该 Chunk 里压根没提这个规则（例如声称违反了分库分表规则）
    hallucination_violation = ViolationDetail(
        rule_id="rule_fake_2",
        rule_name="单表行数超过500万必须分库分表",
        severity="ERROR",
        target_object="table_row_count",
        description="模型脑补的规则，规范依据[1]中白纸黑字完全未提及",
        suggested_fix="分表",
        citation_index=1
    )

    res = verifier.verify_and_filter(
        raw_violations=[valid_violation, out_of_bound_violation, hallucination_violation],
        chunk_index_map=chunk_index_map
    )

    assert len(res.verified_violations) == 1, f"真实违规数应为 1，实际: {len(res.verified_violations)}"
    assert res.verified_violations[0].rule_id == "rule_foreign_key"
    assert len(res.hallucinations) == 2, f"拦截的幻觉数应为 2，实际: {len(res.hallucinations)}"
    assert not res.is_compliant, "存在真实违规，合规状态应为 False"
    assert res.score == 80, f"单项 ERROR 扣 20 分，最终得分应为 80，实际: {res.score}"
    print(f"[PASS] Double Check 成功拦截 2 项模型幻觉误报，保留真实外键违规，得分动态修正为 {res.score} 分！")


async def test_3_spec_query_e2e():
    """测试 3: 自然语言规范问答端到端推理与 Markdown 生成"""
    print("\n--- [测试 3: SpecQueryService 端到端规范问答] ---")
    service = get_spec_query_service()

    request = SpecQueryRequest(
        question="在数据库设计规范中，金额字段必须使用什么数据类型存储？单价和金额的命名后缀有什么要求？"
    )

    print(f"提问: {request.question}")
    response = await service.query_spec(request)

    assert len(response.answer) > 20, "回答内容过短"
    assert len(response.citations) > 0, "应附带规范依据引用"
    assert "### 💡 数据库规范咨询解答" in response.markdown_content
    print(f"\n[LLM 问答输出 Markdown 预览]:\n{response.markdown_content[:350]}...\n")
    print(f"[PASS] 规范问答端到端调用成功，关联了 {len(response.citations)} 条规范引用依据！")


async def test_4_sql_audit_e2e():
    """测试 4: 真实违规 SQL 端到端智能审查、Double Check 与重构 SQL 生成"""
    print("\n--- [测试 4: SqlAuditService 真实违规 SQL 端到端智能审查] ---")
    service = get_sql_audit_service()

    # 包含典型违规的 SQL：
    # 1. 表名 order (保留关键字、缺少 db_ 前缀)
    # 2. 主键 order_id (本表字段加表名前缀反例)
    # 3. 价格 total_amount double (禁用 double)
    # 4. 外键 FOREIGN KEY (严禁外键)
    # 5. 缺失 7 大基类审计字段
    bad_sql = """
    CREATE TABLE `order` (
        `order_id` bigint(20) NOT NULL AUTO_INCREMENT,
        `order_no` varchar(64) NOT NULL,
        `total_amount` double NOT NULL COMMENT '总金额',
        `user_id` bigint(20) NOT NULL COMMENT '用户ID',
        PRIMARY KEY (`order_id`),
        CONSTRAINT `fk_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
    """

    request = SqlAuditRequest(sql_text=bad_sql)
    print("[INFO] 提交待审查违规 SQL，开始调用 RAG 检索 + Lost-in-the-Middle 编排 + DeepSeek 推理 + Double Check...")

    audit_result = await service.audit_sql(request)

    print(f"\n[审查结果看板]:")
    print(f" - 是否合规: {audit_result.is_compliant} (预期 False)")
    print(f" - 合规评分: {audit_result.score} / 100")
    print(f" - 违规条数: {len(audit_result.violations)} 项")
    print(f" - 核心总结: {audit_result.summary}")

    assert not audit_result.is_compliant, "存在明显违规，is_compliant 必须为 False"
    assert audit_result.score < 100, "存在违规时得分必须低于 100"
    assert len(audit_result.violations) >= 2, f"至少应检测出 2 项核心违规，实际: {len(audit_result.violations)}"

    # 验证违规项中是否检测到了 double、外键或冗余前缀
    violation_rules = [v.rule_name for v in audit_result.violations]
    violation_descs = " ".join([v.description + " " + v.target_object for v in audit_result.violations])
    print(f" - 检测到的违规明细清单: {violation_rules}")

    # 验证重构 SQL 是否补全了 decimal、去除了外键、包含 id
    print(f"\n[重构合规 SQL 预览]:\n{audit_result.suggested_sql[:300]}...")
    assert "foreign key" not in audit_result.suggested_sql.lower(), "重构 SQL 严禁保留外键"

    # 验证精简 Markdown 整改回复格式: 不满足项 (含编号引用依据) + 整改方案 + 修改后的 SQL
    report = audit_result.markdown_report
    assert "### ⚠️ 不满足项与整改方案" in report
    assert "依据：" in report and f"[{audit_result.violations[0].citation_index}]" in report
    assert "- 整改方案：" in report
    assert "### ✅ 修改后的 SQL" in report
    assert "审查总览看板" not in report, "精简回复不应再包含总览看板"
    assert "待审查原始 SQL" not in report, "精简回复不应再回显原始 SQL"

    print("\n[生成的精简 Markdown 整改回复前 600 字符]:")
    print("-------------------------------------------------------")
    print(report[:600])
    print("-------------------------------------------------------")
    print("[PASS] 端到端违规反例审查回复生成成功，仅包含不满足项 + 整改方案 + 修改后的 SQL！")


async def test_4b_compliant_sql_positive():
    """测试 4b: 真实完全合规正例 SQL 端到端审查 (100分通过测试)"""
    print("\n--- [测试 4b: SqlAuditService 完全合规正例 SQL 审查 (正例测试)] ---")
    service = get_sql_audit_service()

    # 100% 严格符合规范的正例 SQL：
    # 1. db_ 开头表名
    # 2. id BIGINT UNSIGNED 主键
    # 3. 命名规范：本表字段无冗余前缀、金额 order_money、类型 decimal(20, 6)
    # 4. 无外键
    # 5. 严格包含 7 大基类审计字段 (version, deleted, disabled, create_id, create_time, modify_id, modify_time)
    # 6. InnoDB 引擎、utf8mb4、完整中文注释
    perfect_sql = """
    CREATE TABLE `db_order_info` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
      `code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '订单编码',
      `order_money` DECIMAL(20, 6) NOT NULL DEFAULT '0.000000' COMMENT '订单金额',
      `status` TINYINT(4) NOT NULL DEFAULT 0 COMMENT '订单状态',
      `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
      `deleted` TINYINT(4) NOT NULL DEFAULT 0 COMMENT '逻辑删除',
      `disabled` TINYINT(4) NOT NULL DEFAULT 0 COMMENT '禁用标记',
      `create_id` BIGINT NOT NULL DEFAULT 0 COMMENT '创建人ID',
      `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
      `modify_id` BIGINT NOT NULL DEFAULT 0 COMMENT '更新人ID',
      `modify_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='标准合规订单表';
    """

    request = SqlAuditRequest(sql_text=perfect_sql)
    print("[INFO] 提交完全合规正例 SQL，验证模型与 DoubleCheck 是否评定 100 分及零违规...")

    audit_result = await service.audit_sql(request)

    print(f"\n[正例审查看板]:")
    print(f" - 是否合规: {audit_result.is_compliant} (预期 True)")
    print(f" - 合规评分: {audit_result.score} / 100 (预期 100)")
    print(f" - 违规条数: {len(audit_result.violations)} 项 (预期 0)")
    print(f" - 核心总结: {audit_result.summary}")

    assert audit_result.is_compliant, f"合规正例 SQL 判定错误: {audit_result.violations}"
    assert audit_result.score == 100, f"合规正例得分应为 100，实际: {audit_result.score}"
    assert len(audit_result.violations) == 0, f"合规正例不应产生违规条目: {audit_result.violations}"
    assert "完全合规" in audit_result.markdown_report
    print("[PASS] 完全合规正例 SQL 审查验证通过！系统评定 100 分满分！")


def test_5_http_controller_endpoints():
    """测试 5: FastAPI RESTful 端点集成测试"""
    print("\n--- [测试 5: RESTful API 控制器端点测试] ---")
    client = TestClient(app)

    # 1. 测试 SQL 审查端点 POST /api/v1/sql/audits
    audit_payload = {
        "sql_text": "CREATE TABLE `user` (`user_id` bigint, `price` double);",
        "db_type": "mysql",
        "user_roles": ["all_staff"]
    }
    resp = client.post("/api/v1/sql/audits", json=audit_payload)
    assert resp.status_code == 200, f"状态码异常: {resp.status_code}, 响应: {resp.text}"
    body = resp.json()
    assert body["code"] == 20000, f"业务状态码异常: {body}"
    assert "markdown_report" in body["data"]
    print("[PASS] HTTP 端点 POST /api/v1/sql/audits 请求成功，返回标准统一 ApiResponse 结构！")

    # 2. 测试规范问答端点 POST /api/v1/spec/queries
    query_payload = {
        "question": "规范中主键应该怎么定义？",
        "top_k": 3
    }
    resp = client.post("/api/v1/spec/queries", json=query_payload)
    assert resp.status_code == 200, f"状态码异常: {resp.status_code}"
    body = resp.json()
    assert body["code"] == 20000
    assert "markdown_content" in body["data"]
    print("[PASS] HTTP 端点 POST /api/v1/spec/queries 请求成功，问答数据结构完整！")


async def main():
    test_1_lost_in_the_middle_orchestration()
    test_2_double_check_anti_hallucination()
    await test_3_spec_query_e2e()
    await test_4_sql_audit_e2e()
    await test_4b_compliant_sql_positive()
    test_5_http_controller_endpoints()
    print("\n=======================================================")
    print(">>> 恭喜！第四与第五阶段：智能审查、正反例端到端测试全部通过！<<<")
    print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(main())
