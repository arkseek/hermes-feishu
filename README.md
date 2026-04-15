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
pip install hermes-feishu
```

### 3. 配置环境变量

```bash
export FEISHU_APP_ID="cli_xxxxxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxx"
```

或在 Hermes 的 `.env` 文件中添加：

```env
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. 重启 Hermes

```bash
hermes gateway restart
```

重启后使用 `/plugins` 命令确认插件已加载。

## 使用方式

插件加载后，LLM 在飞书平台上会自动收到格式化指令。当需要展示表格时，LLM 会自动调用 `send_feishu_card` 或 `send_feishu_table` 工具。

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
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 运行测试（带覆盖率）
pytest tests/ -v --cov=hermes_feishu
```

## 许可证

MIT License
