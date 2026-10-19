# 切块详情: chunk_framework_mybatis

## 一、元数据 (Metadata)
- **切块 ID**: chunk_framework_mybatis
- **面包屑层级路径**: 数据库规范 > 建表规范 > 框架主键实现与依赖
- **所属小节**: 框架实现
- **规则分类**: framework
- **细分类型**: code_sample
- **ACL 访问控制**: ['all_staff']

## 二、专有名词与关键词 (Keywords - 供 BM25 稀疏检索)
[
  "IdWorker",
  "IdWorker.getId()",
  "IdWorker.getIdStr()",
  "ASSIGN_ID",
  "TableId",
  "mybatis-plus",
  "mybatis-plus-boot-starter",
  "雪花算法"
]

## 三、供大模型与前端阅读的纯净正文 (display_text)
`markdown
## 框架主键实现规范 (雪花算法代码与依赖)

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
`

## 四、供向量模型计算的增强文本 (embedding_text)
`	ext
【规范层级】数据库规范 > 建表规范 > 框架主键实现与依赖
## 框架主键实现规范 (雪花算法代码与依赖)

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
`
