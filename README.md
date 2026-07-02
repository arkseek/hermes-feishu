# hermes-feishu

增强 Hermes Agent 飞书消息通道，支持卡片消息和表格渲染。

## 问题背景

Hermes Agent 内置的飞书通道使用 `post` 消息类型 + `tag: "md"` 发送 Markdown 内容。但飞书的 Markdown 组件仅支持语法子集，**不支持表格语法** (`| col | col |`)。这导致 LLM 生成的表格在飞书中无法正常渲染。

## 解决方案

本插件通过以下方式解决：

1. **`send_feishu_card` 工具** — 发送包含表格的飞书卡片消息。自动检测 Markdown 中的表格语法，转换为飞书卡片 Table 组件。
2. **`send_feishu_table` 工具** — 直接发送结构化表格数据（headers + rows）。
3. **`pre_llm_call` 钩子** — 当平台为飞书时，自动注入格式化指令，引导 LLM 使用卡片工具发送表格。

## 快速安装

### 1. 环境准备

- Python 3.10+
- Hermes Agent 已安装并配置飞书平台
- 飞书开放平台应用（需要 App ID 和 App Secret）

### 2. 安装插件

```bash
hermes plugins install arkseek/hermes-feishu
```

### 3. 配置环境变量

**⚠️ 重要：凭证必须配置在 `~/.hermes/.env` 文件中，否则插件工具不会加载。**

```bash
# 编辑 Hermes 环境变量文件
nano ~/.hermes/.env

# 添加以下内容
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx

# 可选：设置默认 chat_id（用于 Hermes 未传递 chat_id 的情况）
# HERMES_FEISHU_CHAT_ID=oc_xxxxxxxxxxxxxxxxxxxxxxxx
```

#### 关于 HERMES_FEISHU_CHAT_ID

Hermes Agent 目前存在一个已知问题：`pre_llm_call` 钩子不会传递 `chat_id` 参数给插件（尽管 Hermes 内部拥有该信息）。这导致插件无法自动确定目标会话。

**临时解决方案**：
- 在 `.env` 中设置 `HERMES_FEISHU_CHAT_ID`，插件会在找不到 chat_id 时使用该默认值
- 适用于单会话场景（例如只在特定群组中使用）
- 多会话场景下，建议向 Hermes 提交 Issue 请求修复

**如何获取 chat_id**：
1. 在飞书中发送消息给机器人
2. 查看 Hermes gateway 日志，搜索 `inbound message` 日志
3. 日志中的 `chat=oc_xxx` 即为 chat_id

### 4. 重启 Hermes

```bash
hermes gateway restart
```

重启后使用 `/plugins` 命令确认插件已加载。

## 使用方式

插件加载后，LLM 在飞书平台上会自动收到格式化指令。当需要展示表格时，LLM 会自动调用 `send_feishu_card` 或 `send_feishu_table` 工具。

### 工具参数

#### `send_feishu_card`

发送富文本卡片消息,支持 Markdown 内容和表格。

**参数:**
- `content` (必填): Markdown 内容,可包含表格
- `title` (可选): 卡片标题
- `chat_id` (可选): 目标会话 ID (通常自动检测)
- `template` (可选): 卡片配色模板 (默认: `blue`)
- `reaction` (可选): 发送后添加的表情反应 (例如: `👍`, `✅`, `🎉`)

**示例:**
```json
{
  "content": "| 姓名 | 年龄 |\n| --- | --- |\n| 张三 | 25 |\n| 李四 | 30 |",
  "title": "📊 数据表格",
  "template": "blue",
  "reaction": "✅"
}
```

#### `send_feishu_table`

发送结构化表格数据。

**参数:**
- `headers` (必填): 列标题数组
- `rows` (必填): 数据行数组
- `title` (可选): 卡片标题
- `chat_id` (可选): 目标会话 ID
- `template` (可选): 卡片配色模板
- `reaction` (可选): 发送后添加的表情反应

**示例:**
```json
{
  "headers": ["姓名", "年龄"],
  "rows": [["张三", "25"], ["李四", "30"]],
  "title": "📊 数据表格",
  "reaction": "👍"
}
```

### 示例：Markdown 表格

LLM 生成包含表格的内容时会自动调用：

```
用户: 帮我对比一下这两个方案

LLM 调用 send_feishu_card:
  content: |
    | 对比项 | 方案A | 方案B |
    | --- | --- | --- |
    | 成本 | ¥1000 | ¥2000 |
    | 周期 | 2周 | 1周 |
    | 风险 | 低 | 中 |
```

飞书中会渲染为带颜色标题的卡片消息，表格使用飞书 Table 组件。

### 示例：结构化表格

LLM 可以直接使用结构化数据：

```
LLM 调用 send_feishu_table:
  headers: ["指标", "当前值", "目标值"]
  rows: [
    ["日活用户", "10,000", "15,000"],
    ["转化率", "3.2%", "5%"],
    ["NPS", "42", "60"]
  ]
```

### 示例：X/Twitter 监控摘要

如果 Hermes 同时安装 [Hermes Tweet](https://github.com/Xquik-dev/hermes-tweet)，可以先让代理读取 X/Twitter 账号、帖子或趋势，再用本插件把结果发送为飞书卡片表格：

```json
{
  "headers": ["来源", "内容", "建议动作"],
  "rows": [
    ["@example", "新品发布被 3 个行业账号转发", "整理复盘"],
    ["关键词", "品牌词讨论量上升", "继续观察"]
  ],
  "title": "X/Twitter 监控摘要",
  "template": "blue"
}
```

这样飞书群内能直接看到结构化摘要，而 X/Twitter 的读取或动作权限仍由 Hermes Tweet 的配置控制。

## 插件架构

```
src/hermes_feishu/
├── __init__.py      # 插件注册：工具 + 钩子
├── schemas.py       # 工具 Schema 定义
├── tools.py         # 工具处理器
├── card_builder.py  # 飞书卡片 JSON 构建
├── table_parser.py  # Markdown 表格解析
└── sender.py        # 飞书 API 发送层
```

## 飞书应用权限

插件需要以下飞书应用权限：

| 权限 | 权限标识 | 用途 |
| --- | --- | --- |
| 获取与发送单聊、群组消息 | `im:message` | 发送卡片消息 |
| 读取消息中的消息体内容 | `im:message:readonly` | 读取消息内容 |

## 开发

```bash
# 克隆仓库
git clone https://github.com/arkseek/hermes-feishu.git
cd hermes-feishu

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 运行测试（带覆盖率）
pytest tests/ -v --cov=hermes_feishu
```

## 许可证

MIT License

## 更新日志

### v0.4.0 (2026-04-15)

**新功能**
- ✨ 添加消息 Reaction 支持：工具支持 `reaction` 参数，发送成功后自动添加表情反应
- 🔧 添加 `HERMES_FEISHU_CHAT_ID` 环境变量回退，解决 Hermes 未传递 chat_id 的问题

**Bug 修复**
- 🐛 修复飞书 Table 组件格式错误，正确使用字典列表格式
- 🐛 修复表格渲染失败问题（"table rows is invalid" 错误）

**改进**
- 📝 完善 README 文档，添加环境变量配置说明
- 🎨 改进错误消息，提供明确的解决方案

### v0.3.6 (之前)

- 初始版本
- 实现基本的卡片消息和表格渲染功能
