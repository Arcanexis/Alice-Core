import sys
from agent import AliceAgent

def main():
    print("\n" + "*"*50)
    print("      Alice 智能体系统已就绪")
    print("*"*50)
    print("输入 'quit' 或 'exit' 退出程序。")

    alice = AliceAgent()

    while True:
        try:
            user_input = input("\n[您]: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['quit', 'exit']:
                print("再见！")
                break
            
            alice.chat(user_input)
            
        except KeyboardInterrupt:
            print("\n程序终止。")
            break
        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    main()
