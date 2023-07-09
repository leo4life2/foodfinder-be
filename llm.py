from langchain.chat_models import ChatAnthropic
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from stream_handler import FoodFinderStreamingCallbackHandler

class LLM:
    def __init__(self, model="claude-1-100k", temperature=0.0):
        self.chat = ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens_to_sample=10000,
            max_tokens=10000,
            callback_manager=CallbackManager([FoodFinderStreamingCallbackHandler()]),
        )
        
    def ask(self, messages):
        return self.chat(messages)