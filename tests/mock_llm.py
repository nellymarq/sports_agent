class MockLLM:
    """
    A safe, isolated mock LLM for pytest.
    It never calls Groq and cannot interfere with runtime.
    """

    async def chat(self, messages):
        # Return a predictable assistant message
        return {
            "role": "assistant",
            "content": "[MOCK RESPONSE]",
            "tool_calls": []
        }
