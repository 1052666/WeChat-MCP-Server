#!/usr/bin/env python3
"""
微信 MCP 服务器
用于发送微信消息的模型上下文协议服务器。
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional, Union
import logging
import io

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

# MCP 协议类型
class JSONRPCRequest:
    def __init__(self, method: str, params: Optional[Dict[str, Any]] = None, id: Optional[Union[str, int]] = None):
        self.jsonrpc = "2.0"
        self.method = method
        self.params = params or {}
        self.id = id

class JSONRPCResponse:
    def __init__(self, result: Optional[Any] = None, error: Optional[Dict[str, Any]] = None, id: Optional[Union[str, int]] = None):
        self.jsonrpc = "2.0"
        self.result = result
        self.error = error
        self.id = id
    
    def to_dict(self) -> Dict[str, Any]:
        response = {"jsonrpc": self.jsonrpc}
        if self.result is not None:
            response["result"] = self.result
        if self.error is not None:
            response["error"] = self.error
        if self.id is not None:
            response["id"] = self.id
        return response

class MCPServer:
    """微信消息传递的 MCP 服务器实现。"""
    
    def __init__(self):
        self.name = "wechat-mcp-server"
        self.version = "1.0.0"
        self.initialized = False
        self.capabilities = {
            "tools": {}
        }
        self.tools = []
        self._setup_logging()
        self._register_tools()
    
    def _setup_logging(self):
        """设置日志配置。"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.name)
    
    def _register_tools(self):
        """注册可用的 MCP 工具。"""
        self.tools = [
            {
                "name": "send_wechat_message",
                "description": "向微信联系人或群组发送文本消息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "contact_name": {
                            "type": "string",
                            "description": "要发送消息的微信联系人或群组名称"
                        },
                        "message": {
                            "type": "string",
                            "description": "要发送的文本消息内容"
                        }
                    },
                    "required": ["contact_name", "message"]
                }
            },
            {
                "name": "schedule_wechat_message",
                "description": "安排在延迟后发送微信消息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "contact_name": {
                            "type": "string",
                            "description": "要发送消息的微信联系人或群组名称"
                        },
                        "message": {
                            "type": "string",
                            "description": "要发送的文本消息内容"
                        },
                        "delay_seconds": {
                            "type": "number",
                            "description": "发送消息前的延迟秒数"
                        }
                    },
                    "required": ["contact_name", "message", "delay_seconds"]
                }
            }
        ]
    
    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理传入的 JSON-RPC 请求。"""
        try:
            method = request_data.get("method")
            params = request_data.get("params", {})
            request_id = request_data.get("id")
            
            self.logger.info(f"处理请求: {method}")
            
            if method == "initialize":
                return await self._handle_initialize(params, request_id)
            elif method == "tools/list":
                return await self._handle_tools_list(request_id)
            elif method == "tools/call":
                return await self._handle_tools_call(params, request_id)
            else:
                error = {
                    "code": -32601,
                    "message": f"方法未找到: {method}"
                }
                return JSONRPCResponse(error=error, id=request_id).to_dict()
                
        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            error = {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
            return JSONRPCResponse(error=error, id=request_data.get("id")).to_dict()
    
    async def _handle_initialize(self, params: Dict[str, Any], request_id: Optional[Union[str, int]]) -> Dict[str, Any]:
        """处理 MCP 初始化请求。"""
        self.initialized = True
        
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": self.capabilities,
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }
        
        self.logger.info("Server initialized successfully")
        return JSONRPCResponse(result=result, id=request_id).to_dict()
    
    async def _handle_tools_list(self, request_id: Optional[Union[str, int]]) -> Dict[str, Any]:
        """处理 tools/list 请求。"""
        if not self.initialized:
            error = {
                "code": -32002,
                "message": "Server not initialized"
            }
            return JSONRPCResponse(error=error, id=request_id).to_dict()
        
        result = {"tools": self.tools}
        return JSONRPCResponse(result=result, id=request_id).to_dict()
    
    async def _handle_tools_call(self, params: Dict[str, Any], request_id: Optional[Union[str, int]]) -> Dict[str, Any]:
        """处理 tools/call 请求。"""
        if not self.initialized:
            error = {
                "code": -32002,
                "message": "Server not initialized"
            }
            return JSONRPCResponse(error=error, id=request_id).to_dict()
        
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "send_wechat_message":
            return await self._execute_send_message(arguments, request_id)
        elif tool_name == "schedule_wechat_message":
            return await self._execute_schedule_message(arguments, request_id)
        else:
            error = {
                "code": -32601,
                "message": f"Unknown tool: {tool_name}"
            }
            return JSONRPCResponse(error=error, id=request_id).to_dict()
    
    async def _execute_send_message(self, arguments: Dict[str, Any], request_id: Optional[Union[str, int]]) -> Dict[str, Any]:
        """执行 send_wechat_message 工具。"""
        try:
            contact_name = arguments.get("contact_name")
            message = arguments.get("message")
            
            if not contact_name or not message:
                error = {
                    "code": -32602,
                    "message": "Missing required parameters: contact_name and message"
                }
                return JSONRPCResponse(error=error, id=request_id).to_dict()
            
            # 导入并使用微信功能
            from wechat_controller import WeChatController
            
            controller = WeChatController()
            send_result = await controller.send_text_message(contact_name, message)

            success = send_result if isinstance(send_result, bool) else bool(send_result.get("ok"))

            if success:
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": "Message sent successfully"
                        }
                    ]
                }
            else:
                if isinstance(send_result, dict):
                    stage = send_result.get("stage")
                    reason = send_result.get("reason")
                    version = send_result.get("wechat_version")
                    is_nt = send_result.get("is_nt_framework")
                    extra = f" (stage={stage}, reason={reason}, wechat_version={version}, nt={is_nt})"
                else:
                    extra = ""
                result = {
                    "content": [
                        {
                            "type": "text", 
                            "text": f"Failed to send message{extra}"
                        }
                    ]
                }
            
            return JSONRPCResponse(result=result, id=request_id).to_dict()
            
        except Exception as e:
            self.logger.error(f"Error executing send_message: {e}")
            error = {
                "code": -32603,
                "message": f"Tool execution error: {str(e)}"
            }
            return JSONRPCResponse(error=error, id=request_id).to_dict()
    
    async def _execute_schedule_message(self, arguments: Dict[str, Any], request_id: Optional[Union[str, int]]) -> Dict[str, Any]:
        """执行 schedule_wechat_message 工具。"""
        try:
            contact_name = arguments.get("contact_name")
            message = arguments.get("message")
            delay_seconds = arguments.get("delay_seconds")
            
            if not contact_name or not message or delay_seconds is None:
                error = {
                    "code": -32602,
                    "message": "Missing required parameters: contact_name, message and delay_seconds"
                }
                return JSONRPCResponse(error=error, id=request_id).to_dict()
            
            # 导入并使用微信功能
            from wechat_controller import WeChatController
            
            controller = WeChatController()
            success = await controller.schedule_message(contact_name, message, delay_seconds)
            
            if success:
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Message scheduled to be sent in {delay_seconds} seconds"
                        }
                    ]
                }
            else:
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": "Failed to schedule message"
                        }
                    ]
                }
            
            return JSONRPCResponse(result=result, id=request_id).to_dict()
            
        except Exception as e:
            self.logger.error(f"Error executing schedule_message: {e}")
            error = {
                "code": -32603,
                "message": f"Tool execution error: {str(e)}"
            }
            return JSONRPCResponse(error=error, id=request_id).to_dict()

async def main():
    """MCP 服务器的主入口点。"""
    server = MCPServer()
    
    # 从标准输入读取并写入标准输出进行 MCP 通信
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            request_data = json.loads(line.strip())
            response = await server.handle_request(request_data)
            
            print(json.dumps(response, ensure_ascii=False, separators=(',', ':')))
            sys.stdout.flush()
            
        except json.JSONDecodeError as e:
            error_response = JSONRPCResponse(
                error={"code": -32700, "message": f"解析错误: {str(e)}"}
            ).to_dict()
            print(json.dumps(error_response, ensure_ascii=False, separators=(',', ':')))
            sys.stdout.flush()
        except Exception as e:
            server.logger.error(f"意外错误: {e}")
            break

if __name__ == "__main__":
    asyncio.run(main())
