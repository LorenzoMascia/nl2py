import httpx
import re
from openai import OpenAI
from typing import List, Dict, Optional


class OpenAIClient:
    def __init__(self, api_key: str, api_base: str, model: str = "gpt-4"):
        """
        Initialize the OpenAI client with API key and model.

        Args:
            api_key (str): Your OpenAI API key.
            api_base (str): Base URL of the OpenAI-compatible service.
            model (str): The OpenAI model to use (default 'gpt-4').
        """
        custom_http_client = httpx.Client(verify=False)

        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            http_client=custom_http_client  # Use custom HTTP client
        )
        self.model = model

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1024) -> str:
        """
        Send a message to the OpenAI chat API and return the response.

        Args:
            messages (List[Dict[str, str]]): List of messages in format [{"role": "user", "content": "Hello"}]
            temperature (float): Sampling temperature.
            max_tokens (int): Maximum number of tokens in the output.

        Returns:
            str: The response from the model.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()

    def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 4096, model: Optional[str] = None) -> str:
        """
        Send a prompt to the OpenAI completion API and return the response.

        Args:
            prompt (str): The input string.
            temperature (float): Sampling temperature.
            max_tokens (int): Maximum number of tokens in the output.
            model (str, optional): Completion model (e.g. 'text-davinci-003').

        Returns:
            str: The response from the model.
        """
        # Note: some compatible services may not support the legacy completion API
        # but only the chat.completions API
        response = self.client.completions.create(
            model=model or self.model,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            n=1,
            stop=None
        )
        return response.choices[0].text.strip()

    def get_python(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096, model: Optional[str] = None) -> str:
        """
        Send a prompt to the OpenAI completion API and return Python code.

        Args:
            prompt (str): The input string.
            temperature (float): Sampling temperature.
            max_tokens (int): Maximum number of tokens in the output.
            model (str, optional): Completion model (e.g. 'text-davinci-003').

        Returns:
            str: The extracted Python code from the model response.
        """
        # Note: some compatible services may not support the legacy completion API
        # but only the chat.completions API
        response = self.client.completions.create(
            model=model or self.model,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            n=1,
            stop=None
        )
        txtresponse = response.choices[0].text.strip()
        return self.extract_python_code(txtresponse)

    def extract_python_code(self, input_string: str) -> str:
        """
        Extract Python code from markdown code blocks.

        Args:
            input_string (str): String potentially containing ```python...``` blocks.

        Returns:
            str: Extracted Python code or the original string if no code block found.
        """
        pattern = r'```python(.*?)```'
        match = re.search(pattern, input_string, re.DOTALL)

        return match.group(1).strip() if match else input_string
