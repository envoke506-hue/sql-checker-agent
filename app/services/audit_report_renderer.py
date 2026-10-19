r"""
SQL 规范合规审查精简 Markdown 渲染器 (Audit Report Renderer)

【职责说明】
- 遵循 MVC 架构中的 View 渲染职责；
- 只渲染答复必需的三类内容，避免冗长排版：
  1. 不满足项明细（每条均带 [n] 编号引用依据）；
  2. 每一项对应的整改方案；
  3. 修改后的合规 SQL。
"""

from typing import Dict, List
from app.models.dto.sql_audit import CitationDetail, ViolationDetail


class AuditReportRenderer:
    """
    负责将 SQL 审查结果格式化为精简的 Markdown 整改答复
    """

    @staticmethod
    def render(
        is_compliant: bool,
        score: int,
        violations: List[ViolationDetail],
        suggested_sql: str,
        citations: List[CitationDetail],
    ) -> str:
        """
        组装只包含「不满足项 + 整改方案 + 修改后的 SQL」的 Markdown 回复
        """
        if is_compliant or not violations:
            return f"✅ **未发现不满足项，SQL 完全合规**（合规得分 **{score} / 100**）"

        # 编号引用依据映射: [n] -> 规范章节标题，便于读者回溯条款出处
        citation_titles: Dict[int, str] = {c.index: c.title for c in citations}

        lines: List[str] = [f"### ⚠️ 不满足项与整改方案（共 {len(violations)} 项）", ""]
        for idx, v in enumerate(violations, start=1):
            severity = "🔴 ERROR" if v.severity.upper() == "ERROR" else "🟡 WARN"
            title = citation_titles.get(v.citation_index, "")
            basis = f"[{v.citation_index}]" + (f" {title}" if title else "")

            lines.append(f"**{idx}. {v.rule_name}** · {severity} · 依据：{basis}")
            if v.target_object:
                lines.append(f"- 不满足片段：`{v.target_object}`")
            if v.description:
                lines.append(f"- 问题说明：{v.description}")
            lines.append(f"- 整改方案：{v.suggested_fix or '参照下方修改后的 SQL 调整该片段'}")
            lines.append("")

        lines.extend([
            "### ✅ 修改后的 SQL",
            "```sql",
            suggested_sql.strip(),
            "```",
        ])

        return "\n".join(lines)
