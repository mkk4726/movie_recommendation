from .base import BaseClipEncoder


class SiglipMultilingualEncoder(BaseClipEncoder):
    def __init__(self):
        super().__init__(model_key="siglip-multilingual")
