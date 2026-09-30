# Orange Code 最小 code agent 评估

本文固化自 2026-09-29 的评估记录，描述的是当时仓库里的代码，不是改造之后的现状。对照目标：能完成基本改代码任务，可接本地或外部大模型，并挂上简单 MCP。源码审阅于 2026-09-29。

## 结论

当时不能当作可用的 coding agent。文档写成生产就绪，三条启动路径里有两条引用了不存在的符号。唯一能进到模型调用的路径，在执行工具时会抛异常，而且读文件不会把内容交回模型。

| 指标 | 数值 |
| --- | --- |
| 目标能力可用 | 0/3 |
| 闭环上的断点 | 8 |
| 互相冲突的入口 | 3 |
| MCP 实现 | 0 |

## 和目标的差距

源码：`orangecode.py`、`agent.py`、`tools.py`、`tool_executor.py`、`cli.py`。仓库内无 MCP 相关文件。

| 能力 | 最小形态 | 现状 | 判断 |
| --- | --- | --- | --- |
| 编码闭环 | 读文件、改文件、跑命令，多轮直到完成 | 提示词要求 JSON，解析后不回灌；工具不返回文件内容 | 阻断 |
| 本地模型 | Ollama 或任意 OpenAI 兼容地址 | 写死 ollama.Client 与 qwen2.5-coder:3b，默认主机 10.0.0.55 | 半成品 |
| 外部链接 | base_url + api_key 切换云端或网关 | 无 OpenAI 兼容客户端，无密钥配置 | 缺失 |
| 简单 MCP | 连接一个 stdio/HTTP server，把工具并入同一列表 | 仓库内没有 MCP 客户端或协议代码 | 缺失 |

## 闭环为什么断

期望路径是：用户请求 → 模型给出 tool call → 执行并把结果写回 messages → 模型继续，直到给出最终文本。当时每一步都有一处对不上。

| 位置 | 代码在做什么 | 结果 |
| --- | --- | --- |
| cli.py | import agent_no_rag | 模块不存在，命令入口直接失败 |
| agent.py main | AgentScheduler(...) | 类名是 OrangeCodeScheduler，Rich 入口无法启动 |
| 工具分发 | execute_tool_with_llm_* | ToolExecutor 没有这些方法；user_query、tool_name 未定义 |
| 工具契约 | await tool(**args) | 注册表存的是字典，函数是同步的，参数是 Pydantic 模型 |
| read_file | 返回成功字样 | 模型看不到文件正文，无法改代码 |
| 技能映射 | developer → DEVELOPER | 枚举不存在，退回 ALL_SKILLS 后工具列表为空 |
| 重试客户端 | self.retry_client | 只声明，从未调用 create_retry_aware_client |
| 对话续写 | Tool result 注释 | 工具结果没有追加进 messages，循环在第一轮结束 |

## 建议收成的结构

用一个 OpenAI 兼容客户端覆盖本地和外部模型。Ollama 自带 `/v1`，不需要第二套 SDK。MCP 只做客户端：发现工具，转成同一份 tools schema。

### llm.py

`chat(messages, tools)`。环境变量 `MODEL`、`BASE_URL`、`API_KEY`。超时与有限次重试放在这一层。

### agent.py

非流式循环。有 tool_calls 就执行并追加 `role=tool`；没有就返回文本。步数上限防止空转。

### tools + mcp

内置 read、write、list、shell。MCP stdio 进程的工具以 `mcp_` 前缀注册进同一张表。

### 一轮请求

用户消息 → chat + tools → 内置或 MCP → 结果写回 → 最终文本。

shell 保持确认或工作区限制。当时的确认逻辑只 print，subprocess 仍以 `shell=True` 直接执行。

## 先减再加

约 1600 行核心代码里，调度器、技能权限、流式面板和重试统计没有接到真正的模型调用上。最小 agent 不需要这些层。

| 动作 | 模块 | 原因 |
| --- | --- | --- |
| 保留并收薄 | retry.py 的退避 | 只包在 chat 请求上，删掉未使用的错误分类展示 |
| 保留并改写 | 五个内置工具 | 统一到一处，返回真实 stdout / 文件正文 |
| 保留 | AGENTS.md 项目说明 | 放进 system prompt 的前几百行即可 |
| 删掉 | 技能 × 权限矩阵 | 最小 agent 用一个工具白名单 |
| 删掉 | StreamingDisplayManager | 先把非流式闭环跑通 |
| 删掉 | utils.py 与 tools.py 的双份实现 | 文件操作只留一份 |
| 删掉 | extract_filename_from_code | 与 agent 循环无关 |
| 后置 | ESC 键盘线程 | 与 input() 抢 stdin，先用 Ctrl-C |

## 三步做到最小可用

| 步骤 | 主题 | 完成标准 |
| --- | --- | --- |
| 1 | 闭环 | 单一入口；OpenAI tools 格式的多轮循环，最多 8 步；read/write/list/shell 返回真实结果 |
| 2 | 模型 | 一个客户端：MODEL、BASE_URL、API_KEY。本地 Ollama 用 /v1，外部用同一协议 |
| 3 | MCP | 配置一个 stdio server，initialize + tools/list + tools/call，工具名加 mcp_ 前缀 |

MCP 做到这一步就够：配置一个命令，例如 uvx 启动的 filesystem server。启动时 `initialize` 和 `tools/list`，调用时 `tools/call`。不需要自己实现 MCP server，也不需要 resources 和 prompts。
