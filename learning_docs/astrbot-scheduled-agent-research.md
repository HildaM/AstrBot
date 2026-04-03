# AstrBot 定时任务 Agent 可行性调研报告

## 一、需求概述

构建一个**定时任务 Agent**，每天自动执行以下工作流：

1. **信息收集**：联网搜索"鸣潮"官方资讯、二创视频剧情、二创故事等
2. **剧本创作**：结合官方人物故事/主线剧情，创作"明天"的 2-3 个故事剧本
3. **文件管理**：创建以 `【Daily Auto】` 为前缀的文件夹存储剧本
4. **视频提示词生成**：使用 seedance skill 辅助生成剧本
5. **分镜图创作**：使用 storyboard-quartet skill 创作分镜文档
6. **Git 同步**：将 `wuwa-video` 内容提交并推送到远程仓库

### 核心能力需求

| # | 能力 | 描述 |
|---|------|------|
| 1 | 工作区隔离 | 在指定工作区执行，不影响其他文件 |
| 2 | 工具执行能力 | 联网查询、文件创建、Git 操作 |
| 3 | 定时任务执行 | 按日调度，自动触发 |
| 4 | 长时间任务执行 | 合理的任务规划与多步骤执行 |
| 5 | 记忆管理 | 跨执行的上下文积累与回忆 |

---

## 二、AstrBot 架构速览

```
main.py → InitialLoader → AstrBotCoreLifecycle
  ├── EventBus ← EventQueue ← PlatformManager (各平台适配器)
  │     └── PipelineScheduler (9 阶段洋葱模型)
  │           └── ProcessStage → build_main_agent() → ToolLoopAgentRunner
  ├── CronJobManager (APScheduler)
  │     └── _woke_main_agent() → build_main_agent() → runner.step_until_done(30)
  ├── PluginManager (Star 插件系统)
  ├── ConversationManager (对话/记忆管理)
  ├── ProviderManager (多 LLM 供应商)
  ├── SubAgentOrchestrator (子 Agent 编排 / HandoffTool)
  ├── KnowledgeBaseManager (知识库 / 向量检索)
  └── Context (统一接口上下文)
```

---

## 三、五大能力逐项分析

### 3.1 工作区隔离 ✅ 基本满足，需适配

**现状分析：**

AstrBot 的工作区概念体现在以下几个层面：

- **会话隔离**（`unified_msg_origin`）：每个消息来源（`platform:type:session_id`）有独立的对话上下文和工具集
- **沙箱环境**（`computer/`）：支持 `local` 和 `sandbox` 两种运行时，`sandbox` 模式下 Shell/Python 命令在隔离容器中执行
- **文件路径管理**：通过 `astrbot.core.utils.path_utils` 提供统一的数据目录、临时目录管理

**核心代码：**

| 文件 | 关键类/函数 | 作用 |
|------|------------|------|
| `astrbot/core/astr_main_agent.py` | `MainAgentBuildConfig.computer_use_runtime` | 控制运行时: `none` / `local` / `sandbox` |
| `astrbot/core/computer/computer_client.py` | `get_booter()` | 获取沙箱 Shell 客户端 |
| `astrbot/core/astr_main_agent_resources.py` | `ExecuteShellTool` / `PythonTool` | Shell/Python 工具（区分 local 和 sandbox） |

**评估：**

- ✅ `sandbox` 模式天然隔离，Shell/Python 操作在容器中执行
- ✅ `local` 模式下也可通过配置 `cwd` 限制操作目录
- ⚠️ **但**：定时任务唤醒 Agent 时（`_woke_main_agent`），默认不会设定独立工作目录，Shell 工具的 `cwd` 需要在 System Prompt 或工具参数中明确指定
- 🔧 **建议**：在 Cron 任务的 `payload` 中增加 `workspace` 字段，唤醒时注入到 Agent 的 System Prompt 中

---

### 3.2 工具执行能力 ✅ 满足

AstrBot 拥有丰富的内置工具和扩展机制：

#### 3.2.1 内置工具清单

| 工具 | 代码位置 | 能力 |
|------|---------|------|
| `ExecuteShellTool` | `astrbot/core/computer/tools/` | Shell 命令执行（支持 git 操作） |
| `PythonTool` / `LocalPythonTool` | 同上 | Python 代码执行 |
| `BrowserExecTool` / `BrowserBatchExecTool` | 同上 | 浏览器自动化（联网信息收集） |
| `FileUploadTool` / `FileDownloadTool` | 同上 | 文件上传/下载 |
| `SendMessageToUserTool` | `astrbot/core/astr_main_agent_resources.py` | 主动发送消息给用户 |
| `KnowledgeBaseQueryTool` | 同上 | 知识库查询 |
| `CreateActiveCronTool` | `astrbot/core/tools/cron_tools.py` | 创建定时任务 |

#### 3.2.2 MCP 扩展工具

| 代码位置 | 能力 |
|---------|------|
| `astrbot/core/agent/mcp_client.py` | 完整 MCP 客户端，支持 stdio/SSE/StreamableHTTP |
| `astrbot/core/provider/func_tool_manager.py` | MCP 工具管理器，自动发现和注册 |

#### 3.2.3 联网搜索能力

- ✅ 浏览器工具（`BrowserExecTool`）支持网页访问和信息提取
- ✅ 可通过 MCP 接入 `web_search_tavily` / `web_search_bocha` 等搜索工具
- ✅ Agent Hooks 中已有对搜索结果的引用格式处理（见 `astr_agent_hooks.py:58-81`）

#### 3.2.4 Git 操作能力

- ✅ 通过 `ExecuteShellTool` 直接执行 `git add`、`git commit`、`git push` 等命令
- ✅ 支持 local 和 sandbox 两种模式

**评估：** 工具层面完全满足需求。联网、文件操作、Git 都有现成的工具支持。

---

### 3.3 定时任务执行能力 ✅ 满足

**这是 AstrBot 的核心特性之一，已经有完整的实现。**

#### 3.3.1 定时任务系统架构

```
CronJobManager (基于 APScheduler)
  ├── add_basic_job()        → 简单回调
  ├── add_active_job()       → 主动唤醒 Agent
  └── _woke_main_agent()     → 构建完整 Agent 并执行
       ├── CronMessageEvent  → 合成消息事件
       ├── build_main_agent() → 构建 Agent
       ├── runner.step_until_done(30) → 最多 30 步自主执行
       └── persist_agent_history()    → 保存执行记录
```

#### 3.3.2 关键代码路径

| 文件 | 关键类/函数 | 作用 |
|------|------------|------|
| `astrbot/core/cron/manager.py` | `CronJobManager` | 定时任务管理器（APScheduler 封装） |
| `astrbot/core/cron/manager.py:91-120` | `add_active_job()` | 添加主动 Agent 定时任务 |
| `astrbot/core/cron/manager.py:234-262` | `_run_active_agent_job()` | 触发 Agent 执行 |
| `astrbot/core/cron/manager.py:263-378` | `_woke_main_agent()` | **核心**：构建并运行 Agent |
| `astrbot/core/cron/events.py` | `CronMessageEvent` | 定时任务触发的合成消息事件 |
| `astrbot/core/tools/cron_tools.py` | `CreateActiveCronTool` | LLM 可自主创建定时任务的工具 |
| `astrbot/core/astr_main_agent_resources.py:113-129` | `PROACTIVE_AGENT_CRON_WOKE_SYSTEM_PROMPT` | 定时唤醒时的专用 System Prompt |

#### 3.3.3 创建定时任务的两种方式

1. **LLM 自主创建**：通过 `create_future_task` 工具，Agent 可在对话中自行创建定时任务
2. **API 创建**：通过 Dashboard API 直接创建

#### 3.3.4 执行流程详解

```python
# astrbot/core/cron/manager.py:263-378
async def _woke_main_agent(self, *, message, session_str, extras):
    # 1. 构造 CronMessageEvent（模拟用户消息）
    cron_event = CronMessageEvent(context=self.ctx, session=session, ...)
    
    # 2. 加载历史对话上下文
    conv = await _get_session_conv(event=cron_event, plugin_context=self.ctx)
    context = json.loads(conv.history)
    req.system_prompt += "历史对话..."
    
    # 3. 注入定时任务专用 System Prompt
    req.system_prompt += PROACTIVE_AGENT_CRON_WOKE_SYSTEM_PROMPT.format(cron_job=...)
    
    # 4. 注入 send_message_to_user 工具
    req.func_tool.add_tool(SEND_MESSAGE_TO_USER_TOOL)
    
    # 5. 构建并运行 Agent
    result = await build_main_agent(event=cron_event, plugin_context=self.ctx, ...)
    async for _ in runner.step_until_done(30):
        pass  # Agent 自主执行，通过工具与用户交互
    
    # 6. 保存执行历史
    await persist_agent_history(...)
```

**评估：** 定时任务系统非常完善，支持 cron 表达式和一次性执行。

---

### 3.4 长时间任务执行能力 ⚠️ 部分满足，存在瓶颈

#### 3.4.1 当前限制

```python
# astrbot/core/cron/manager.py:355
async for _ in runner.step_until_done(30):
    pass
```

**关键限制：`max_step=30`**

- 每次定时任务唤醒时，Agent 最多执行 **30 步**（30 次 LLM 调用 + 工具执行循环）
- 对于你的需求（搜索 → 收集 → 创作 2-3 个剧本 → seedance → storyboard → git），30 步可能不够

#### 3.4.2 步骤消耗估算

| 阶段 | 预估步骤 |
|------|---------|
| 信息搜索和收集（3-5 次浏览器/搜索） | 5-8 步 |
| 剧本创作（2-3 个剧本，每个需多次推理） | 6-12 步 |
| 文件夹创建 + 文件写入 | 3-5 步 |
| Seedance skill 处理 | 3-5 步 |
| Storyboard-quartet skill 处理 | 3-5 步 |
| Git 操作（add + commit + push） | 2-3 步 |
| **合计** | **22-38 步** |

#### 3.4.3 核心代码

| 文件 | 关键代码 | 说明 |
|------|---------|------|
| `astrbot/core/agent/runners/tool_loop_agent_runner.py` | `ToolLoopAgentRunner.step_until_done()` | Agent 执行循环 |
| `astrbot/core/agent/runners/base.py:13-19` | `AgentState` | 状态机: IDLE → RUNNING → DONE/ERROR |
| `astrbot/core/agent/context/manager.py` | `ContextManager.process()` | 上下文压缩（防止超长上下文） |
| `astrbot/core/agent/context/compressor.py` | `LLMSummaryCompressor` | LLM 摘要压缩器 |

**评估与建议：**

- ⚠️ 30 步限制可能不足以完成全部流程
- 🔧 **方案 1**：修改 `_woke_main_agent()` 中的 `max_step` 参数为 50-60
- 🔧 **方案 2**：拆分为多个 Cron 任务（收集→创作→提交），通过知识库传递中间结果
- 🔧 **方案 3**：使用 SubAgent 编排，将复杂任务分解为子 Agent 并行执行
- ✅ 上下文压缩机制已有（`LLMSummaryCompressor` / `TruncateByTurnsCompressor`），可防止长对话溢出

---

### 3.5 记忆管理能力 ⚠️ 部分满足，需增强

#### 3.5.1 现有记忆机制

**层次 1：对话历史（短期记忆）** ✅

```
ConversationManager
  ├── session → conversation 映射（多对话管理）
  ├── 对话历史持久化到 SQLite（JSON 格式）
  └── 上下文压缩（LLM 摘要 / 轮次截断）
```

| 文件 | 关键类 | 作用 |
|------|-------|------|
| `astrbot/core/conversation_mgr.py` | `ConversationManager` | 对话 CRUD |
| `astrbot/core/db/po.py` | `ConversationV2` | 对话数据模型 |
| `astrbot/core/utils/history_saver.py` | `persist_agent_history()` | Cron 任务执行结果持久化 |

**层次 2：知识库（长期知识）** ✅

```
KnowledgeBaseManager
  ├── 文档解析（PDF/Markdown/HTML 等）
  ├── 文档分块（chunking）
  ├── 向量化存储（vec_db）
  └── 语义检索（retrieval）
```

| 文件 | 关键类 | 作用 |
|------|-------|------|
| `astrbot/core/knowledge_base/kb_mgr.py` | `KnowledgeBaseManager` | 知识库管理 |
| `astrbot/core/knowledge_base/kb_helper.py` | `KBHelper` | 知识库检索工具 |

**层次 3：人格系统（角色记忆）** ✅

```
PersonaManager
  ├── 人格提示词（system prompt）
  ├── 开场白对话（begin_dialogs）
  └── 工具/技能绑定
```

#### 3.5.2 记忆系统的不足

**问题 1：Cron 执行后的记忆保存过于简单**

```python
# astrbot/core/utils/history_saver.py:25-26
history.append({"role": "user", "content": "Output your last task result below."})
history.append({"role": "assistant", "content": summary_note})
```

仅保存了一轮 user-assistant 对话，中间的工具调用、搜索结果、创作过程**全部丢失**。

**问题 2：缺少结构化的任务记忆**

- 没有 "我昨天创作了什么剧本" 的结构化回忆
- 没有 "鸣潮最近的热门话题" 的主题积累
- 没有跨执行的状态追踪（第几天？已完成哪些？）

**问题 3：上下文窗口限制**

- 对话历史在 Cron 唤醒时被加载为纯文本注入 System Prompt
- 随着时间积累，历史会越来越长，可能超出模型上下文窗口

#### 3.5.3 建议改进方向

| 改进方向 | 实现方式 |
|---------|---------|
| 结构化任务记录 | 扩展 `persist_agent_history()` 保存工具调用链和中间产物 |
| 知识库积累 | 将每次创作的剧本摘要自动写入知识库，支持后续检索 |
| 主题记忆 | 通过 Persona 的 `begin_dialogs` 注入 "鸣潮" 相关的长期上下文 |
| 执行状态追踪 | 在 CronJob 的 `payload` 中维护执行状态（JSON） |

---

## 四、关键代码地图

### 4.1 定时任务触发链路

```
CronJobManager.start()                    # [cron/manager.py:35]
  └── APScheduler 触发
    └── _run_job()                         # [cron/manager.py:191]
      └── _run_active_agent_job()          # [cron/manager.py:234]
        └── _woke_main_agent()             # [cron/manager.py:263]  ★ 核心入口
          ├── CronMessageEvent()           # [cron/events.py:14]
          ├── _get_session_conv()           # [astr_main_agent.py:178]
          ├── build_main_agent()           # [astr_main_agent.py]  ★ 构建 Agent
          │   ├── _select_provider()       # 选择 LLM Provider
          │   ├── ToolSet 组装             # 内置工具 + 插件工具 + MCP 工具
          │   ├── System Prompt 注入       # 人格 + 安全 + 工具提示
          │   └── AgentRunner.reset()      # 初始化运行器
          ├── runner.step_until_done(30)   # [agent/runners/tool_loop_agent_runner.py]
          │   ├── Provider.llm_chat()      # 调用 LLM
          │   ├── ToolExecutor.execute()   # 执行工具
          │   └── ContextManager.process() # 上下文压缩
          └── persist_agent_history()      # [utils/history_saver.py]
```

### 4.2 Agent 工具执行链路

```
ToolLoopAgentRunner.step()                # [runners/tool_loop_agent_runner.py]
  ├── provider.llm_chat_stream()          # LLM 推理
  ├── _handle_function_tools()            # 处理工具调用
  │   └── FunctionToolExecutor.execute()  # [astr_agent_tool_exec.py:46]
  │       ├── HandoffTool → 子 Agent 委派
  │       ├── MCPTool → MCP 协议调用
  │       ├── ExecuteShellTool → Shell 命令
  │       ├── PythonTool → Python 代码
  │       ├── BrowserExecTool → 浏览器操作
  │       └── SendMessageToUserTool → 发消息
  └── ContextManager.process()            # 上下文管理
      ├── truncate_by_turns()             # 轮次截断
      └── LLMSummaryCompressor()          # LLM 摘要压缩
```

### 4.3 子 Agent 编排链路

```
SubAgentOrchestrator.reload_from_config()  # [subagent_orchestrator.py:29]
  └── 创建 HandoffTool[] → 注册到 ToolSet
      └── FunctionToolExecutor._handle_handoff()  # [astr_agent_tool_exec.py]
          ├── 创建子 Agent 的 AgentRunner
          ├── 注入子 Agent 的 System Prompt + 工具
          └── runner.step_until_done()
```

---

## 五、可行性总结与实施建议

### 5.1 总体评估

| 能力 | 评估 | 得分 |
|------|------|------|
| 工作区隔离 | ✅ Sandbox 模式天然支持，Shell/Python 可限定 cwd | 8/10 |
| 工具执行 | ✅ Shell、Python、浏览器、MCP 等工具齐全 | 9/10 |
| 定时任务 | ✅ APScheduler + Active Agent 模式完善 | 9/10 |
| 长任务执行 | ⚠️ 30 步限制需调整，上下文压缩已有 | 6/10 |
| 记忆管理 | ⚠️ 短期记忆有，长期结构化记忆需增强 | 5/10 |

**结论：AstrBot 已具备 70-80% 的基础能力，可以完成你的需求，但需要针对性优化。**

### 5.2 具体实施路线

#### Phase 1：基础配置（无需改代码）

1. **创建专用 Persona**：为"鸣潮剧本创作 Agent"创建专用人格，System Prompt 中注入：
   - 鸣潮世界观、角色信息
   - 创作风格和格式要求
   - 工作目录约定（`wuwa-video/`）
2. **配置 MCP 搜索工具**：接入 web_search_tavily 或 bocha 搜索服务
3. **创建知识库**：将鸣潮官方人物故事、主线剧情导入知识库

#### Phase 2：核心改造（需少量代码修改）

4. **调整 max_step 限制**：

```python
# astrbot/core/cron/manager.py:355
# 将 30 改为 50-60
async for _ in runner.step_until_done(50):
    pass
```

5. **增强 Cron 任务 payload**：

```python
# 在 payload 中支持 workspace 和 skills 字段
payload = {
    "session": "...",
    "note": "收集鸣潮信息并创作剧本...",
    "workspace": "/path/to/wuwa-video",  # 新增
    "skills": ["seedance", "storyboard-quartet"],  # 新增
}
```

6. **增强 `_woke_main_agent()` 的 System Prompt 注入**：在唤醒时注入工作区信息

#### Phase 3：记忆增强（中等代码量）

7. **扩展 `persist_agent_history()`**：保存结构化的执行摘要（JSON 格式）
8. **任务状态追踪**：利用 CronJob 的 `payload` 字段维护执行计数器和状态
9. **知识库自动写入**：创作完成后，自动将剧本摘要写入知识库供后续检索

### 5.3 推荐的最终架构

```
定时触发 (每天 X 点)
  └── 主 Agent (鸣潮创作人格)
       ├── 搜索子任务 → web_search + browser 工具
       │     └── 收集热门资讯、二创信息
       ├── 知识库查询 → astr_kb_search
       │     └── 检索官方人物故事、主线剧情
       ├── 剧本创作 → LLM 推理 + Shell(mkdir/写文件)
       │     └── 2-3 个 【Daily Auto】剧本
       ├── Seedance 处理 → HandoffTool(seedance子Agent)
       │     └── 生成视频提示词
       ├── 分镜创作 → HandoffTool(storyboard子Agent)
       │     └── 生成四宫格分镜文档
       ├── Git 同步 → Shell(git add/commit/push)
       └── 发送通知 → send_message_to_user
```

---

## 六、关键文件索引

| 文件路径 | 说明 | 与需求的关系 |
|---------|------|-------------|
| `astrbot/core/cron/manager.py` | **定时任务管理器** | 定时触发 Agent |
| `astrbot/core/cron/events.py` | Cron 合成事件 | 定时任务事件模型 |
| `astrbot/core/tools/cron_tools.py` | Cron 工具定义 | LLM 自主创建定时任务 |
| `astrbot/core/astr_main_agent.py` | **主 Agent 构建** | 整个 Agent 生命周期 |
| `astrbot/core/astr_main_agent_resources.py` | 工具 & 提示词资源 | 工具注册和 System Prompt |
| `astrbot/core/astr_agent_run_util.py` | Agent 运行工具 | Agent 执行循环 |
| `astrbot/core/astr_agent_tool_exec.py` | **工具执行器** | 所有工具的执行入口 |
| `astrbot/core/agent/runners/tool_loop_agent_runner.py` | **核心运行器** | Tool-Loop 模式 |
| `astrbot/core/agent/context/manager.py` | 上下文压缩管理 | 长对话管理 |
| `astrbot/core/agent/context/compressor.py` | 压缩器实现 | LLM 摘要 / 轮次截断 |
| `astrbot/core/agent/handoff.py` | HandoffTool | 子 Agent 委派 |
| `astrbot/core/subagent_orchestrator.py` | 子 Agent 编排器 | 配置和管理子 Agent |
| `astrbot/core/conversation_mgr.py` | 对话管理器 | 记忆持久化 |
| `astrbot/core/utils/history_saver.py` | 历史保存工具 | Cron 执行结果记录 |
| `astrbot/core/knowledge_base/kb_mgr.py` | 知识库管理 | 长期知识积累 |
| `astrbot/core/persona_mgr.py` | 人格管理器 | Agent 角色设定 |
| `astrbot/core/computer/tools/` | 内置工具实现 | Shell/Python/浏览器 |
| `astrbot/core/agent/mcp_client.py` | MCP 客户端 | 外部工具扩展 |
| `astrbot/core/provider/func_tool_manager.py` | 工具管理器 | MCP + 插件工具统一管理 |
| `astrbot/core/star/context.py` | 插件上下文 | 所有管理器的统一入口 |
| `astrbot/core/core_lifecycle.py` | 生命周期管理 | 系统初始化和启动 |
