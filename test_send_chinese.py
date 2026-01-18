
import asyncio
import os
import sys
import logging

# 将 src 目录添加到 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from wechat_controller import WeChatController

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    controller = WeChatController()
    
    # 打印当前状态
    status = controller.get_status()
    print(f"Current Status: {status}")
    
    if not status.get('wechat_available'):
        print("WeChat not available!")
        return

    # 测试中文发送
    contact = "10.14"
    message = "你好，这是一条中文测试消息"
    
    print(f"Sending message to {contact}: {message}")
    result = await controller.send_text_message(contact, message)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
