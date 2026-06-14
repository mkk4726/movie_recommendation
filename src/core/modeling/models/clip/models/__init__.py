MODEL_REGISTRY = {
    # JinaCLIP (multilingual, SigLIP backbone) — legacy
    "jina-clip": "jinaai/jina-clip-v1",
    # OpenAI CLIP (영어 중심)
    "openai-b32": "openai/clip-vit-base-patch32",
    "openai-b16": "openai/clip-vit-base-patch16",
    "openai-l14": "openai/clip-vit-large-patch14",
    # OpenCLIP (LAION)
    "openclip-b32": "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
    "openclip-h14": "laion/CLIP-ViT-H-14-laion2B-s32B-b79K",
    # M-CLIP (multilingual)
    "mclip": "M-CLIP/XLM-Roberta-Large-Vit-B-32",
    # SigLIP multilingual (Google, 768-dim, 한국어 지원)
    "siglip-multilingual": "google/siglip-base-patch16-256-multilingual",
    "siglip-kr": "google/siglip-base-patch16-256-multilingual",  # alias
}

__all__ = ["MODEL_REGISTRY"]
