# Alice Agent 技术文档

Alice 是一个基于 ReAct 模式的智能体框架，具备分级记忆管理、动态技能加载及隔离执行环境。

## 1. 技术架构

项目采用“宿主机核心+容器化沙盒”的隔离架构，确保执行环境的安全性和可复现性。

### 1.1 状态管理与记忆系统
智能体状态通过分层记忆实现，所有记忆文件均持久化于宿主机物理存储。
*   **短期记忆 (STM)**: 记录近 7 天的交互序列。通过 `AliceAgent.manage_memory()` 实现滚动清理。
*   **长期记忆 (LTM)**: 存储经 LLM 提炼后的高价值知识、用户偏好及决策日志。
*   **提炼逻辑**: 系统启动或触发阈值时，自动提取过期 STM 内容进行结构化总结并追加至 LTM。

### 1.2 环境隔离机制
*   **常驻容器模式**: 采用 `alice-sandbox-instance` Docker 容器作为执行引擎，避免重复冷启动。
*   **挂载策略**: 
    - 宿主机 `skills/` 目录：挂载至容器 `/app/skills`，用于存放可执行脚本。
    - 宿主机 `alice_output/` 目录：挂载至容器 `/app/alice_output`，用于存放任务产出物。
*   **非挂载项**: `agent.py`、`memory/`、`prompts/` 等核心逻辑不进入容器，防止恶意代码通过沙盒环境篡改宿主机状态或窃取隐私。

### 1.3 技能动态加载
*   **注册中心**: `SnapshotManager` 实时扫描 `skills/` 目录。
*   **识别协议**: 遵循 `agent-skills-spec_cn.md`，检测 `SKILL.md` 中的 YAML 前置元数据（name/description）。
*   **上下文注入**: 采用索引快照策略，仅将技能描述注入 LLM 上下文，降低 Token 成本，智能体需详细信息时再通过 `cat` 或 `toolkit info` 读取。

---

## 2. 内置指令参考

智能体通过宿主机引擎拦截执行的内置指令进行自维护：

| 指令 | 参数 | 描述 |
| :--- | :--- | :--- |
| `toolkit` | `list` / `info <name>` / `refresh` | 管理与查询技能注册表 |
| `memory` | `"content"` [`--ltm`] | 更新 STM 或追加 LTM 经验教训 |
| `update_prompt` | `"new_content"` | 热更新 `prompts/alice.md` 系统提示词 |

---

## 3. 项目结构

```text
.
├── agent.py                # 核心逻辑：状态机管理、指令拦截与隔离调度
├── snapshot_manager.py     # 资产索引：技能自动发现与快照生成
├── main.py                 # 交互入口：启动对话循环
├── config.py               # 配置管理：环境变量解析与路径定义
├── Dockerfile.sandbox      # 沙盒环境：基于 Ubuntu 24.04 的 Python/Node 运行环境
├── requirements.txt        # 环境依赖：沙盒镜像构建所需的 Python 库
├── agent-skills-spec_cn.md # 开发规范：技能包结构与元数据标准
├── alice_output/           # 输出目录：存储执行过程中的生成文件
├── prompts/                # 指令目录：存放 System Prompt
├── memory/                 # 状态目录：存放分级记忆文件
└── skills/                 # 技能库：存放可执行的业务插件
```

---

## 4. 开发与部署工作流

### 4.1 环境准备
1. 依赖 Python 3.8+ 及 Docker 环境。
2. 配置 `.env` 文件（必需参数：`API_KEY`, `MODEL_NAME`, `API_BASE_URL`）。

### 4.2 技能扩展流程
1. 在 `skills/` 目录下创建子目录。
2. 编写 `SKILL.md`，包含必需的 `name` 和 `description` 元数据。
3. 放置可执行代码（Python/Node.js 等）。
4. 在交互中运行 `toolkit refresh` 即可完成加载。

### 4.3 安全模型
*   **指令白名单**: `is_safe_command` 拦截 `rm` 等高危操作。
*   **容器隔离**: 所有业务逻辑与生成的未知代码均在非特权容器中执行。

---

## 5. 许可证
项目遵循 MIT 开源协议。
