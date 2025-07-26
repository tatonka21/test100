import asyncio
import inspect
import logging
from typing import Dict, Any, Callable, Awaitable, Union, Optional

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
