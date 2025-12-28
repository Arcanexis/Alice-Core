import re
import subprocess
from openai import OpenAI
import config

class AliceAgent:
    def __init__(self, model_name=None, prompt_path=None):
        self.model_name = model_name or config.MODEL_NAME
        self.prompt_path = prompt_path or config.DEFAULT_PROMPT_PATH
        self.client = OpenAI(
            base_url=config.BASE_URL,
            api_key=config.API_KEY
        )
        self.system_prompt = self._load_prompt()
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def _load_prompt(self):
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"加载提示词失败: {e}")
            return "你是一个 AI 助手。"

    def execute_command(self, command):
        """执行 shell 命令并返回输出"""
        print(f"\n[Alice 正在执行命令]: {command}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            output = result.stdout
            if result.stderr:
                output += f"\n错误输出:\n{result.stderr}"
            return output if output else "[命令执行成功，无回显内容]"
        except Exception as e:
            return f"执行过程中出错: {str(e)}"

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

            # 检查命令
            commands = re.findall(r'```bash\n(.*?)\n```', full_content, re.DOTALL)
            
            if not commands:
                # 记录助手回答并退出循环
                self.messages.append({"role": "assistant", "content": full_content})
                break
                
            # 执行命令
            self.messages.append({"role": "assistant", "content": full_content})
            results = []
            for cmd in commands:
                res = self.execute_command(cmd.strip())
                results.append(f"命令 `{cmd.strip()}` 的结果:\n{res}")
            
            # 反馈结果
            feedback = "\n\n".join(results)
            self.messages.append({"role": "user", "content": f"系统执行反馈：\n{feedback}"})
            print(f"\n{'-'*40}\n结果已反馈给 Alice，继续生成中...")
