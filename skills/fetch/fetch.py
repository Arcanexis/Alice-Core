import subprocess
import json
import sys
import time

class MCPFetchClient:
    def __init__(self):
        # 启动 MCP fetch 服务器
        # 使用实际存在的包: @smithery/mcp-fetch
        self.process = subprocess.Popen(
            ["npx", "-y", "@smithery/mcp-fetch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0  # 无缓冲
        )
        self.request_id = 0
        time.sleep(2)  # 等待服务器启动

    def send_request(self, method, params=None):
        """发送 JSON-RPC 请求"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }

        # 发送请求
        request_str = json.dumps(request) + "\n"
        try:
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
        except BrokenPipeError:
            stderr_output = self.process.stderr.read()
            raise Exception(f"与 MCP 服务器的连接中断。错误信息: {stderr_output}")

        # 读取响应，跳过通知消息
        while True:
            response_str = self.process.stdout.readline()
            if not response_str:
                stderr_output = self.process.stderr.read()
                raise Exception(f"未收到响应，服务器可能已关闭。错误信息: {stderr_output}")

            try:
                response = json.loads(response_str)
                # 只处理匹配 ID 的响应，跳过通知
                if "id" in response and response["id"] == self.request_id:
                    return response
            except json.JSONDecodeError:
                continue

    def initialize(self):
        """初始化 MCP 连接"""
        response = self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "python-mcp-client",
                "version": "1.0.0"
            }
        })

        # 发送 initialized 通知
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        self.process.stdin.write(json.dumps(notification) + "\n")
        self.process.stdin.flush()

        return response

    def fetch_url(self, url, max_length=20000, raw=False):
        """获取网页内容"""
        return self.send_request("tools/call", {
            "name": "fetch",
            "arguments": {
                "url": url,
                "maxLength": max_length,  # 注意是 maxLength 不是 max_length
                "raw": raw
            }
        })

    def close(self):
        """关闭连接"""
        if self.process:
            try:
                self.process.stdin.close()
            except BrokenPipeError:
                pass
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except:
                self.process.kill()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fetch_fixed.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    client = MCPFetchClient()

    try:
        # 初始化
        client.initialize()

        # 获取网页
        fetch_response = client.fetch_url(url)

        if fetch_response and 'result' in fetch_response:
            # MCP tools/call 返回的结果通常在 result.content 中
            content_list = fetch_response['result'].get('content', [])
            for item in content_list:
                if item.get('type') == 'text':
                    print(item.get('text'))
        else:
            print("获取内容失败:", json.dumps(fetch_response, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        client.close()
