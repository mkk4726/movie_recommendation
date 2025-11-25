from .base import BaseClipEncoder
from typing import Literal

class OpenCLIPEncoder(BaseClipEncoder):
    def __init__(self, model_key: Literal["openclip-b32", "openclip-h14"] = "openclip-b32"):
        """
        model_key는 'openclip-b32' 또는 'openclip-h14' 중 하나입니다.
        """
        if model_key not in ("openclip-b32", "openclip-h14"):
            raise ValueError(f"model_key must be one of 'openclip-b32', 'openclip-h14', got '{model_key}'")
        super().__init__(model_key=model_key)