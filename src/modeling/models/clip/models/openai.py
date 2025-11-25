from typing import Union, List, Literal
from io import BytesIO
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from . import MODEL_REGISTRY
from ..utils import make_square


# OpenAI CLIP 모델 스펙 요약
#
# 1. ViT-B/32 (clip-b32)
#   - 파라미터:     151M
#   - 임베딩 차원:   512
#   - 패치 크기:    32x32
#   - 입력 해상도:  224x224
#   - 장점:         가볍고 빠름
#   - 단점:         해상도 낮아 세밀한 이미지 표현 한계
#
# 2. ViT-B/16 (clip-b16)
#   - 파라미터:     151M
#   - 임베딩 차원:   512
#   - 패치 크기:    16x16
#   - 입력 해상도:  224x224
#   - 장점:         B/32보다 정확도 크게 향상
#   - 단점:         속도는 약간 느림 (패치 수 2배)
#
# 3. ViT-L/14 (clip-l14)
#   - 파라미터:     428M
#   - 임베딩 차원:   768
#   - 패치 크기:    14x14
#   - 입력 해상도:  224x224
#   - 장점:         SOTA급 이미지·텍스트 성능
#   - 단점:         매우 무거움, 메모리 사용량 많음
#
# | 모델               | 파라미터 | 임베딩 | 패치  | 해상도  | 특징                        |
# |------------------|--------|------|------|-------|-----------------------------|
# | clip-b32(ViT-B/32)| 151M   | 512  | 32x32| 224x224| 가장 가벼움, 속도 빠름         |
# | clip-b16(ViT-B/16)| 151M   | 512  | 16x16| 224x224| 동일 파라미터, 더 높은 정확도   |
# | clip-l14(ViT-L/14)| 428M   | 768  | 14x14| 224x224| SOTA, 리소스 많이 요구         |


class OpenAICLIPEncoder:
    """
    Unified Encoder for OpenAI CLIP Models
    - Supports image encoding
    - Supports text encoding
    - Returns L2-normalized embeddings (industry standard for retrieval)
    """

    def __init__(
        self,
        model_key: Literal["openai-b32", "openai-b16", "openai-l14"]
        | str = "openai-b32",
        device: str | None = None,
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        resolved_model_name = MODEL_REGISTRY.get(model_key, model_key)

        self.model = CLIPModel.from_pretrained(resolved_model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(resolved_model_name)

        self.model.eval()

    @torch.no_grad()
    def encode_image(self, image: Union[str, Image.Image], apply_square: bool = True):
        if isinstance(image, str):
            image = Image.open(image).convert("RGB")
        elif isinstance(image, Image.Image):
            image = image.convert("RGB")
        else:
            raise TypeError("image must be a str path or PIL.Image.Image instance")

        processed_image = make_square(image) if apply_square else image
        inputs = self.processor(images=processed_image, return_tensors="pt").to(self.device)
        embeddings = self.model.get_image_features(**inputs)

        # L2 normalization for retrieval
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
        return embeddings.cpu()

    @torch.no_grad()
    def encode_image_from_bytes(self, image_bytes: Union[bytes, bytearray], apply_square: bool = True):
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        return self.encode_image(image, apply_square=apply_square)

    @torch.no_grad()
    def encode_text(self, text: Union[str, List[str]]):
        if isinstance(text, str):
            text = [text]

        inputs = self.processor(text=text, return_tensors="pt", padding=True).to(self.device)
        embeddings = self.model.get_text_features(**inputs)

        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
        return embeddings.cpu()
