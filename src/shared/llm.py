"""
LLM Integration module for the Agent Platform.

This module provides integration with various LLM providers including OpenAI, Anthropic,
and local models to give agents real AI capabilities.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", "unknown")
        self.model = config.get("model", "default")
        
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text from a prompt."""
        pass
    
    @abstractmethod
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate a chat completion from messages."""
        pass
    
    @abstractmethod
    async def generate_code(self, description: str, language: str = "python", **kwargs) -> Dict[str, Any]:
        """Generate code from a description."""
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-3.5-turbo")
        
        if not self.api_key:
            logger.warning("OpenAI API key not provided. LLM functionality will be limited.")
    
    async def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using OpenAI API."""
        if not self.api_key:
            return await self._mock_response("text_generation", prompt)
        
        try:
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.7)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "text": result["choices"][0]["message"]["content"],
                            "model": self.model,
                            "provider": "openai",
                            "usage": result.get("usage", {}),
                            "status": "success"
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "error": f"OpenAI API error: {response.status} - {error_text}",
                            "status": "failed"
                        }
                        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion using OpenAI API."""
        if not self.api_key:
            return await self._mock_response("chat_completion", messages)
        
        try:
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.7)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "message": result["choices"][0]["message"],
                            "model": self.model,
                            "provider": "openai",
                            "usage": result.get("usage", {}),
                            "status": "success"
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "error": f"OpenAI API error: {response.status} - {error_text}",
                            "status": "failed"
                        }
                        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def generate_code(self, description: str, language: str = "python", **kwargs) -> Dict[str, Any]:
        """Generate code using OpenAI API."""
        prompt = f"""Generate {language} code for the following description:

{description}

Requirements:
- Write clean, well-documented code
- Include error handling where appropriate
- Follow best practices for {language}
- Provide a complete, runnable solution

Code:"""
        
        result = await self.generate_text(prompt, **kwargs)
        
        if result.get("status") == "success":
            result["language"] = language
            result["description"] = description
        
        return result
    
    async def _mock_response(self, task_type: str, input_data: Any) -> Dict[str, Any]:
        """Generate mock response when API key is not available."""
        await asyncio.sleep(1)  # Simulate API call delay
        
        if task_type == "text_generation":
            return {
                "text": f"Mock response for prompt: {str(input_data)[:100]}...",
                "model": "mock-model",
                "provider": "openai-mock",
                "status": "success"
            }
        elif task_type == "chat_completion":
            return {
                "message": {
                    "role": "assistant",
                    "content": f"Mock response to conversation with {len(input_data)} messages"
                },
                "model": "mock-model",
                "provider": "openai-mock",
                "status": "success"
            }
        else:
            return {
                "result": f"Mock response for {task_type}",
                "status": "success"
            }

class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = config.get("base_url", "https://api.anthropic.com/v1")
        self.model = config.get("model", "claude-3-sonnet-20240229")
        
        if not self.api_key:
            logger.warning("Anthropic API key not provided. LLM functionality will be limited.")
    
    async def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using Anthropic API."""
        if not self.api_key:
            return await self._mock_response("text_generation", prompt)
        
        try:
            import aiohttp
            
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": self.model,
                "max_tokens": kwargs.get("max_tokens", 1000),
                "messages": [{"role": "user", "content": prompt}]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "text": result["content"][0]["text"],
                            "model": self.model,
                            "provider": "anthropic",
                            "usage": result.get("usage", {}),
                            "status": "success"
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "error": f"Anthropic API error: {response.status} - {error_text}",
                            "status": "failed"
                        }
                        
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion using Anthropic API."""
        if not self.api_key:
            return await self._mock_response("chat_completion", messages)
        
        try:
            import aiohttp
            
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": self.model,
                "max_tokens": kwargs.get("max_tokens", 1000),
                "messages": messages
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "message": {
                                "role": "assistant",
                                "content": result["content"][0]["text"]
                            },
                            "model": self.model,
                            "provider": "anthropic",
                            "usage": result.get("usage", {}),
                            "status": "success"
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "error": f"Anthropic API error: {response.status} - {error_text}",
                            "status": "failed"
                        }
                        
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def generate_code(self, description: str, language: str = "python", **kwargs) -> Dict[str, Any]:
        """Generate code using Anthropic API."""
        prompt = f"""Generate {language} code for the following description:

{description}

Requirements:
- Write clean, well-documented code
- Include error handling where appropriate
- Follow best practices for {language}
- Provide a complete, runnable solution

Please provide only the code without additional explanation."""
        
        result = await self.generate_text(prompt, **kwargs)
        
        if result.get("status") == "success":
            result["language"] = language
            result["description"] = description
        
        return result
    
    async def _mock_response(self, task_type: str, input_data: Any) -> Dict[str, Any]:
        """Generate mock response when API key is not available."""
        await asyncio.sleep(1)  # Simulate API call delay
        
        if task_type == "text_generation":
            return {
                "text": f"Mock Anthropic response for prompt: {str(input_data)[:100]}...",
                "model": "mock-claude",
                "provider": "anthropic-mock",
                "status": "success"
            }
        elif task_type == "chat_completion":
            return {
                "message": {
                    "role": "assistant",
                    "content": f"Mock Claude response to conversation with {len(input_data)} messages"
                },
                "model": "mock-claude",
                "provider": "anthropic-mock",
                "status": "success"
            }
        else:
            return {
                "result": f"Mock Claude response for {task_type}",
                "status": "success"
            }

class LLMManager:
    """Manager for LLM providers and routing."""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider = None
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize LLM providers based on configuration."""
        # OpenAI provider
        openai_config = {
            "name": "openai",
            "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            "api_key": os.getenv("OPENAI_API_KEY")
        }
        self.providers["openai"] = OpenAIProvider(openai_config)
        
        # Anthropic provider
        anthropic_config = {
            "name": "anthropic",
            "model": os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            "api_key": os.getenv("ANTHROPIC_API_KEY")
        }
        self.providers["anthropic"] = AnthropicProvider(anthropic_config)
        
        # Set default provider
        default_provider_name = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
        self.default_provider = self.providers.get(default_provider_name, self.providers["openai"])
        
        logger.info(f"Initialized LLM providers: {list(self.providers.keys())}")
        logger.info(f"Default provider: {default_provider_name}")
    
    def get_provider(self, provider_name: Optional[str] = None) -> LLMProvider:
        """Get a specific provider or the default one."""
        if provider_name and provider_name in self.providers:
            return self.providers[provider_name]
        return self.default_provider
    
    async def generate_text(self, prompt: str, provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate text using specified or default provider."""
        llm_provider = self.get_provider(provider)
        return await llm_provider.generate_text(prompt, **kwargs)
    
    async def chat_completion(self, messages: List[Dict[str, str]], provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate chat completion using specified or default provider."""
        llm_provider = self.get_provider(provider)
        return await llm_provider.chat_completion(messages, **kwargs)
    
    async def generate_code(self, description: str, language: str = "python", provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate code using specified or default provider."""
        llm_provider = self.get_provider(provider)
        return await llm_provider.generate_code(description, language, **kwargs)
    
    async def analyze_data(self, data_description: str, analysis_type: str = "general", provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Analyze data using LLM."""
        prompt = f"""Analyze the following data and provide insights:

Data Description: {data_description}
Analysis Type: {analysis_type}

Please provide:
1. Key observations
2. Patterns or trends identified
3. Potential insights or recommendations
4. Areas for further investigation

Analysis:"""
        
        result = await self.generate_text(prompt, provider, **kwargs)
        
        if result.get("status") == "success":
            result["analysis_type"] = analysis_type
            result["data_description"] = data_description
        
        return result
    
    async def plan_project(self, description: str, requirements: List[str] = None, provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate project plan using LLM."""
        requirements_text = "\n".join(f"- {req}" for req in (requirements or []))
        
        prompt = f"""Create a detailed project plan for the following:

Project Description: {description}

Requirements:
{requirements_text}

Please provide:
1. Project breakdown into phases/milestones
2. Estimated timeline for each phase
3. Key deliverables
4. Potential risks and mitigation strategies
5. Resource requirements

Project Plan:"""
        
        result = await self.generate_text(prompt, provider, **kwargs)
        
        if result.get("status") == "success":
            result["project_description"] = description
            result["requirements"] = requirements or []
        
        return result

# Global LLM manager instance
llm_manager = LLMManager()

# Convenience functions
async def generate_text(prompt: str, provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Generate text using the global LLM manager."""
    return await llm_manager.generate_text(prompt, provider, **kwargs)

async def chat_completion(messages: List[Dict[str, str]], provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Generate chat completion using the global LLM manager."""
    return await llm_manager.chat_completion(messages, provider, **kwargs)

async def generate_code(description: str, language: str = "python", provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Generate code using the global LLM manager."""
    return await llm_manager.generate_code(description, language, provider, **kwargs)

async def analyze_data(data_description: str, analysis_type: str = "general", provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Analyze data using the global LLM manager."""
    return await llm_manager.analyze_data(data_description, analysis_type, provider, **kwargs)

async def plan_project(description: str, requirements: List[str] = None, provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Generate project plan using the global LLM manager."""
    return await llm_manager.plan_project(description, requirements, provider, **kwargs)