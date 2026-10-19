"""
MarkdownASTParser 逐步执行演练与输出演示 (Step-by-Step Execution Demo)
"""

import json
import re
import sys
import yaml

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

sample_markdown = """---
chunk_id: chunk_demo_order
heading_path: 数据库规范 > 订单系统规范 > 命名与数据类型
section: 订单系统规范
category: demo_rule
rule_type: naming_rule
keywords:
  - order_code
  - biz_id
---

## 订单系统规范与错误示范

1. 订单编号统一使用 `order_code` 命名
2. 业务主键统一命名为 `biz_id`，类型统一为 `BIGINT UNSIGNED`
3. 严禁使用浮点数 `double` 存储金额，必须使用 `decimal(20, 6)`
"""

print("=" * 70)
print("【原始输入文档片段 (包含标准 YAML Frontmatter 与 Markdown 正文)】:")
print(sample_markdown)
print("=" * 70)

# ---------------------------------------------------------
# 步骤 1: 扫描语法边界 (Pattern match)
# ---------------------------------------------------------
pattern = re.compile(r"(?:^|\n)---\s*\n(.*?)\n---\s*\n", re.DOTALL)
matches = list(pattern.finditer(sample_markdown))
print(f"\n>>> [步骤 1: 正则扫描边界]")
print(f"    - 探测到 {len(matches)} 个 Frontmatter 语法块")
match = matches[0]

raw_yaml = match.group(1).strip()
start_body = match.end()
end_body = len(sample_markdown)
body_text = sample_markdown[start_body:end_body].strip()

print(f"    - 提取出的原始 YAML 字符串:\n'''\n{raw_yaml}\n'''")
print(f"    - 提取出的纯正文 Body 字符区间: [{start_body} ~ {end_body}]")

# ---------------------------------------------------------
# 步骤 2: YAML 安全反序列化
# ---------------------------------------------------------
meta_dict = yaml.safe_load(raw_yaml)
print(f"\n>>> [步骤 2: 安全反序列化 YAML -> Python 字典 (meta_dict)]:")
print(json.dumps(meta_dict, ensure_ascii=False, indent=2))

# ---------------------------------------------------------
# 步骤 3: 提取与推导元数据
# ---------------------------------------------------------
chunk_id = meta_dict.get("chunk_id", "chunk_default")
section = meta_dict.get("section", "默认小节")
heading_path = meta_dict.get("heading_path", f"数据库规范 > {section}")
category = meta_dict.get("category", "general")
rule_type = meta_dict.get("rule_type", "general")

print(f"\n>>> [步骤 3: 提取与推导元数据字段 (ChunkMetadata)]:")
print(f"    chunk_id     = '{chunk_id}'")
print(f"    section      = '{section}'")
print(f"    heading_path = '{heading_path}'")
print(f"    category     = '{category}'")
print(f"    rule_type    = '{rule_type}'")

# ---------------------------------------------------------
# 步骤 4: BM25 专有名词关键词双重抽取
# ---------------------------------------------------------
declared_keywords = meta_dict.get("keywords", [])
inline_code_pattern = re.compile(r"`([^`\r\n]{2,60})`")
auto_keywords = inline_code_pattern.findall(body_text)

combined_keywords = []
seen = set()
for kw in declared_keywords + auto_keywords:
    clean = str(kw).strip()
    if clean.lower() not in seen:
        seen.add(clean.lower())
        combined_keywords.append(clean)

print(f"\n>>> [步骤 4: BM25 专有名词关键词双重抽取 (供稀疏倒排索引)]:")
print(f"    - 1. YAML Frontmatter 中显式声明的词: {declared_keywords}")
print(f"    - 2. 从正文反引号代码语法中自动抓取的词: {auto_keywords}")
print(f"    - 3. 最终合并去重后的完整词表 (共 {len(combined_keywords)} 个): {combined_keywords}")

# ---------------------------------------------------------
# 步骤 5: 双轨文本构建 (核心职责分离)
# ---------------------------------------------------------
display_text = body_text
embedding_text = f"【规范层级】{heading_path}\n{display_text}"

print(f"\n>>> [步骤 5: 双轨文本生成 (职责分离)]:")
print("\n" + "-" * 20 + " [轨 1: display_text (纯净正文)] " + "-" * 20)
print(display_text)
print("-" * 65)
print("【说明】给 DeepSeek 大模型阅读与前端 Web 渲染，绝无人工标签干扰。")

print("\n" + "-" * 20 + " [轨 2: embedding_text (语义检索钩子)] " + "-" * 20)
print(embedding_text)
print("-" * 65)
print("【说明】头部注入全局面包屑，专供 Ollama 计算高维向量，充当多维空间检索钩子。")

print("\n" + "=" * 70)
print(">>> [步骤 6: 组装完成的标准 Chunk 实体 (已就绪)]")
print(f"    Chunk(id='{chunk_id}', metadata={section}, keywords_count={len(combined_keywords)})")
print("=" * 70)
