# tests/mock_llm.py
# S-tier MockLLM that mimics the real LLM interface (supports .content)

class MockMessage:
    def __init__(self, content: str):
        self.content = content


class MockLLM:
    """
    Minimal async mock that behaves like the real LLM:
    - chat() returns an object with .content
    - complete() returns an object with .content
    - deterministic output
    """

    async def chat(self, messages):
        return MockMessage("Mock response")

    async def complete(self, prompt: str):
        return MockMessage("Mock completion")
