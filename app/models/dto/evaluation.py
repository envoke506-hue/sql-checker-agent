r"""
RAG 评测基准与数据权限领域 DTO (Evaluation & Security DTO)

【对应课件第 20 篇：RAG评测与数据权限】
1. 检索质量指标：Hit Rate@K, MRR@K, Context Precision;
2. 生成质量指标：忠实度 (Faithfulness), 违规检出率 (Recall/Precision/F1), 无答案拒答准确率;
3. 权限安全：基于 ACL 的前置检索过滤。
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class EvalSampleResult(BaseModel):
    """单个测试样本的评测明细"""
    sample_id: str = Field(..., description="测试样本唯一标识")
    query_text: str = Field(..., description="评测输入文本 (SQL 或自然语言问题)")
    sample_type: str = Field(..., description="样本类型: sql_audit / spec_query / unanswerable")
    
    # 检索侧评测结果
    golden_chunks: List[str] = Field(default_factory=list, description="标定的黄金切块 ID")
    retrieved_chunks: List[str] = Field(default_factory=list, description="实际召回的切块 ID")
    hit_rate: float = Field(..., description="Hit Rate 命中得分 (0.0 或 1.0)")
    reciprocal_rank: float = Field(..., description="倒数排名得分 (1/rank 或 0.0)")
    
    # 生成/审计侧评测结果
    passed_audit: bool = Field(..., description="审计判定或回答是否正确")
    faithfulness: float = Field(default=1.0, description="忠实度得分 (0.0 ~ 1.0)")
    remarks: str = Field(default="", description="评测诊断说明")


class MetricSummary(BaseModel):
    """各项宏观指标汇总"""
    # 1. 检索阶段指标
    total_samples: int = Field(..., description="总评测样本数")
    hit_rate_at_3: float = Field(..., description="Top-3 黄金切块命中率 (Hit Rate@3)")
    hit_rate_at_5: float = Field(..., description="Top-5 黄金切块命中率 (Hit Rate@5)")
    mrr_at_5: float = Field(..., description="平均倒数排名 (MRR@5)")
    
    # 2. 生成与审计阶段指标
    violation_detection_precision: float = Field(..., description="违规项检出精确率 (Precision)")
    violation_detection_recall: float = Field(..., description="违规项检出召回率 (Recall)")
    violation_detection_f1: float = Field(..., description="违规检出综合 F1 分数")
    hallucination_rejection_rate: float = Field(..., description="Double Check 幻觉拦截率")
    refusal_accuracy: float = Field(..., description="无答案拒答准确率 (知识库无依据时不胡编)")


class EvaluationRequest(BaseModel):
    """评测触发请求参数"""
    dataset_path: Optional[str] = Field(
        default="data/eval/golden_dataset.json",
        description="金标测试集路径 (相对或绝对路径)"
    )
    user_roles: List[str] = Field(
        default=["all_staff"],
        description="发起评测的用户角色，用于测试 ACL 前置权限隔离"
    )
    run_llm_generation: bool = Field(
        default=True,
        description="是否运行端到端大模型生成评测 (设为 False 时仅运行检索质量评测，耗时更短)"
    )


class EvaluationResponseData(BaseModel):
    """评测响应完整结果"""
    summary: MetricSummary = Field(..., description="指标汇总卡片")
    sample_details: List[EvalSampleResult] = Field(default_factory=list, description="逐题评测明细")
    markdown_report: str = Field(..., description="排版优美的基准评测报告 Markdown")
