import os
from dotenv import load_dotenv

load_dotenv()

# API 配置
API_KEY = os.getenv("MODELSCOPE_API_KEY")
BASE_URL = os.getenv("API_BASE_URL", "https://api-inference.modelscope.cn/v1")

# 模型配置
# 您可以在此处更改默认模型名称，或者在 .env 中设置 MODEL_NAME
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-ai/DeepSeek-V3.2")

# 提示词路径
DEFAULT_PROMPT_PATH = "prompts/alice.md"
