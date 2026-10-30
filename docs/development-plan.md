# Orange Code 开发计划

本文把 `docs/industrial-remediation.md` 拆成实施任务。方案里的默认决定（shell 策略、检查时机、字符预算、会话和快照位置）在这里不再重开。日期是 2026-10-29。

## 顺序

四步串行。前一步的新增测试和原有 `python3 -m pytest` 都通过，再开始下一步。

```text
1 不越界、不卡死
    → 2 改完自检
        → 3 长任务可恢复
            → 4 可撤销、可观测、可配置
```

结构保持五个入口模块。第 3 步可以新增 `session.py`，第 4 步可以新增 `snapshot.py` 和 `config.py`。三个新模块只做文件和配置，工具循环仍在 `agent.py`。

每项任务的测试使用脚本化模型或假 MCP 进程，不连接真实模型。工具错误继续返回以 `Error:` 开头的文本。

## 第一步：不越界、不卡死

目标：未授权的命令不执行，密钥不被读走，MCP 超时会返回，中断后的消息仍然合法。

| 编号 | 任务 | 主要文件 | 测试 |
| --- | --- | --- | --- |
| 1.1 | 路径拒绝。`.env`、`.env.*`、`.netrc`、`id_rsa`、`id_dsa`、`credentials.json`，后缀 `.pem`、`.key`、`.p12`、`.pfx`，以及路径中的 `.git`、`.orangecode`。读、写、改返回错误；`search` 跳过 | `tools.py` | 读取 `.env` 得到错误；搜索结果里没有 `.env` 的行；写入 `.git/config` 得到错误 |
| 1.2 | `SHELL=ask\|allow\|deny`。交互默认 `ask`，单次任务默认 `deny`。`CONFIRM_SHELL=1` 视为 `ask`，`CONFIRM_SHELL=0` 视为 `allow`，`SHELL` 优先。无终端的 `ask` 按拒绝处理 | `tools.py`、`orangecode.py` | 单次任务路径下 shell 不执行并返回错误；`SHELL=allow` 才执行；交互用假的 confirmer，拒绝时命令不跑 |
| 1.3 | `write_file` 和 `edit_file` 写临时文件后替换 | `tools.py` | 替换后内容正确；目标的父目录里不留下临时文件 |
| 1.4 | MCP 读响应超时，默认 30 秒，`MCP_TIMEOUT` 可调，上限 120 秒。排空 stderr | `mcp_client.py` | 假服务只写 stderr 或不回答时，调用在超时内返回 `Error:`，进程被关掉 |
| 1.5 | 工具执行中断时，为尚未写回的 tool call 补 `Error: interrupted`，`run` 返回 `Interrupted.` | `agent.py` | 脚本化工具在第一次调用时抛出 `KeyboardInterrupt`，消息里助手的每个 tool call 都有 tool 结果 |
| 1.6 | 对齐文档。`AGENTS.md` 写上六个工具和 shell 策略。`README.md` 写上 `SHELL`、路径拒绝，并说明 shell 不是沙箱。删掉 `tests/main.py` 和 `tests/setup.py`。`tests/run.sh` 的注释改为当前入口 | `AGENTS.md`、`README.md`、`tests/` | `test_environment.py` 仍确认核心模块存在；文档任务不另写断言 |

1.2 要改 `orangecode.py` 把「这次是单次任务还是交互」传给 `ToolRegistry`。现有 `CONFIRM_SHELL` 测试保持通过：确认回调返回假时，命令不执行。

这一步的完成标准：

- `python3 -m pytest` 通过，包含上表的新测试
- 未设置 `SHELL` 时，`python3 orangecode.py "跑命令"` 这条路径上的 `execute_shell` 返回错误且不启动子进程
- 假 MCP 不回答时，`call` 在超时内返回错误

## 第二步：改完自检

目标：模型声明做完之后，配置了的检查若失败，输出会回到循环。超过 400 行的文件不能整文件读取。

| 编号 | 任务 | 主要文件 | 测试 |
| --- | --- | --- | --- |
| 2.1 | 成功的 `write_file`、`edit_file` 把相对路径记入本轮集合。新的用户请求开始时清空 | `agent.py`、`tools.py` | 读文件和失败的编辑不记入；成功编辑记入 |
| 2.2 | 模型返回纯文本、本轮有写入、且 `CHECK_COMMAND` 非空时执行该命令。退出码为 0 则把模型文本返回给用户。非 0 则追加 user 消息并继续，占用一步。命令不走 shell 确认，超时 120 秒，输出超过 2 万字符则截断 | `agent.py` | 脚本化模型先写文件再给出最终文本。检查命令退出码非 0 时，下一次 `chat` 的消息里有该输出，并且循环还会再请求模型。退出码为 0 时不再追加。未设置 `CHECK_COMMAND` 时行为与现在相同 |
| 2.3 | 未传行号且超过 400 行时，`read_file` 返回错误和总行数，不返回正文。传了行号时保持现在的切片行为 | `tools.py` | 401 行文件的整文件读取以 `Error:` 开头；同一文件 `start_line=1`、`end_line=20` 返回带行号的正文 |
| 2.4 | README 和 `AGENTS.md` 写上 `CHECK_COMMAND`，以及整文件读取的行数上限 | `README.md`、`AGENTS.md` | 无单独测试 |

检查只在模型准备结束时跑一次，不在每次写入后跑。避免一步编辑就花掉整个 `MAX_STEPS`。

这一步的完成标准：

- 新增的 agent 测试在不连接模型的情况下覆盖「检查失败则继续、检查成功则停止、未配置则不跑」
- 原有「读文件内容回到模型」的测试仍然通过

## 第三步：长任务可恢复

目标：发出去的非 system 内容有字符上限。进程退出后可以用会话号接着聊。

| 编号 | 任务 | 主要文件 | 测试 |
| --- | --- | --- | --- |
| 3.1 | `chat` 前按 `MESSAGE_CHAR_BUDGET` 裁剪，默认 24000。先把最早的 tool 正文换成带原始长度的占位，再缩短更早的 user / assistant 正文。保留 system 和最后一条 user | 新的裁剪函数，由 `agent.py` 调用 | 构造超过预算的历史后，送入 `chat` 的字符数不超过预算；最后一条 user 原文还在；被裁的 tool 消息仍是 `role=tool` |
| 3.2 | 每轮结束后把消息写入 `.orangecode/sessions/<id>.jsonl`。`.gitignore` 忽略 `.orangecode/` | 新的 `session.py`，`orangecode.py` 调用 | 跑完一轮后文件存在，读回的消息与内存一致 |
| 3.3 | `python3 orangecode.py --resume <id>` 从该文件恢复后再接受新请求。交互命令 `resume` 恢复最近一次 | `orangecode.py`、`session.py` | 写入会话、新建 `Agent`、恢复后，历史里有上一轮的 user 文本 |

裁剪发生在发请求前的副本上。落盘的会话保留完整消息，方便恢复后仍能看到工具结果。恢复之后的下一轮请求再按预算裁剪。

这一步的完成标准：

- 预算测试不依赖真实模型
- 用临时目录做会话目录，测试不在仓库里留下 `.orangecode/`

## 第四步：可撤销、可观测、可配置

目标：最近一次请求的文件改动可以还原。用户看得到工具轨迹。项目可以用 toml 固定常用设置。

| 编号 | 任务 | 主要文件 | 测试 |
| --- | --- | --- | --- |
| 4.1 | 本轮第一次改某个已存在文件前，把原字节拷到 `.orangecode/snapshots/<turn-id>/`。新文件在清单里记为创建 | 新的 `snapshot.py`，`tools.py` 或 `agent.py` 在写入前调用 | 改已有文件后快照内容是旧正文；新建文件在清单里标记为创建 |
| 4.2 | 交互命令 `undo`，以及 `python3 orangecode.py --undo`。恢复最近一次请求：写回旧内容，删除本次新建的文件。不执行 git | `snapshot.py`、`orangecode.py` | 改文件并新建文件后 undo，旧文件回到原内容，新文件消失 |
| 4.3 | 工具开始和结束向 stderr 各打一行。`TRACE=0` 关闭。stdout 仍是最终回答 | `agent.py` | 捕获 stderr，其中有工具名；`TRACE=0` 时没有这行 |
| 4.4 | 读取工作区根的 `orangecode.toml`：`model`、`base_url`、`max_steps`、`check_command`、`shell`、`mcp_command`。环境变量覆盖文件中的同名项。不从文件读 API key | 新的 `config.py`，`agent.py`、`llm.py`、`orangecode.py` | 临时目录里的 toml 改变模型名；同时设置 `MODEL` 时环境变量胜出 |
| 4.5 | README 写 toml 字段、`undo`、`TRACE`。给一份 `orangecode.toml` 的例子，不把含密钥的文件提交进仓库 | `README.md` | 无单独测试 |

快照目录沿用第 3 步的 `.gitignore` 规则。

这一步的完成标准：

- undo 测试使用临时工作区，不改动本仓库的源文件
- `python3 orangecode.py --config` 在存在 toml 时打印文件里的模型名，环境变量设置后打印环境变量的值

## 建议的提交切分

每步内部按任务提交，消息说明原因。可以合并同一文件里紧挨着的测试和实现，不要把四步合成一个提交。

| 提交 | 内容 |
| --- | --- |
| 1.1–1.3 | 路径拒绝、shell 策略、原子写，加工具测试 |
| 1.4 | MCP 超时和 stderr 排空，加 MCP 测试 |
| 1.5 | 中断后补齐 tool 消息，加循环测试 |
| 1.6 | 文档和过时测试脚本 |
| 2.1–2.2 | 写入记录和检查命令 |
| 2.3–2.4 | 大文件拒绝整读，以及文档 |
| 3.1 | 请求前裁剪 |
| 3.2–3.3 | 会话落盘和恢复 |
| 4.1–4.2 | 快照和 undo |
| 4.3 | stderr 轨迹 |
| 4.4–4.5 | toml 和 README |

## 完成时的仓库状态

四步都做完时，下面的命令和文件应当成立：

```bash
python3 -m pytest
```

- `SHELL` 未设置时，单次任务不能跑 shell；交互会确认
- `CHECK_COMMAND` 设置后，改动文件且检查失败时，模型还会再被调用
- `.orangecode/` 被 git 忽略，会话和快照都在其中
- `orangecode.toml` 能设置模型、步数、检查命令、shell 和 MCP，环境变量可以盖过它
- `AGENTS.md` 与 README 描述的工具和行为与代码一致

持续集成、多个 MCP、Plan 模式和操作系统级沙箱不在这四步里。第一步的 README 需要写明 shell 仍不是沙箱。
