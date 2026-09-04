import json
import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from backend.config import settings


class ToolDefinition:
    def __init__(self, name: str, description: str, parameters: dict):
        self.name = name
        self.description = description
        self.parameters = parameters


class LLMResponse:
    def __init__(self, tokens_used: int = 0):
        self.tokens_used = tokens_used


class TextResponse(LLMResponse):
    def __init__(self, text: str, tokens_used: int = 0):
        super().__init__(tokens_used=tokens_used)
        self.text = text


class ToolCallResponse(LLMResponse):
    def __init__(self, tool_name: str, arguments: dict, tool_call_id: str = "", tokens_used: int = 0):
        super().__init__(tokens_used=tokens_used)
        self.tool_name = tool_name
        self.arguments = arguments
        self.tool_call_id = tool_call_id


def _openai_style_usage_tokens(response: Any) -> int:
    usage = getattr(response, "usage", None)
    if not usage:
        return 0
    total = getattr(usage, "total_tokens", None)
    return int(total or 0)


def _gemini_usage_tokens(response: Any) -> int:
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return 0
    total = getattr(usage, "total_token_count", None)
    return int(total or 0)


class LLMClient(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolDefinition]] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse | List[LLMResponse]:
        pass


class OllamaLLMClient(LLMClient):
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolDefinition]] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse | List[LLMResponse]:
        import httpx

        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "tool":
                ollama_messages.append({
                    "role": "tool",
                    "content": content
                })
            elif role in ("user", "assistant", "system"):
                ollama_messages.append({"role": role, "content": content})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False
        }

        if tools:
            ollama_tools = []
            for tool in tools:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                })
            payload["tools"] = ollama_tools

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload
                )
                resp.raise_for_status()
                data = resp.json()

            choice = data["choices"][0]["message"]
            tokens_used = int(data.get("usage", {}).get("total_tokens") or 0)
            if not tokens_used:
                tokens_used = int(data.get("prompt_eval_count") or 0) + int(data.get("eval_count") or 0)

            if choice.get("tool_calls"):
                results = []
                if choice.get("content"):
                    results.append(TextResponse(text=choice["content"], tokens_used=tokens_used))
                for tc in choice["tool_calls"]:
                    args = {}
                    func = tc.get("function", {})
                    if func.get("arguments"):
                        args = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
                    results.append(ToolCallResponse(
                        tool_name=func["name"],
                        arguments=args,
                        tool_call_id=tc.get("id", f"call_{uuid.uuid4().hex[:12]}"),
                        tokens_used=tokens_used
                    ))
                return results

            if choice.get("content"):
                return TextResponse(text=choice["content"], tokens_used=tokens_used)

            return TextResponse(text="I couldn't generate a response. Please try again.")

        except httpx.ConnectError:
            print("[LLM] Ollama not running. Start with: ollama serve")
            return TextResponse(text="AI service is offline. Please start Ollama (ollama serve) and try again.")
        except Exception as e:
            print(f"[LLM] Ollama error: {e}")
            return TextResponse(text="I encountered an error processing your request. Please try again.")


class GroqLLMClient(LLMClient):
    def __init__(self, api_key: str = "", model: str = ""):
        try:
            from groq import Groq
            self.client = Groq(api_key=api_key or settings.LLM_API_KEY, timeout=180.0)
            self.model = model or settings.LLM_MODEL
        except Exception as e:
            print(f"[LLM] Warning: Could not initialize Groq client: {e}")
            self.client = None
            self.model = None

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolDefinition]] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse | List[LLMResponse]:
        if not self.client:
            return TextResponse(text="AI service not configured. Please check the LLM_API_KEY environment variable.")

        groq_messages = []
        if system_prompt:
            groq_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "tool":
                groq_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "content": content
                })
            elif role in ("user", "assistant", "system"):
                groq_messages.append({"role": role, "content": content})

        kwargs = {"model": self.model, "messages": groq_messages}

        if tools:
            groq_tools = []
            for tool in tools:
                groq_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                })
            kwargs["tools"] = groq_tools
            kwargs["tool_choice"] = "auto"

        try:
            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            tokens_used = _openai_style_usage_tokens(response)

            if choice.message.tool_calls:
                results = []
                if choice.message.content:
                    results.append(TextResponse(text=choice.message.content, tokens_used=tokens_used))
                for tc in choice.message.tool_calls:
                    args = {}
                    if tc.function.arguments:
                        args = json.loads(tc.function.arguments)
                    results.append(ToolCallResponse(
                        tool_name=tc.function.name,
                        arguments=args,
                        tool_call_id=tc.id,
                        tokens_used=tokens_used
                    ))
                return results

            if choice.message.content:
                return TextResponse(text=choice.message.content, tokens_used=tokens_used)

            return TextResponse(text="I couldn't generate a response. Please try again.")

        except Exception as e:
            print(f"[LLM] Groq error: {e}")
            return TextResponse(text="I encountered an error processing your request. Please try again.")


class RotatingGroqClient(LLMClient):
    """Rotates through multiple Groq API keys on rate limit/quota errors."""

    def __init__(self, api_keys: List[str], model: str = ""):
        from groq import Groq
        self.clients = []
        self.model = model or settings.LLM_MODEL
        for key in api_keys:
            if key.strip():
                self.clients.append(Groq(api_key=key.strip(), timeout=180.0))
        self._current = 0
        print(f"[LLM] Initialized RotatingGroqClient with {len(self.clients)} keys")

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolDefinition]] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse | List[LLMResponse]:
        last_error = None
        for attempt in range(len(self.clients)):
            idx = (self._current + attempt) % len(self.clients)
            client = self.clients[idx]
            try:
                result = self._call_groq(client, messages, tools, system_prompt)
                self._current = idx
                return result
            except Exception as e:
                err_str = str(e).lower()
                if "rate" in err_str or "limit" in err_str or "quota" in err_str or "429" in err_str:
                    print(f"[LLM] Key {idx} rate limited, rotating to next...")
                    last_error = TextResponse(text=(
                        "The AI service is temporarily rate limited. "
                        "Please wait a moment and try again."
                    ))
                    continue
                last_error = TextResponse(text=f"LLM error: {str(e)[:100]}")
                print(f"[LLM] Key {idx} error: {e}")
                continue

        return last_error or TextResponse(text="All API keys exhausted. Please try again later.")

    def _call_groq(self, client, messages, tools, system_prompt):
        groq_messages = []
        if system_prompt:
            groq_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "tool":
                groq_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "content": content
                })
            elif role in ("user", "assistant", "system"):
                groq_messages.append({"role": role, "content": content})

        kwargs = {"model": self.model, "messages": groq_messages}

        if tools:
            groq_tools = []
            for tool in tools:
                groq_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                })
            kwargs["tools"] = groq_tools
            kwargs["tool_choice"] = "auto"

        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        tokens_used = _openai_style_usage_tokens(response)

        if choice.message.tool_calls:
            results = []
            if choice.message.content:
                results.append(TextResponse(text=choice.message.content, tokens_used=tokens_used))
            for tc in choice.message.tool_calls:
                args = {}
                if tc.function.arguments:
                    args = json.loads(tc.function.arguments)
                results.append(ToolCallResponse(
                    tool_name=tc.function.name,
                    arguments=args,
                    tool_call_id=tc.id,
                    tokens_used=tokens_used
                ))
            return results

        if choice.message.content:
            return TextResponse(text=choice.message.content, tokens_used=tokens_used)

        return TextResponse(text="I couldn't generate a response. Please try again.")


class GeminiLLMClient(LLMClient):
    def __init__(self, api_key: str = "", model: str = ""):
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key or settings.LLM_API_KEY)
            self.model = model or settings.LLM_MODEL
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
            return TextResponse(text="AI service not configured. Please check the LLM_API_KEY environment variable.")

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
            tokens_used = _gemini_usage_tokens(response)

            if response.candidates and response.candidates[0].content:
                parts = response.candidates[0].content.parts
                tool_calls = []
                text_parts = []

                for part in parts:
                    if part.function_call:
                        tool_calls.append(ToolCallResponse(
                            tool_name=part.function_call.name,
                            arguments=dict(part.function_call.args) if part.function_call.args else {},
                            tool_call_id=f"call_{uuid.uuid4().hex[:12]}",
                            tokens_used=tokens_used
                        ))
                    elif part.text:
                        text_parts.append(part.text)

                if tool_calls:
                    results = []
                    if text_parts:
                        results.append(TextResponse(text="\n".join(text_parts), tokens_used=tokens_used))
                    results.extend(tool_calls)
                    return results

                if text_parts:
                    return TextResponse(text="\n".join(text_parts), tokens_used=tokens_used)

            return TextResponse(text="I couldn't generate a response. Please try again.")

        except Exception as e:
            print(f"[LLM] Gemini error: {e}")
            return TextResponse(text="I encountered an error processing your request. Please try again.")


class RotatingLLMClient(LLMClient):
    """Tries multiple LLM clients in sequence, rotating on rate limit errors."""

    def __init__(self, clients: List[LLMClient]):
        self.clients = clients
        self._current = 0

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolDefinition]] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse | List[LLMResponse]:
        last_error = None
        for attempt in range(len(self.clients)):
            idx = (self._current + attempt) % len(self.clients)
            client = self.clients[idx]
            try:
                result = await client.generate(messages, tools, system_prompt)
                if isinstance(result, TextResponse) and "rate" in result.text.lower() and "limit" in result.text.lower():
                    last_error = result
                    print(f"[LLM] Rate limited on client {idx}, trying next...")
                    continue
                if isinstance(result, TextResponse) and "quota" in result.text.lower():
                    last_error = result
                    print(f"[LLM] Quota exhausted on client {idx}, trying next...")
                    continue
                self._current = idx
                return result
            except Exception as e:
                last_error = TextResponse(text=str(e))
                print(f"[LLM] Client {idx} failed: {e}, trying next...")
                continue

        return last_error or TextResponse(text="All AI providers are unavailable. Please try again later.")
