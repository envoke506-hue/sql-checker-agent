# 切块详情: chunk_terminology

## 一、元数据 (Metadata)
- **切块 ID**: chunk_terminology
- **面包屑层级路径**: 数据库规范 > 名词术语 > 标准命名单词字典
- **所属小节**: 名词术语
- **规则分类**: terminology
- **细分类型**: glossary
- **ACL 访问控制**: ['all_staff']

## 二、专有名词与关键词 (Keywords - 供 BM25 稀疏检索)
[
  "id",
  "name",
  "code",
  "type",
  "sort",
  "parent",
  "status",
  "remark",
  "audit",
  "create",
  "modify",
  "expire",
  "tag",
  "url",
  "source",
  "time",
  "info",
  "version",
  "deleted",
  "disabled",
  "relation",
  "path",
  "username",
  "password",
  "nick",
  "email",
  "gender",
  "birthday",
  "role",
  "duty",
  "dept",
  "order",
  "pay",
  "organ",
  "company",
  "goods",
  "province",
  "city",
  "district",
  "address",
  "zip",
  "contact",
  "mobile"
]

## 三、供大模型与前端阅读的纯净正文 (display_text)
`markdown
## 名词术语 (数据库设计首选推荐单词或组合单词)

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
`

## 四、供向量模型计算的增强文本 (embedding_text)
`	ext
【规范层级】数据库规范 > 名词术语 > 标准命名单词字典
## 名词术语 (数据库设计首选推荐单词或组合单词)

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
`
