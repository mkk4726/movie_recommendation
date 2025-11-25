from .base import BaseClipEncoder


class JinaClipEncoder(BaseClipEncoder):
    def __init__(self):
        super().__init__(model_key="jina-clip")