import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from backend.config import settings


class ToolDefinition:
    def __init__(self, name: str, description: str, parameters: dict):
        self.name = name
        self.description = description
        self.parameters = parameters

    def to_gemini_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class LLMResponse:
    pass


class TextResponse(LLMResponse):
    def __init__(self, text: str):
        self.text = text


class ToolCallResponse(LLMResponse):
    def __init__(self, tool_name: str, arguments: dict):
        self.tool_name = tool_name
        self.arguments = arguments


class LLMClient(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolDefinition]] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse | List[LLMResponse]:
        pass


class GeminiLLMClient(LLMClient):
    def __init__(self):
        try:
            from google import genai
            self.client = genai.Client(api_key=settings.LLM_API_KEY)
            self.model = settings.LLM_MODEL
        except Exception as e:
            print(f"[LLM] Warning: Could not initialize Gemini client: {e}")
            self.client = None
            self.model = None

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolDefinition]] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse | List[LLMResponse]:
        if not self.client:
            return TextResponse(text="I'm sorry, the AI service is not configured. Please check the LLM_API_KEY environment variable.")

        from google.genai import types

        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content_text = msg.get("content", "")
            if role == "system":
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append(types.Content(
                role=gemini_role,
                parts=[types.Part.from_text(text=content_text)]
            ))

        config = types.GenerateContentConfig()
        if system_prompt:
            config.system_instruction = system_prompt

        if tools:
            function_declarations = []
            for tool in tools:
                func_decl = types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.parameters
                )
                function_declarations.append(func_decl)
            config.tools = [types.Tool(function_declarations=function_declarations)]

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )

            # Check for tool calls
            if response.candidates and response.candidates[0].content:
                parts = response.candidates[0].content.parts
                tool_calls = []
                text_parts = []

                for part in parts:
                    if part.function_call:
                        tool_calls.append(ToolCallResponse(
                            tool_name=part.function_call.name,
                            arguments=dict(part.function_call.args) if part.function_call.args else {}
                        ))
                    elif part.text:
                        text_parts.append(part.text)

                if tool_calls:
                    results = []
                    if text_parts:
                        results.append(TextResponse(text="\n".join(text_parts)))
                    results.extend(tool_calls)
                    return results

                if text_parts:
                    return TextResponse(text="\n".join(text_parts))

            return TextResponse(text="I couldn't generate a response. Please try again.")

        except Exception as e:
            print(f"[LLM] Error: {e}")
            return TextResponse(text=f"I encountered an error processing your request. Please try again.")
