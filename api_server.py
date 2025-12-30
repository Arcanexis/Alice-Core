import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from agent import AliceAgent
import config
import os
from anyio import to_thread

app = FastAPI(title="Alice Agent API")

# 启用 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 Agent 实例
alice = AliceAgent()

def save_chat_history(user_msg, bot_msg):
    """保存对话历史到 JSON"""
    history = []
    if os.path.exists(config.CHAT_HISTORY_FILE_PATH):
        try:
            with open(config.CHAT_HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    
    history.append(user_msg)
    history.append(bot_msg)
    
    # 保持最近的 50 条消息对 (100 条记录)
    if len(history) > 100:
        history = history[-100:]
        
    try:
        with open(config.CHAT_HISTORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving chat history: {e}")

# 确保输出目录存在
os.makedirs(config.ALICE_OUTPUT_DIR, exist_ok=True)

# 挂载输出目录为静态资源
app.mount("/outputs", StaticFiles(directory=config.ALICE_OUTPUT_DIR), name="outputs")

@app.post("/api/interrupt")
async def interrupt():
    alice.interrupt()
    return {"status": "ok"}

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    message = data.get("message")
    
    async def event_generator():
        user_msg = {"role": "user", "content": message}
        bot_msg = {"role": "bot", "steps": [], "finalAnswer": "", "isComplete": False}
        
        def sync_gen():
            for chunk in alice.stream_chat(message):
                yield chunk
        
        for chunk in sync_gen():
            # 记录到历史记录对象中
            if chunk["type"] == "start_step":
                bot_msg["steps"].append({
                    "id": chunk["step"],
                    "thinking": "",
                    "content": "",
                    "executionResults": [],
                    "systemLogs": []
                })
            elif chunk["type"] == "thinking" and bot_msg["steps"]:
                bot_msg["steps"][-1]["thinking"] += chunk["delta"]
            elif chunk["type"] == "content" and bot_msg["steps"]:
                bot_msg["steps"][-1]["content"] += chunk["delta"]
            elif chunk["type"] == "system" and bot_msg["steps"]:
                bot_msg["steps"][-1]["systemLogs"].append(chunk["content"])
            elif chunk["type"] == "execution_result" and bot_msg["steps"]:
                bot_msg["steps"][-1]["executionResults"].append(chunk["content"])
            elif chunk["type"] == "final_answer":
                bot_msg["finalAnswer"] = chunk["content"]
                bot_msg["isComplete"] = True
            
            yield json.dumps(chunk, ensure_ascii=False) + "\n"
            await asyncio.sleep(0.01)
        
        # 对话结束后保存
        await to_thread.run_sync(save_chat_history, user_msg, bot_msg)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/history")
async def get_history():
    if os.path.exists(config.CHAT_HISTORY_FILE_PATH):
        try:
            with open(config.CHAT_HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

@app.post("/api/history/clear")
async def clear_history():
    if os.path.exists(config.CHAT_HISTORY_FILE_PATH):
        os.remove(config.CHAT_HISTORY_FILE_PATH)
    return {"status": "ok"}

@app.get("/api/tasks")
async def get_tasks():
    if os.path.exists(config.TODO_FILE_PATH):
        with open(config.TODO_FILE_PATH, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    return {"content": "暂无任务清单"}

@app.get("/api/skills")
async def get_skills():
    alice.snapshot_mgr.refresh()
    return {"skills": alice.snapshot_mgr.skills}

def get_directory_tree(path, base_url):
    """递归构建目录树"""
    tree = []
    try:
        items = os.listdir(path)
        # 排序：目录在前，文件在后，同类按修改时间排序
        items_with_meta = []
        for f in items:
            full_path = os.path.join(path, f)
            items_with_meta.append({
                "name": f,
                "is_dir": os.path.isdir(full_path),
                "mtime": os.path.getmtime(full_path)
            })
        
        items_with_meta.sort(key=lambda x: (not x["is_dir"], -x["mtime"]))
        
        for item in items_with_meta:
            name = item["name"]
            full_path = os.path.join(path, name)
            rel_path = os.path.relpath(full_path, config.ALICE_OUTPUT_DIR)
            url = f"{base_url}/{rel_path.replace(os.sep, '/')}"
            
            node = {
                "name": name,
                "type": "directory" if item["is_dir"] else "file",
                "mtime": item["mtime"],
                "url": url
            }
            
            if item["is_dir"]:
                node["children"] = get_directory_tree(full_path, base_url)
                # 检查是否有 index.html 以便前端提供快捷访问
                if os.path.exists(os.path.join(full_path, "index.html")):
                    node["hasIndex"] = True
                    node["indexUrl"] = f"{url}/index.html"
            else:
                node["size"] = os.path.getsize(full_path)
                
            tree.append(node)
    except Exception as e:
        print(f"Error building tree for {path}: {e}")
    return tree

@app.get("/api/outputs")
async def list_outputs():
    if os.path.exists(config.ALICE_OUTPUT_DIR):
        tree = get_directory_tree(config.ALICE_OUTPUT_DIR, "/outputs")
        return {"files": tree}
    return {"files": []}

@app.get("/api/memory")
async def get_memory():
    ltm = ""
    stm = ""
    if os.path.exists(config.MEMORY_FILE_PATH):
        with open(config.MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
            ltm = f.read()
    if os.path.exists(config.SHORT_TERM_MEMORY_FILE_PATH):
        with open(config.SHORT_TERM_MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
            stm = f.read()
    return {"ltm": ltm, "stm": stm}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
