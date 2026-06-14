from io import BytesIO
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor

from ..utils import make_square
from . import MODEL_REGISTRY as CLIP_MODEL_REGISTRY


class BaseClipEncoder:
    MODEL_REGISTRY = CLIP_MODEL_REGISTRY

    def __init__(self, model_key: str = "siglip-multilingual"):
        if model_key not in self.MODEL_REGISTRY:
            raise ValueError(f"Unknown model_key '{model_key}'. Available: {list(self.MODEL_REGISTRY.keys())}")

        model_name = self.MODEL_REGISTRY[model_key]

        if torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # 일부 모델은 remote code 필요
        trust = True if "jina" in model_name or "siglip" in model_name else False

        self.model = AutoModel.from_pretrained(model_name, trust_remote_code=trust).to(self.device)

        self.processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=trust)

    def encode_text(self, text: str):
        inputs = self.processor(text=[text], return_tensors="pt").to(self.device)

        with torch.no_grad():
            emb = self.model.get_text_features(**inputs)
        return emb / emb.norm(dim=-1, keepdim=True)

    def _encode_image_tensor(self, image: Image.Image, apply_square: bool = True):
        processed_image = make_square(image) if apply_square else image
        inputs = self.processor(images=processed_image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            emb = self.model.get_image_features(**inputs)
        return emb / emb.norm(dim=-1, keepdim=True)

    def encode_image(self, image: Image.Image, apply_square: bool = True):
        if not isinstance(image, Image.Image):
            raise TypeError("image must be a PIL.Image.Image instance")
        return self._encode_image_tensor(image.convert("RGB"), apply_square=apply_square)

    def encode_image_from_path(self, image_path: str | Path, apply_square: bool = True):
        image = Image.open(image_path).convert("RGB")
        return self._encode_image_tensor(image, apply_square=apply_square)

    def encode_image_from_bytes(self, image_bytes: bytes | bytearray, apply_square: bool = True):
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        return self._encode_image_tensor(image, apply_square=apply_square)
