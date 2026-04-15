# 安装指南

本文档详细说明如何安装和配置 hermes-feishu 插件。

## 前置条件

- **Python 3.10+**
- **Hermes Agent** 已安装并正常运行
- **飞书开放平台** 账号

## 第一步：创建飞书应用

### 1.1 登录飞书开放平台

访问 [飞书开放平台](https://open.feishu.cn/app) 并登录。

### 1.2 创建应用

1. 点击「创建企业自建应用」
2. 填写应用名称（如 `Hermes AI`）和描述
3. 记录 **App ID** 和 **App Secret**（在「凭证与基础信息」页面）

### 1.3 配置权限

在「权限管理」页面，搜索并开通以下权限：

| 权限 | 权限标识 |
| --- | --- |
| 获取与发送单聊、群组消息 | `im:message` |
| 以应用的身份发消息 | `im:message:send_as_bot` |
| 读取消息中的消息体内容 | `im:message:readonly` |

### 1.4 发布应用

1. 在「版本管理与发布」页面创建版本
2. 提交审核（企业内部应用通常自动通过）
3. 确认发布

## 第二步：配置事件订阅

如果你的 Hermes 飞书通道使用 Webhook 模式接收消息，确保事件订阅配置正确：

1. 在飞书应用「事件与回调」页面，配置请求地址 (Request URL) 指向 Hermes Gateway
2. 添加事件订阅：`接收消息 im.message.receive_v1`

## 第三步：安装插件

### 方式一：pip 安装（推荐）

```bash
pip install hermes-feishu
```

安装后 Hermes 会在下次启动时自动发现插件。

### 方式二：从源码安装（开发模式）

```bash
# 克隆仓库
git clone https://github.com/your-username/hermes-feishu.git
cd hermes-feishu

# 安装（开发模式，修改源码后立即生效）
pip install -e .
```

### 方式三：手动复制到 Hermes 插件目录

```bash
# 复制插件清单
mkdir -p ~/.hermes/plugins/hermes-feishu
cp plugin.yaml ~/.hermes/plugins/hermes-feishu/

# 复制源码
cp -r src/hermes_feishu/ ~/.hermes/plugins/hermes-feishu/
```

## 第四步：配置环境变量

### 4.1 获取凭证

在飞书开放平台 → 应用管理 → 凭证与基础信息 中获取：
- **App ID**（格式如 `cli_xxxxxxxxxxxx`）
- **App Secret**

### 4.2 设置环境变量

**Linux/macOS（~/.bashrc 或 ~/.zshrc）：**

```bash
export FEISHU_APP_ID="cli_xxxxxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxx"
```

**Windows（PowerShell）：**

```powershell
$env:FEISHU_APP_ID = "cli_xxxxxxxxxxxx"
$env:FEISHU_APP_SECRET = "xxxxxxxxxxxxxxxxxxxxxxxx"
```

### 4.3 使用 Hermes .env 文件（推荐）

在 `~/.hermes/.env` 中添加：

```env
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
```

Hermes 会自动加载 `.env` 文件中的变量。

## 第五步：启动验证

### 5.1 启动 Hermes

```bash
hermes
```

### 5.2 验证插件加载

在飞书中向机器人发送：

```
/plugins
```

确认输出中包含 `hermes-feishu` 插件，且 `send_feishu_card` 和 `send_feishu_table` 工具可用。

### 5.3 测试表格渲染

在飞书中发送：

```
帮我用表格展示一周天气数据
```

LLM 应该会调用 `send_feishu_table` 或 `send_feishu_card` 工具，你会在飞书中看到带颜色的卡片消息，表格使用飞书 Table 组件渲染。

## 故障排查

### 插件未加载

**症状**：`/plugins` 不显示 hermes-feishu

**排查**：
1. 确认安装成功：`pip show hermes-feishu`
2. 确认 entry-points 正确：`python -c "import importlib.metadata; print(importlib.metadata.entry_points(group='hermes_agent.plugins'))"`
3. 确认依赖已安装：`pip show lark-oapi`

### 工具不可用

**症状**：LLM 不使用卡片工具

**排查**：
1. 确认环境变量已设置：`echo $FEISHU_APP_ID`
2. 查看 Hermes 日志中是否有插件相关错误
3. 确认平台配置为 `feishu`（不是 `lark` 或其他）

### 发送失败

**症状**：工具被调用但消息未发送

**排查**：
1. 确认 App ID 和 Secret 正确
2. 确认应用已发布
3. 确认应用有 `im:message` 权限
4. 确认机器人已添加到目标群聊
5. 查看 Hermes 日志中的具体错误信息

### 表格不显示

**症状**：收到卡片但没有表格

**排查**：
1. 确认 Markdown 表格语法正确（需要表头行 + 分隔行 + 数据行）
2. 飞书 Table 组件有列数限制（建议不超过 20 列）
3. 检查卡片 JSON 是否正确构建（启用 debug 日志查看）

### 常见错误信息

| 错误 | 原因 | 解决方案 |
| --- | --- | --- |
| `Feishu credentials not configured` | 环境变量未设置 | 设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET |
| `lark-oapi package not installed` | 依赖缺失 | `pip install lark-oapi` |
| `Feishu API error: code=99991668` | 机器人不在群聊中 | 将机器人添加到群聊 |
| `Feishu API error: code=99991663` | 消息发送频率过高 | 等待后重试 |
| `Feishu API error: code=99991672` | 应用权限不足 | 在飞书开放平台开通 im:message 权限 |

## 卸载

```bash
pip uninstall hermes-feishu
```

然后重启 Hermes 即可。
