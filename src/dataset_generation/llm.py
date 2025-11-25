"""
LLM 모델 사용을 위한 기본 모듈
로컬에서 Qwen 모델을 사용하여 텍스트 생성
"""
import logging
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Logger 설정
logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM 설정"""
    model_name: str = "Qwen/Qwen2.5-3B-Instruct"
    max_new_tokens: int = 512
    temperature: float = 0.9
    top_p: float = 0.95
    do_sample: bool = True
    
    @classmethod
    def from_yaml(cls, yaml_path: Optional[str] = None) -> 'LLMConfig':
        """
        YAML 파일에서 설정을 로드하여 LLMConfig 객체 생성
        
        Args:
            yaml_path: YAML 파일 경로 (None이면 기본 경로 사용)
            
        Returns:
            LLMConfig 객체
        """
        # 기본 경로 설정
        if yaml_path is None:
            yaml_path = Path(__file__).parent / 'config.yaml'
        else:
            yaml_path = Path(yaml_path)
        
        # YAML 파일 읽기
        logger.info(f"📄 설정 파일 로드: {yaml_path}")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        
        # query_generation 섹션 추출
        if 'query_generation' not in config_dict:
            raise ValueError("config.yaml 파일에 'query_generation' 섹션이 없습니다.")
        
        qg_config = config_dict['query_generation']
        
        # LLMConfig에 필요한 필드만 추출
        llm_config = {
            'model_name': qg_config.get('model_name', 'Qwen/Qwen2.5-3B-Instruct'),
            'max_new_tokens': qg_config.get('max_new_tokens', 512),
            'temperature': qg_config.get('temperature', 0.9),
            'top_p': qg_config.get('top_p', 0.95),
            'do_sample': qg_config.get('do_sample', True),
        }
        
        logger.info("✅ LLM 설정 로드 완료")
        return cls(**llm_config)


class LLM:
    """Qwen 모델 기반 LLM 클래스"""
    
    def __init__(self, config: Optional[LLMConfig] = None, yaml_path: Optional[str] = None):
        """
        LLM 초기화
        
        Args:
            config: LLMConfig 객체 (None이면 YAML에서 로드)
            yaml_path: YAML 파일 경로 (config가 None일 때 사용)
        """
        # 설정 로드
        if config is None:
            self.config = LLMConfig.from_yaml(yaml_path)
        else:
            self.config = config
        
        self.model_name = self.config.model_name
        self._load_model()
    
    def _load_model(self):
        """모델 및 토크나이저 로드"""
        logger.info(f"🔄 모델 로드 중: {self.model_name}")
        
        # 토크나이저 로드
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # 디바이스 및 dtype 설정
        use_cuda = torch.cuda.is_available()
        use_mps = torch.backends.mps.is_available()
        
        if use_cuda:
            dtype = torch.float16
            device_map = "auto"
        elif use_mps:
            dtype = torch.float16
            device_map = "auto"
        else:
            dtype = torch.float32
            device_map = None
        
        # 모델 로드
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=dtype,
            device_map=device_map,
            low_cpu_mem_usage=True,
        )
        
        self.model.eval()
        logger.info("✅ 모델 로드 완료")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        do_sample: Optional[bool] = None,
    ) -> str:
        """
        프롬프트를 입력받아 텍스트 생성
        
        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택)
            max_new_tokens: 생성할 최대 토큰 수
            temperature: 샘플링 온도
            top_p: Top-p 샘플링 값
            do_sample: 샘플링 사용 여부
            
        Returns:
            생성된 텍스트
        """
        # 파라미터 설정 (None이면 config 값 사용)
        max_new_tokens = max_new_tokens if max_new_tokens is not None else self.config.max_new_tokens
        temperature = temperature if temperature is not None else self.config.temperature
        top_p = top_p if top_p is not None else self.config.top_p
        do_sample = do_sample if do_sample is not None else self.config.do_sample
        
        # 메시지 구성
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 템플릿 적용
        template_result = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_tensors="pt",
        )
        
        # 입력 텐서 준비
        if isinstance(template_result, torch.Tensor):
            input_ids = template_result
            attention_mask = torch.ones_like(input_ids)
            inputs = {"input_ids": input_ids, "attention_mask": attention_mask}
        else:
            inputs = template_result
            if "attention_mask" not in inputs:
                inputs["attention_mask"] = torch.ones_like(inputs["input_ids"])
        
        # 디바이스로 이동
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # 텍스트 생성
        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.eos_token_id,
                use_cache=True,
            )
        
        # 결과 디코딩
        response = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[-1]:],
            skip_special_tokens=True
        )
        
        return response


# 사용 예시
if __name__ == "__main__":
    # LLM 초기화
    llm = LLM()
    
    # 쿼리 생성
    prompt = "파이썬에서 리스트와 튜플의 차이점을 간단히 설명해줘."
    response = llm.generate(prompt)
    
    print("\n" + "="*60)
    print("프롬프트:", prompt)
    print("-"*60)
    print("응답:", response)
    print("="*60)

