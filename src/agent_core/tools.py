import asyncio
import inspect
import logging
import json
import os
import sys
import subprocess
import tempfile
from typing import Dict, Any, Callable, Awaitable, Union, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type for tool functions - can be either sync or async
ToolFunction = Union[
    Callable[..., Dict[str, Any]],
    Callable[..., Awaitable[Dict[str, Any]]]
]

class ToolRegistry:
    """Registry for tools that agents can use."""
    
    def __init__(self):
        self.tools: Dict[str, ToolFunction] = {}
    
    def register(self, name: str, func: ToolFunction):
        """Register a tool function."""
        if name in self.tools:
            logger.warning(f"Tool {name} is already registered. Overwriting.")
        
        self.tools[name] = func
        logger.debug(f"Registered tool: {name}")
    
    def unregister(self, name: str):
        """Unregister a tool function."""
        if name in self.tools:
            del self.tools[name]
            logger.debug(f"Unregistered tool: {name}")
        else:
            logger.warning(f"Tool {name} is not registered.")
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self.tools
    
    async def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool function."""
        if name not in self.tools:
            raise ValueError(f"Tool {name} is not registered.")
        
        tool_func = self.tools[name]
        
        try:
            # Check if the function is a coroutine function
            if inspect.iscoroutinefunction(tool_func):
                # Execute asynchronously
                result = await tool_func(**kwargs)
            else:
                # Execute synchronously in a thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: tool_func(**kwargs)
                )
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return {
                "error": str(e),
                "status": "failed"
            }
    
    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all registered tools with their metadata."""
        result = {}
        
        for name, func in self.tools.items():
            # Get function signature
            sig = inspect.signature(func)
            
            # Get function docstring
            doc = inspect.getdoc(func) or "No documentation available."
            
            # Get parameter info
            params = {}
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                
                param_info = {
                    "required": param.default is inspect.Parameter.empty,
                }
                
                if param.annotation is not inspect.Parameter.empty:
                    param_info["type"] = str(param.annotation)
                
                if param.default is not inspect.Parameter.empty:
                    param_info["default"] = param.default
                
                params[param_name] = param_info
            
            result[name] = {
                "description": doc,
                "parameters": params,
                "is_async": inspect.iscoroutinefunction(func)
            }
        
        return result

# Built-in tool implementations
class BuiltinTools:
    """Collection of built-in tools for agents."""
    
    @staticmethod
    async def read_file(file_path: str) -> Dict[str, Any]:
        """Read content from a file."""
        try:
            if not os.path.exists(file_path):
                return {"error": f"File {file_path} does not exist", "status": "failed"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "content": content,
                "file_path": file_path,
                "size": len(content),
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    @staticmethod
    async def write_file(file_path: str, content: str, mode: str = 'w') -> Dict[str, Any]:
        """Write content to a file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)
            
            return {
                "file_path": file_path,
                "bytes_written": len(content.encode('utf-8')),
                "mode": mode,
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    @staticmethod
    async def execute_code(code: str, language: str = "python", timeout: int = 30) -> Dict[str, Any]:
        """Execute code in a sandboxed environment."""
        try:
            if language.lower() not in ["python", "bash", "javascript"]:
                return {"error": f"Unsupported language: {language}", "status": "failed"}
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            try:
                if language.lower() == "python":
                    result = subprocess.run(
                        [sys.executable, temp_file],
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                elif language.lower() == "bash":
                    result = subprocess.run(
                        ["bash", temp_file],
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                elif language.lower() == "javascript":
                    result = subprocess.run(
                        ["node", temp_file],
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                    "language": language,
                    "status": "success" if result.returncode == 0 else "failed"
                }
            
            finally:
                # Clean up temporary file
                os.unlink(temp_file)
                
        except subprocess.TimeoutExpired:
            return {"error": f"Code execution timed out after {timeout} seconds", "status": "failed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    @staticmethod
    async def search_text(text: str, pattern: str, case_sensitive: bool = False) -> Dict[str, Any]:
        """Search for a pattern in text."""
        try:
            import re
            
            flags = 0 if case_sensitive else re.IGNORECASE
            matches = re.finditer(pattern, text, flags)
            
            results = []
            for match in matches:
                results.append({
                    "match": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "groups": match.groups()
                })
            
            return {
                "pattern": pattern,
                "matches": results,
                "count": len(results),
                "case_sensitive": case_sensitive,
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    @staticmethod
    async def memory_add(memory_store: list, item: Dict[str, Any]) -> Dict[str, Any]:
        """Add an item to memory."""
        try:
            memory_item = {
                "id": len(memory_store),
                "timestamp": datetime.utcnow().isoformat(),
                "data": item
            }
            memory_store.append(memory_item)
            
            return {
                "item_id": memory_item["id"],
                "memory_size": len(memory_store),
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    @staticmethod
    async def memory_search(memory_store: list, query: str) -> Dict[str, Any]:
        """Search memory for items matching a query."""
        try:
            results = []
            query_lower = query.lower()
            
            for item in memory_store:
                item_str = json.dumps(item.get("data", {})).lower()
                if query_lower in item_str:
                    results.append(item)
            
            return {
                "query": query,
                "results": results,
                "count": len(results),
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    @staticmethod
    async def http_request(url: str, method: str = "GET", headers: Dict[str, str] = None, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make an HTTP request."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method.upper(),
                    url=url,
                    headers=headers or {},
                    json=data
                ) as response:
                    content = await response.text()
                    
                    return {
                        "url": url,
                        "method": method.upper(),
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "content": content,
                        "status": "success"
                    }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    @staticmethod
    async def json_parse(json_string: str) -> Dict[str, Any]:
        """Parse JSON string."""
        try:
            parsed = json.loads(json_string)
            return {
                "parsed_data": parsed,
                "type": type(parsed).__name__,
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    @staticmethod
    async def calculate(expression: str) -> Dict[str, Any]:
        """Safely evaluate mathematical expressions."""
        try:
            # Only allow safe mathematical operations
            allowed_names = {
                k: v for k, v in __builtins__.items()
                if k in ['abs', 'round', 'min', 'max', 'sum', 'len']
            }
            allowed_names.update({
                'pi': 3.14159265359,
                'e': 2.71828182846
            })
            
            # Evaluate the expression safely
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            
            return {
                "expression": expression,
                "result": result,
                "type": type(result).__name__,
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

def register_builtin_tools(registry: ToolRegistry):
    """Register all built-in tools with a registry."""
    builtin_tools = {
        "read_file": BuiltinTools.read_file,
        "write_file": BuiltinTools.write_file,
        "execute_code": BuiltinTools.execute_code,
        "search_text": BuiltinTools.search_text,
        "memory_add": BuiltinTools.memory_add,
        "memory_search": BuiltinTools.memory_search,
        "http_request": BuiltinTools.http_request,
        "json_parse": BuiltinTools.json_parse,
        "calculate": BuiltinTools.calculate
    }
    
    for name, func in builtin_tools.items():
        registry.register(name, func)
    
    logger.info(f"Registered {len(builtin_tools)} built-in tools")
