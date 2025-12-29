# Alice Agent 技术文档

Alice 是一个基于 ReAct 模式的智能体框架，具备分级记忆管理、动态技能加载及隔离执行环境。

## 1. 技术架构

项目采用“宿主机核心+容器化沙盒”的隔离架构，确保执行环境的安全性和可复现性。

### 1.1 状态管理与记忆系统
智能体状态通过三层分级记忆实现，所有记忆文件均持久化于宿主机物理存储。
*   **短期记忆 (STM)**: 记录近 7 天的交互序列。系统启动时通过 `AliceAgent.manage_memory()` 实现滚动清理。
*   **长期记忆 (LTM)**: 存储经 LLM 提炼后的高价值知识、用户偏好。通过 `memory --ltm` 指令可手动追加经验教训。
*   **任务清单 (Todo)**: 存储当前活跃的任务及其完成状态，辅助智能体维持长线任务目标。
*   **提炼逻辑**: 系统启动时，自动提取过期 STM 内容（超过 7 天）进行结构化总结并追加至 LTM。

### 1.2 环境隔离机制
*   **自动化容器管理**: 系统启动时自动检测 `alice-sandbox` 镜像，若缺失则基于 `Dockerfile.sandbox` 自动构建。同时自动唤醒或初始化 `alice-sandbox-instance` 常驻容器。
*   **挂载策略**: 
    - 宿主机 `skills/` 目录：挂载至容器 `/app/skills`（读写），用于存放可执行脚本。
    - 宿主机 `alice_output/` 目录：挂载至容器 `/app/alice_output`（读写），用于存放任务产出物。
*   **非挂载项**: `agent.py`、`memory/`、`prompts/` 等核心逻辑不进入容器，防止恶意代码通过沙盒环境篡改宿主机状态或窃取隐私。

### 1.3 技能动态加载
*   **注册中心**: `SnapshotManager` 实时扫描 `skills/` 目录。
*   **识别协议**: 遵循 `agent-skills-spec_cn.md`，检测 `SKILL.md` 中的 YAML 前置元数据（name/description）。
*   **上下文注入**: 采用索引快照策略，仅将技能描述注入 LLM 上下文，降低 Token 成本，智能体需详细信息时再通过 `cat` 或 `toolkit info` 读取。

---

## 2. 内置指令参考

智能体通过宿主机引擎拦截并执行以下指令。这些指令在宿主机环境运行，而非沙盒容器：

| 指令 | 参数示例 | 描述 |
| :--- | :--- | :--- |
| `toolkit` | `list` / `info <name>` / `refresh` | 管理技能注册表。`refresh` 用于实时扫描 `skills/` 目录 |
| `memory` | `"内容"` [`--ltm`] | 默认更新 STM。若带 `--ltm` 则追加至 LTM 的“经验教训”小节 |
| `update_prompt` | `"新的人设内容"` | 热更新 `prompts/alice.md` 系统提示词 |

---

## 3. 项目结构

```text
.
├── agent.py                # 核心逻辑：状态机管理、指令拦截与隔离调度
├── snapshot_manager.py     # 资产索引：技能自动发现与快照生成
├── main.py                 # 交互入口：启动对话循环
├── config.py               # 配置管理：环境变量解析与路径定义
├── .env.example            # 配置模板：环境变量示例文件
├── Dockerfile.sandbox      # 沙盒环境：基于 Ubuntu 24.04 的 Python/Node 运行环境
├── requirements.txt        # 环境依赖：基础镜像构建所需的 Python 库
├── agent-skills-spec_cn.md # 开发规范：技能包结构与元数据标准
├── alice_output/           # 输出目录：存储任务执行过程中的生成文件（已挂载）
├── prompts/                # 指令目录：存放系统提示词 (alice.md)
├── memory/                 # 状态目录：存放分级记忆文件
│   ├── alice_memory.md     # 长期记忆 (LTM)
│   ├── short_term_memory.md # 短期记忆 (STM)
│   └── todo.md             # 任务清单 (Todo)
└── skills/                 # 技能库：存放可执行的业务插件（已挂载）
```

---

## 4. 开发与部署工作流

### 4.1 环境准备
1. **基础环境**: 确保已安装 Python 3.8+、Node.js 及 Docker。
2. **安装依赖**: 
   - **后端**: `pip install openai python-dotenv fastapi uvicorn anyio`
   - **前端**: `cd alice-ui && npm install`
   *(注：业务相关的复杂依赖如 pandas, matplotlib 等已在 Docker 沙盒中预装)*
3. **配置文件**: 参考 `.env.example` 创建 `.env` 文件并填入必需参数。

### 4.2 运行方式
*   **终端模式**: `python main.py`
*   **UI 模式**:
    1. 启动后端: `python api_server.py`
    2. 启动前端: `cd alice-ui && npm run dev`
    3. 访问: `http://localhost:5173`

### 4.3 技能扩展流程
>>>>>>>

1. 在 `skills/` 目录下创建子目录。
2. 编写 `SKILL.md`，包含必需的 `name` 和 `description` 元数据。
3. 放置可执行代码（Python/Node.js 等）。
4. 在交互中运行 `toolkit refresh` 即可完成加载。

### 4.3 安全模型
*   **指令白名单**: `is_safe_command` 拦截 `rm` 等高危操作。
*   **容器隔离**: 所有业务逻辑与生成的未知代码均在非特权容器中执行。

---

## 5. 更新日志
*   **2025-12-29**: 
    - 优化 UI 成果物预览功能：支持在浏览器中直接打开 HTML 和 Markdown 文件。
    - 修复 Vite 代理配置，确保 `/outputs` 路径正确转发至后端。
    - 增强侧边栏交互：成果物文件名现在支持点击预览。
*   **2025-12-29 (修复)**:
    - 彻底修复了 Alice 在执行复杂指令（包含括号、引号、重定向等）时的转义冲突问题。
    - 将底层 `subprocess` 调用从字符串拼接待 Shell 解析模式重构为 **List 传参直接执行模式**，消除了多重 Shell 转义陷阱。
    - 正式启用了 `is_safe_command` 命令安全审查机制。
*   **2025-12-29 (优化)**:
    - 修复了 Alice 的路径认知偏差：在系统消息中增加了实时环境上下文注入（宿主/容器工作目录及映射关系）。
    - 更新了核心人设指令，强制规范使用相对路径访问 Skills，消除了 `/opt/alice/` 等虚假路径导致的工具调用失败。

## 6. 许可证
项目遵循 MIT 开源协议。
