r"""
SQL 规范合规审查标准 Markdown 报告渲染器 (Audit Report Renderer)

【职责说明】
- 遵循 MVC 架构中的 View 渲染职责；
- 将审核结果（得分、违规项、重构 SQL、依据引用）渲染为排版优美、结构标准的企业级 Markdown 报告。
"""

from typing import List
from app.models.dto.sql_audit import CitationDetail, ViolationDetail


class AuditReportRenderer:
    """
    负责将 SQL 审查结果格式化为标准 Markdown 报告
    """

    @staticmethod
    def render(
        is_compliant: bool,
        score: int,
        summary: str,
        violations: List[ViolationDetail],
        suggested_sql: str,
        citations: List[CitationDetail],
        original_sql: str,
    ) -> str:
        """
        组装企业级标准 Markdown 报告
        """
        # 1. 状态 Badge 与图标
        status_badge = "✅ **完全合规 (通过)**" if is_compliant else "❌ **存在不符合规范项 (需整改)**"
        
        # 统计严重级别
        error_count = sum(1 for v in violations if v.severity.upper() == "ERROR")
        warn_count = sum(1 for v in violations if v.severity.upper() == "WARN")

        lines: List[str] = [
            "# 📋 数据库设计规范合规审查报告",
            "",
            "## 1. 审查总览看板",
            "| 审查指标 | 评估结果 |",
            "| :--- | :--- |",
            f"| **合规状态** | {status_badge} |",
            f"| **合规健康得分** | **{score} / 100** |",
            f"| **违规统计** | 发现 **{len(violations)}** 处违规 (严重阻断 ERROR: `{error_count}` 项, 建议优化 WARN: `{warn_count}` 项) |",
            f"| **审计总评** | {summary} |",
            "",
        ]

        # 2. 原始输入 SQL
        lines.extend([
            "## 2. 待审查原始 SQL",
            "```sql",
            original_sql.strip(),
            "```",
            "",
        ])

        # 3. 违规项明细对照表
        lines.append("## 3. 违规明细对照与整改建议")
        if not violations:
            lines.extend([
                "> 🎉 **太棒了！该 SQL 语句完全符合《数据库规范》各项设计标准，未发现违规或不推荐写法。**",
                "",
            ])
        else:
            lines.extend([
                "| 序号 | 违规对象 / 片段 | 命中规范规则 | 级别 | 规范依据 | 违规分析与整改建议 |",
                "| :---: | :--- | :--- | :---: | :---: | :--- |",
            ])
            for idx, v in enumerate(violations, start=1):
                sev_icon = "🔴 ERROR" if v.severity.upper() == "ERROR" else "🟡 WARN"
                target = f"`{v.target_object}`" if v.target_object else "-"
                citation_tag = f"[{v.citation_index}]"
                fix_desc = v.description
                if hasattr(v, "suggested_fix") and v.suggested_fix:
                    fix_desc += f"<br>💡 **修改建议**: {v.suggested_fix}"
                
                # 转义表格中的换行与管道符
                clean_desc = fix_desc.replace("\n", " ").replace("|", "\\|")
                lines.append(f"| {idx} | {target} | {v.rule_name} | {sev_icon} | {citation_tag} | {clean_desc} |")
            lines.append("")

        # 4. 标准合规重构 SQL
        lines.extend([
            "## 4. 推荐合规重构 SQL",
            "> 提示：以下重构 SQL 严格依据规范模板注入 7 大通用审计字段、修正数据类型、消除外键约束并统一命名。",
            "```sql",
            suggested_sql.strip(),
            "```",
            "",
        ])

        # 5. 规范依据附录溯源
        lines.append("## 5. 本次审查引用的规范依据清单")
        if not citations:
            lines.append("> 本次审查未调用外置规范条款。")
        else:
            for c in citations:
                lines.extend([
                    f"- **[{c.index}] {c.title}** (来源文档: `{c.source_file}`)",
                    f"  > 📖 **条款关键摘录**: {c.snippet}",
                ])

        lines.append("")
        lines.append("---")
        lines.append("*报告由 基于 RAG 的智能 SQL 规范审查系统 自动生成*")

        return "\n".join(lines)
