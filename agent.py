import re
import subprocess
import os
from openai import OpenAI
import config

class AliceAgent:
    def __init__(self, model_name=None, prompt_path=None):
        self.model_name = model_name or config.MODEL_NAME
        self.prompt_path = prompt_path or config.DEFAULT_PROMPT_PATH
        self.memory_path = config.MEMORY_FILE_PATH
        self.client = OpenAI(
            base_url=config.BASE_URL,
            api_key=config.API_KEY
        )
        self.messages = []
        
        # 沙盒配置
        self.sandbox_venv = ".venv_alice"
        self.sandbox_python = os.path.join(self.sandbox_venv, "bin", "python") if os.name != "nt" else os.path.join(self.sandbox_venv, "Scripts", "python.exe")
        
        self._refresh_system_message()

    def _refresh_system_message(self):
        """刷新系统消息，注入最新的提示词和长期记忆"""
        self.system_prompt = self._load_prompt()
        self.memory_content = self._load_memory()
        
        full_system_content = f"{self.system_prompt}\n\n### 你的长期记忆 (来自 {self.memory_path})\n{self.memory_content}"
        
        if self.messages:
            self.messages[0] = {"role": "system", "content": full_system_content}
        else:
            self.messages = [{"role": "system", "content": full_system_content}]

    def _load_prompt(self):
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"加载提示词失败: {e}")
            return "你是一个 AI 助手。"

    def _load_memory(self):
        """加载长期记忆"""
        try:
            if os.path.exists(self.memory_path):
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return "暂无记忆。"
        except Exception as e:
            print(f"加载记忆失败: {e}")
            return "暂无记忆。"

    def execute_command(self, command, is_python_code=False):
        """
        在沙盒中执行命令或 Python 代码
        """
        if is_python_code:
            # 如果是纯 Python 代码块，将其写入临时文件并运行
            tmp_file = "tmp_sandbox_exec.py"
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(command)
            real_command = f"{self.sandbox_python} {tmp_file}"
            display_name = "Python 代码沙盒"
        else:
            # 如果是 Shell 命令，确保 Python 和 Pip 调用指向沙盒虚拟环境
            if command.startswith("python "):
                real_command = command.replace("python ", f"{self.sandbox_python} ", 1)
            elif command.startswith("pip "):
                # 将 pip 替换为沙盒内的 python -m pip 以确保安全性
                real_command = command.replace("pip ", f"{self.sandbox_python} -m pip ", 1)
            else:
                real_command = command
            display_name = "Shell 沙盒"

        print(f"\n[Alice 正在执行 ({display_name})]: {command[:100]}{'...' if len(command) > 100 else ''}")
        
        try:
            # 设置超时时间为 60 秒
            result = subprocess.run(
                real_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, "PYTHONPATH": os.getcwd()} # 确保能找到本地 skills 模块
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[标准错误输出]:\n{result.stderr}"
            
            if result.returncode != 0:
                output += f"\n[执行失败，退出状态码: {result.returncode}]"
                
            return output if output else "[命令执行成功，无回显内容]"
        
        except subprocess.TimeoutExpired:
            return "错误: 执行超时（限制为 60 秒）。请优化您的代码或命令。"
        except Exception as e:
            return f"执行过程中出错: {str(e)}"
        finally:
            if is_python_code and os.path.exists("tmp_sandbox_exec.py"):
                os.remove("tmp_sandbox_exec.py")

    def chat(self, user_input):
        self.messages.append({"role": "user", "content": user_input})
        
        while True:
            # 调用模型
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

            # 1. 优先检查 Python 代码块 (```python)
            python_codes = re.findall(r'```python\n(.*?)\n```', full_content, re.DOTALL)
            # 2. 检查 Shell 代码块 (```bash)
            bash_commands = re.findall(r'```bash\n(.*?)\n```', full_content, re.DOTALL)
            
            if not python_codes and not bash_commands:
                # 记录助手回答并退出循环
                self.messages.append({"role": "assistant", "content": full_content})
                break
                
            # 执行并收集结果
            self.messages.append({"role": "assistant", "content": full_content})
            results = []
            
            # 先跑 Python
            for code in python_codes:
                res = self.execute_command(code.strip(), is_python_code=True)
                results.append(f"Python 代码执行结果:\n{res}")
            
            # 再跑 Bash
            for cmd in bash_commands:
                res = self.execute_command(cmd.strip(), is_python_code=False)
                results.append(f"Shell 命令 `{cmd.strip()}` 的结果:\n{res}")
                
                # 如果涉及了 memory 文件的修改，标记需要刷新
                if config.MEMORY_FILE_PATH in cmd:
                    print("[系统]: 检测到记忆文件修改。")
            
            # 反馈结果
            feedback = "\n\n".join(results)
            self.messages.append({"role": "user", "content": f"沙盒执行反馈：\n{feedback}"})
            
            # 刷新系统消息以包含最新记忆
            if any(config.MEMORY_FILE_PATH in cmd for cmd in bash_commands):
                self._refresh_system_message()
                print("[系统]: 长期记忆已更新并重新注入上下文。")
                
            print(f"\n{'-'*40}\n结果已反馈给 Alice，继续生成中...")
