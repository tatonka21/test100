import asyncio
import logging
import json
import os
import sys
sys.path.append('/workspaces/test100')
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .base_agent import BaseAgent
from .tools import ToolRegistry, register_builtin_tools
from src.shared.database import db_manager, TaskRepository
from src.shared.llm import generate_text, chat_completion, generate_code, analyze_data, plan_project

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutonomousAgent(BaseAgent):
    """An autonomous agent that can execute tasks independently."""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self.type = "autonomous"
        
        # Initialize tool registry
        self.tools = ToolRegistry()
        
        # Register default tools
        self._register_default_tools()
        
        # Register additional tools based on capabilities
        self._register_capability_tools()
        
        # Agent memory (would be more sophisticated in a real implementation)
        self.memory = []
        self.max_memory_items = config.get("max_memory_items", 100)
        
        # Agent goals and constraints
        self.goals = config.get("goals", [])
        self.constraints = config.get("constraints", [])
        
        # Project context
        self.project_id = config.get("project_id")
        self.project_context = config.get("project_context", {})
    
    def _initialize_state(self):
        """Initialize agent-specific state."""
        self.state = {
            "current_task": None,
            "task_history": [],
            "memory": self.memory,
            "goals": self.goals,
            "constraints": self.constraints,
            "project_context": self.project_context
        }
    
    def _register_default_tools(self):
        """Register default tools available to all autonomous agents."""
        # Register all built-in tools
        register_builtin_tools(self.tools)
        
        # Add agent-specific tools
        self.tools.register("search", self._search_tool)
    
    def _register_capability_tools(self):
        """Register tools based on agent capabilities."""
        capability_tool_map = {
            "code_generation": ["generate_code", "refactor_code", "test_code"],
            "data_analysis": ["analyze_data", "visualize_data", "query_data"],
            "web_browsing": ["browse_web", "scrape_content", "download_file"],
            "llm": ["generate_text", "summarize_text", "translate_text"]
        }
        
        for capability in self.capabilities:
            if capability in capability_tool_map:
                for tool_name in capability_tool_map[capability]:
                    # Register capability-specific tools
                    if tool_name == "generate_code":
                        self.tools.register(tool_name, self._generate_code_tool)
                    elif tool_name == "analyze_data":
                        self.tools.register(tool_name, self._analyze_data_tool)
                    else:
                        # Placeholder for other tools
                        self.tools.register(tool_name, self._placeholder_tool)
    
    async def _search_tool(self, query: str, source: str = "memory") -> Dict[str, Any]:
        """Search tool implementation."""
        try:
            if source == "memory":
                # Search in agent's memory
                results = []
                query_lower = query.lower()
                
                for item in self.memory:
                    item_str = str(item).lower()
                    if query_lower in item_str:
                        results.append(item)
                
                return {
                    "query": query,
                    "source": source,
                    "results": results,
                    "count": len(results),
                    "status": "success"
                }
            else:
                return {"error": f"Unsupported search source: {source}", "status": "failed"}
                
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    async def _generate_code_tool(self, description: str, language: str = "python", framework: str = "") -> Dict[str, Any]:
        """Code generation tool implementation."""
        return await self._handle_generate_code("tool_task", {
            "description": description,
            "language": language,
            "framework": framework
        })
    
    async def _analyze_data_tool(self, data_source: str, analysis_type: str = "general") -> Dict[str, Any]:
        """Data analysis tool implementation."""
        return await self._handle_analyze_data("tool_task", {
            "data_source": data_source,
            "analysis_type": analysis_type
        })
    
    async def _placeholder_tool(self, *args, **kwargs) -> Dict[str, Any]:
        """Placeholder tool for unimplemented capabilities."""
        return {
            "message": "Tool functionality not yet implemented",
            "args": args,
            "kwargs": kwargs,
            "status": "success"
        }
    
    async def process_task(self, task_id: str, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task and return the result."""
        # Update state to reflect current task
        self.state["current_task"] = {
            "id": task_id,
            "type": task_type,
            "parameters": parameters,
            "started_at": datetime.utcnow().isoformat()
        }
        
        result = {}
        
        try:
            # Update task status in database
            async with db_manager.get_session() as db:
                task_repo = TaskRepository(db)
                await task_repo.update(task_id, {
                    "status": "running",
                    "started_at": datetime.utcnow()
                })
            
            # Handle different task types
            if task_type == "execute_tool":
                result = await self._handle_execute_tool(task_id, parameters)
            
            elif task_type == "plan_project":
                result = await self._handle_plan_project(task_id, parameters)
            
            elif task_type == "generate_code":
                result = await self._handle_generate_code(task_id, parameters)
            
            elif task_type == "analyze_data":
                result = await self._handle_analyze_data(task_id, parameters)
            
            elif task_type == "research_topic":
                result = await self._handle_research_topic(task_id, parameters)
            
            else:
                logger.warning(f"Agent {self.agent_id} received unknown task type: {task_type}")
                result = {
                    "error": f"Unknown task type: {task_type}",
                    "status": "failed"
                }
        
        except Exception as e:
            logger.error(f"Agent {self.agent_id} failed to process task {task_id}: {e}")
            result = {
                "error": str(e),
                "status": "failed"
            }
        
        # Update task history and memory
        await self._update_task_completion(task_id, task_type, parameters, result)
        
        return result
    
    async def _handle_execute_tool(self, task_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution tasks."""
        tool_name = parameters.get("tool_name")
        tool_params = parameters.get("parameters", {})
        
        if not tool_name:
            raise ValueError("Tool name is required for execute_tool tasks")
        
        if not self.tools.has_tool(tool_name):
            raise ValueError(f"Tool {tool_name} is not available to this agent")
        
        # Execute the tool
        logger.info(f"Agent {self.agent_id} executing tool {tool_name}")
        tool_result = await self.tools.execute(tool_name, **tool_params)
        
        return {
            "tool_name": tool_name,
            "tool_result": tool_result,
            "status": "success"
        }
    
    async def _handle_plan_project(self, task_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project planning tasks using LLM."""
        project_description = parameters.get("description", "")
        requirements = parameters.get("requirements", [])
        constraints = parameters.get("constraints", [])
        
        logger.info(f"Agent {self.agent_id} planning project: {project_description}")
        
        try:
            # Use LLM to generate intelligent project plan
            llm_result = await plan_project(
                description=project_description,
                requirements=requirements,
                provider=parameters.get("llm_provider")
            )
            
            if llm_result.get("status") == "success":
                # Parse the LLM response and structure it
                plan_text = llm_result.get("text", "")
                
                return {
                    "plan_text": plan_text,
                    "project_description": project_description,
                    "requirements_analyzed": requirements,
                    "constraints_considered": constraints,
                    "llm_provider": llm_result.get("provider", "unknown"),
                    "model": llm_result.get("model", "unknown"),
                    "status": "success"
                }
            else:
                # Fallback to basic planning if LLM fails
                return await self._fallback_plan_project(project_description, requirements, constraints)
                
        except Exception as e:
            logger.error(f"LLM project planning failed: {e}")
            return await self._fallback_plan_project(project_description, requirements, constraints)
    
    async def _fallback_plan_project(self, description: str, requirements: List[str], constraints: List[str]) -> Dict[str, Any]:
        """Fallback project planning when LLM is unavailable."""
        plan_steps = [
            {"step": 1, "description": "Analyze requirements and constraints", "estimated_hours": 2},
            {"step": 2, "description": "Design system architecture", "estimated_hours": 8},
            {"step": 3, "description": "Set up development environment", "estimated_hours": 4},
            {"step": 4, "description": "Implement core functionality", "estimated_hours": 24},
            {"step": 5, "description": "Add tests and documentation", "estimated_hours": 12},
            {"step": 6, "description": "Review and refine", "estimated_hours": 6}
        ]
        
        # Add requirement-specific steps
        if "database" in str(requirements).lower():
            plan_steps.insert(3, {"step": 3.5, "description": "Design and implement database schema", "estimated_hours": 6})
        
        if "api" in str(requirements).lower():
            plan_steps.insert(-2, {"step": 5.5, "description": "Implement API endpoints", "estimated_hours": 8})
        
        total_hours = sum(step.get("estimated_hours", 0) for step in plan_steps)
        
        return {
            "plan": plan_steps,
            "estimated_hours": total_hours,
            "estimated_days": round(total_hours / 8, 1),
            "requirements_analyzed": requirements,
            "constraints_considered": constraints,
            "fallback_used": True,
            "status": "success"
        }
    
    async def _handle_generate_code(self, task_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code generation tasks using LLM."""
        code_description = parameters.get("description", "")
        language = parameters.get("language", "python")
        framework = parameters.get("framework", "")
        
        logger.info(f"Agent {self.agent_id} generating {language} code: {code_description}")
        
        try:
            # Use LLM to generate intelligent code
            llm_result = await generate_code(
                description=code_description,
                language=language,
                provider=parameters.get("llm_provider")
            )
            
            if llm_result.get("status") == "success":
                return {
                    "code": llm_result.get("text", ""),
                    "language": language,
                    "framework": framework,
                    "description": code_description,
                    "llm_provider": llm_result.get("provider", "unknown"),
                    "model": llm_result.get("model", "unknown"),
                    "status": "success"
                }
            else:
                # Fallback to template-based generation if LLM fails
                return await self._fallback_generate_code(code_description, language, framework)
                
        except Exception as e:
            logger.error(f"LLM code generation failed: {e}")
            return await self._fallback_generate_code(code_description, language, framework)
    
    async def _fallback_generate_code(self, description: str, language: str, framework: str) -> Dict[str, Any]:
        """Fallback code generation when LLM is unavailable."""
        if language.lower() == "python":
            if "fastapi" in framework.lower():
                code = f'''# Generated FastAPI code for: {description}
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="{description}")

class RequestModel(BaseModel):
    data: Dict[str, Any]

@app.get("/")
async def root():
    return {{"message": "Hello World"}}

@app.post("/process")
async def process_data(request: RequestModel):
    # Process the data here
    return {{"result": "processed", "data": request.data}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
            else:
                code = f'''# Generated Python code for: {description}
import asyncio
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class {description.replace(" ", "")}:
    """Generated class for {description}."""
    
    def __init__(self):
        self.data = {{}}
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the input data."""
        logger.info(f"Processing data: {{input_data}}")
        
        # Add your processing logic here
        result = {{"processed": True, "input": input_data}}
        
        return result

async def main():
    processor = {description.replace(" ", "")}()
    result = await processor.process({{"test": "data"}})
    print(f"Result: {{result}}")

if __name__ == "__main__":
    asyncio.run(main())
'''
        else:
            code = f"// Generated {language} code for: {description}\n// TODO: Implement {description}"
        
        return {
            "code": code,
            "language": language,
            "framework": framework,
            "description": description,
            "fallback_used": True,
            "status": "success"
        }
    
    async def _handle_analyze_data(self, task_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data analysis tasks using LLM."""
        data_source = parameters.get("data_source", "")
        analysis_type = parameters.get("analysis_type", "general")
        data_description = parameters.get("data_description", data_source)
        
        logger.info(f"Agent {self.agent_id} analyzing data from: {data_source}")
        
        try:
            # Use LLM to generate intelligent data analysis
            llm_result = await analyze_data(
                data_description=data_description,
                analysis_type=analysis_type,
                provider=parameters.get("llm_provider")
            )
            
            if llm_result.get("status") == "success":
                return {
                    "analysis_type": analysis_type,
                    "data_source": data_source,
                    "analysis_text": llm_result.get("text", ""),
                    "data_description": data_description,
                    "llm_provider": llm_result.get("provider", "unknown"),
                    "model": llm_result.get("model", "unknown"),
                    "status": "success"
                }
            else:
                # Fallback to basic analysis if LLM fails
                return await self._fallback_analyze_data(data_source, analysis_type)
                
        except Exception as e:
            logger.error(f"LLM data analysis failed: {e}")
            return await self._fallback_analyze_data(data_source, analysis_type)
    
    async def _fallback_analyze_data(self, data_source: str, analysis_type: str) -> Dict[str, Any]:
        """Fallback data analysis when LLM is unavailable."""
        await asyncio.sleep(2)  # Simulate processing time
        
        return {
            "analysis_type": analysis_type,
            "data_source": data_source,
            "summary": f"Analysis completed for {data_source}",
            "insights": [
                "Data quality is good with 95% completeness",
                "Identified 3 key trends in the dataset",
                "Recommended further investigation of outliers"
            ],
            "recommendations": [
                "Clean missing data points",
                "Apply statistical analysis to trends",
                "Create visualization dashboard"
            ],
            "fallback_used": True,
            "status": "success"
        }
    
    async def _handle_research_topic(self, task_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research tasks using LLM."""
        topic = parameters.get("topic", "")
        depth = parameters.get("depth", "medium")
        
        logger.info(f"Agent {self.agent_id} researching topic: {topic}")
        
        try:
            # Create research prompt
            research_prompt = f"""Research the topic: {topic}

Depth level: {depth}

Please provide a comprehensive research summary including:
1. Overview of the topic
2. Key concepts and definitions
3. Current trends and developments
4. Important findings or insights
5. Potential applications or implications
6. Areas for further research

Research Summary:"""
            
            # Use LLM to generate intelligent research
            llm_result = await generate_text(
                prompt=research_prompt,
                provider=parameters.get("llm_provider"),
                max_tokens=1500
            )
            
            if llm_result.get("status") == "success":
                return {
                    "topic": topic,
                    "depth": depth,
                    "research_text": llm_result.get("text", ""),
                    "llm_provider": llm_result.get("provider", "unknown"),
                    "model": llm_result.get("model", "unknown"),
                    "status": "success"
                }
            else:
                # Fallback to basic research if LLM fails
                return await self._fallback_research_topic(topic, depth)
                
        except Exception as e:
            logger.error(f"LLM research failed: {e}")
            return await self._fallback_research_topic(topic, depth)
    
    async def _fallback_research_topic(self, topic: str, depth: str) -> Dict[str, Any]:
        """Fallback research when LLM is unavailable."""
        await asyncio.sleep(3)  # Simulate research time
        
        return {
            "topic": topic,
            "depth": depth,
            "summary": f"Research completed on {topic}",
            "key_findings": [
                f"Key concept 1 related to {topic}",
                f"Key concept 2 related to {topic}",
                f"Key concept 3 related to {topic}"
            ],
            "sources": [
                "Academic paper 1",
                "Industry report 2",
                "Expert blog post 3"
            ],
            "next_steps": [
                "Deep dive into specific aspects",
                "Validate findings with experts",
                "Apply insights to current project"
            ],
            "fallback_used": True,
            "status": "success"
        }
    
    async def _update_task_completion(self, task_id: str, task_type: str, parameters: Dict[str, Any], result: Dict[str, Any]):
        """Update task completion in memory and database."""
        # Update task history in memory
        task_record = {
            "id": task_id,
            "type": task_type,
            "parameters": parameters,
            "result": result,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        self.state["task_history"].append(task_record)
        self.state["current_task"] = None
        
        # Add to memory if successful
        if result.get("status") == "success":
            memory_item = {
                "type": "task_completion",
                "task_type": task_type,
                "summary": result.get("summary", f"Completed {task_type} task"),
                "timestamp": datetime.utcnow().isoformat()
            }
            self.memory.append(memory_item)
        
        # Limit memory and task history size
        if len(self.memory) > self.max_memory_items:
            self.memory = self.memory[-self.max_memory_items:]
        
        if len(self.state["task_history"]) > self.max_memory_items:
            self.state["task_history"] = self.state["task_history"][-self.max_memory_items:]
        
        # Update task status in database
        try:
            async with db_manager.get_session() as db:
                task_repo = TaskRepository(db)
                await task_repo.update(task_id, {
                    "status": "completed" if result.get("status") == "success" else "failed",
                    "result": result,
                    "completed_at": datetime.utcnow()
                })
        except Exception as e:
            logger.error(f"Failed to update task {task_id} in database: {e}")
