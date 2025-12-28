import re
import subprocess
import os
import sys
from datetime import datetime, timedelta
from openai import OpenAI
import config
from snapshot_manager import SnapshotManager

class AliceAgent:
    def __init__(self, model_name=None, prompt_path=None):
        self.model_name = model_name or config.MODEL_NAME
        self.prompt_path = prompt_path or config.DEFAULT_PROMPT_PATH
        self.memory_path = config.MEMORY_FILE_PATH
        self.todo_path = config.TODO_FILE_PATH
        self.stm_path = config.SHORT_TERM_MEMORY_FILE_PATH
        self.client = OpenAI(
            base_url=config.BASE_URL,
            api_key=config.API_KEY
        )
        self.messages = []
        
        # 权限与路径安全
        self.project_root = os.getcwd() 
        
        # 沙盒配置
        self.sandbox_venv = ".venv_alice"
        self.sandbox_python = os.path.join(self.sandbox_venv, "bin", "python") if os.name != "nt" else os.path.join(self.sandbox_venv, "Scripts", "python.exe")
        
        # 内存快照管理器
        self.snapshot_mgr = SnapshotManager()
        
        # 确保输出目录存在
        os.makedirs(config.ALICE_OUTPUT_DIR, exist_ok=True)
        
        # 启动时管理记忆（滚动与提炼）
        self.manage_memory()
        
        self._refresh_system_message()

    def _refresh_system_message(self):
        """刷新系统消息，注入最新的提示词、长期记忆、短期记忆、任务清单和文件索引快照"""
        self.system_prompt = self._load_prompt()
        self.memory_content = self._load_file_content(self.memory_path, "暂无长期记忆。")
        self.stm_content = self._load_file_content(self.stm_path, "暂无近期记忆。")
        self.todo_content = self._load_file_content(self.todo_path, "暂无活跃任务。")
        self.snapshot_mgr.refresh() # 刷新快照
        self.index_text = self.snapshot_mgr.get_index_text()
        
        loaded_files = [
            self.prompt_path,
            self.memory_path,
            self.stm_path,
            self.todo_path
        ]
        files_list_str = "\n".join([f"- {f}" for f in loaded_files])
        
        full_system_content = (
            f"【核心提示】：以下文件已全量加载到你的上下文中，你可以直接引用其内容：\n{files_list_str}\n\n"
            f"{self.system_prompt}\n\n"
            f"### 你的长期记忆 (来自 {self.memory_path})\n{self.memory_content}\n\n"
            f"### 你的短期记忆 (最近 7 天，来自 {self.stm_path})\n{self.stm_content}\n\n"
            f"### 你的当前任务清单 (来自 {self.todo_path})\n{self.todo_content}\n\n"
            f"### 核心资产索引快照\n{self.index_text}"
        )
        
        if self.messages:
            self.messages[0] = {"role": "system", "content": full_system_content}
        else:
            self.messages = [{"role": "system", "content": full_system_content}]

    def _load_prompt(self):
        try:
            if os.path.exists(self.prompt_path):
                with open(self.prompt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return "你是一个 AI 助手。"
        except Exception as e:
            print(f"加载提示词失败: {e}")
            return "你是一个 AI 助手。"

    def manage_memory(self):
        """管理短期记忆滚动和长期记忆提炼"""
        if not os.path.exists(self.stm_path):
            return

        try:
            with open(self.stm_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            sections = {}
            current_date = None
            
            # 解析日期小节
            for line in lines:
                match = re.match(r'^## (\d{4}-\d{2}-\d{2})', line)
                if match:
                    current_date = match.group(1)
                    sections[current_date] = [line]
                elif current_date:
                    sections[current_date].append(line)

            if not sections:
                return

            # 计算过期日期（7天前）
            sorted_dates = sorted(sections.keys())
            today = datetime.now().date()
            expiry_limit = today - timedelta(days=7)
            
            to_prune = [d for d in sorted_dates if datetime.strptime(d, '%Y-%m-%d').date() < expiry_limit]
            
            if to_prune:
                print(f"[系统]: 发现过期短期记忆 ({len(to_prune)} 天)，正在启动提炼流程...")
                
                # 提取过期内容进行总结
                pruned_content = ""
                for d in to_prune:
                    pruned_content += "\n".join(sections[d]) + "\n"
                
                # 调用 LLM 进行提炼
                distill_prompt = (
                    f"你是一个记忆提炼专家。以下是用户最近 7 天的短期记忆记录：\n\n{content}\n\n"
                    f"请重点分析即将被删除的旧记忆：\n{pruned_content}\n\n"
                    "请根据这 7 天的整体背景，结合旧记忆，提炼出具有长期价值的：\n"
                    "1. 用户的新习惯或偏好变更。\n"
                    "2. 重要的项目决策或里程碑进展。\n"
                    "3. 用户提到的重要个人事实。\n\n"
                    "请以 Markdown 列表格式输出提炼结果，保持简洁。如果没有值得记录的长期价值，请回复“无重要更新”。"
                )
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": distill_prompt}]
                )
                summary = response.choices[0].message.content.strip()
                
                if summary and "无重要更新" not in summary:
                    # 写入长期记忆
                    with open(self.memory_path, 'a', encoding='utf-8') as f:
                        f.write(f"\n\n### 自动提炼记忆 ({datetime.now().strftime('%Y-%m-%d')})\n{summary}\n")
                    print("[系统]: 长期记忆已更新。")
                
                # 更新短期记忆文件（移除过期日期）
                remaining_content = lines[0:2] # 保持标题和描述
                for d in sorted_dates:
                    if d not in to_prune:
                        remaining_content.extend(sections[d])
                
                with open(self.stm_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(remaining_content))
                print(f"[系统]: 已清理过期短期记忆。")

        except Exception as e:
            print(f"记忆管理过程中出错: {e}")

    def _load_file_content(self, path, default_msg):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return content if content.strip() else default_msg
            return default_msg
        except Exception as e:
            print(f"加载文件 {path} 失败: {e}")
            return default_msg

    def is_safe_command(self, command):
        danger_keywords = ["rm -rf /", "mkfs", "dd ", "> /dev/"]
        for kw in danger_keywords:
            if kw in command:
                return False, f"检测到危险操作关键词: {kw}"
        return True, ""

    def execute_command(self, command, is_python_code=False):
        is_safe, error_msg = self.is_safe_command(command)
        if not is_safe:
            return f"安全性拦截: {error_msg}"

        if is_python_code:
            tmp_file = "tmp_sandbox_exec.py"
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(command)
            real_command = f"{self.sandbox_python} {tmp_file}"
            display_name = "Python 代码沙盒"
        else:
            if command.startswith("python "):
                real_command = command.replace("python ", f"{self.sandbox_python} ", 1)
            elif command.startswith("pip "):
                real_command = command.replace("pip ", f"{self.sandbox_python} -m pip ", 1)
            else:
                real_command = command
            display_name = "Shell 沙盒"

        print(f"\n[Alice 正在执行 ({display_name})]: {command[:100]}{'...' if len(command) > 100 else ''}")
        
        try:
            result = subprocess.run(
                real_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_root,
                env={**os.environ, "PYTHONPATH": self.project_root}
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[标准错误输出]:\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[执行失败，退出状态码: {result.returncode}]"
            return output if output else "[命令执行成功，无回显内容]"
        except subprocess.TimeoutExpired:
            return "错误: 执行超时。"
        except Exception as e:
            return f"执行过程中出错: {str(e)}"
        finally:
            if is_python_code and os.path.exists("tmp_sandbox_exec.py"):
                os.remove("tmp_sandbox_exec.py")

    def chat(self, user_input):
        self.messages.append({"role": "user", "content": user_input})
        
        while True:
            extra_body = {"enable_thinking": True}
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.messages,
                stream=True,
                extra_body=extra_body
            )

            full_content = ""
            thinking_content = ""
            done_thinking = False
            
            print(f"\n{'='*20} Alice 正在思考 ({self.model_name}) {'='*20}")
            
            for chunk in response:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    t_chunk = getattr(delta, 'reasoning_content', '')
                    c_chunk = getattr(delta, 'content', '')
                    
                    if t_chunk:
                        print(t_chunk, end='', flush=True)
                        thinking_content += t_chunk
                    elif c_chunk:
                        if not done_thinking:
                            print('\n\n' + "="*20 + " Alice 的回答 " + "="*20 + '\n')
                            done_thinking = True
                        print(c_chunk, end='', flush=True)
                        full_content += c_chunk

            # 改进正则：允许 ```bash 后跟可选空格，且对换行符更宽容
            python_codes = re.findall(r'```python\s*\n?(.*?)\s*```', full_content, re.DOTALL)
            bash_commands = re.findall(r'```bash\s*\n?(.*?)\s*```', full_content, re.DOTALL)
            
            if not python_codes and not bash_commands:
                self.messages.append({"role": "assistant", "content": full_content})
                break
                
            self.messages.append({"role": "assistant", "content": full_content})
            results = []
            
            for code in python_codes:
                res = self.execute_command(code.strip(), is_python_code=True)
                results.append(f"Python 代码执行结果:\n{res}")
            
            for cmd in bash_commands:
                res = self.execute_command(cmd.strip(), is_python_code=False)
                results.append(f"Shell 命令 `{cmd.strip()}` 的结果:\n{res}")
            
            feedback = "\n\n".join(results)
            self.messages.append({"role": "user", "content": f"沙盒执行反馈：\n{feedback}"})
            
            # 刷新系统消息（任何子命令执行后都可能改变文件状态，刷新快照）
            self._refresh_system_message()
                
            print(f"\n{'-'*40}\n系统快照已更新，结果已反馈给 Alice，继续生成中...")
