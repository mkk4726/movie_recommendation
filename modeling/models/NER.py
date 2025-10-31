"""
Qwen 기반 Named Entity Recognition (NER) 모델
영화 추천 쿼리에서 엔티티(배우, 장르, 감독 등)를 추출합니다.
"""
import json
import re
import logging
import yaml
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
)
import torch

# Logger 설정
logger = logging.getLogger(__name__)


@dataclass
class NERConfig:
    """NER 모델 설정"""
    model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"
    allowed_models: list = field(default_factory=lambda: [
        "Qwen/Qwen2.5-1.5B-Instruct",
        "Qwen/Qwen2.5-3B-Instruct",
        "Qwen/Qwen2.5-7B-Instruct"
    ])
    max_new_tokens: int = 128
    temperature: float = 0.7
    top_p: float = 0.9
    do_sample: bool = False
    system_prompt: str = ""
    # MPS 단일 디바이스 강제 여부(메모리 여유 시 속도 향상 가능, 부족 시 OOM 위험)
    mps_single_device: bool = False
    
    @classmethod
    def from_yaml(cls, yaml_path: Optional[str] = None) -> 'NERConfig':
        """
        YAML 파일에서 설정을 로드하여 NERConfig 객체 생성
        
        Args:
            yaml_path: YAML 파일 경로 (None이면 기본 경로 사용)
            
        Returns:
            NERConfig 객체
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
        
        # ner 섹션 추출
        if 'ner' not in config_dict:
            raise ValueError("config.yaml 파일에 'ner' 섹션이 없습니다.")
        
        ner_config = config_dict['ner']
        
        logger.info("✅ NER 설정 로드 완료")
        return cls(**ner_config)


@dataclass
class NERResult:
    """NER 추출 결과"""
    actors: List[str] = field(default_factory=list)
    genres: List[str] = field(default_factory=list)
    years: List[int] = field(default_factory=list)
    directors: List[str] = field(default_factory=list)
    movie_titles: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)
    story_keywords: List[str] = field(default_factory=list)
    other_keywords: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NERResult':
        """
        딕셔너리에서 NERResult 객체 생성
        
        Args:
            data: 추출된 엔티티 딕셔너리
            
        Returns:
            NERResult 객체
        """
        # years 필드는 정수로 변환 시도
        years = []
        if "years" in data:
            for year in data["years"]:
                try:
                    if isinstance(year, str):
                        # "2020년" 같은 형식에서 숫자만 추출
                        year_str = re.sub(r'\D', '', year)
                        if year_str:
                            years.append(int(year_str))
                    else:
                        years.append(int(year))
                except (ValueError, TypeError):
                    logger.warning(f"연도 변환 실패: {year}")
        
        return cls(
            actors=data.get("actors", []),
            genres=data.get("genres", []),
            years=years,
            directors=data.get("directors", []),
            movie_titles=data.get("movie_titles", []),
            regions=data.get("regions", []),
            story_keywords=data.get("story_keywords", []),
            other_keywords=data.get("other_keywords", [])
        )
    
    def __str__(self) -> str:
        """사람이 읽기 쉬운 형식으로 출력"""
        parts = []
        if self.actors:
            parts.append(f"배우: {', '.join(self.actors)}")
        if self.genres:
            parts.append(f"장르: {', '.join(self.genres)}")
        if self.years:
            parts.append(f"연도: {', '.join(map(str, self.years))}")
        if self.directors:
            parts.append(f"감독: {', '.join(self.directors)}")
        if self.movie_titles:
            parts.append(f"영화 제목: {', '.join(self.movie_titles)}")
        if self.regions:
            parts.append(f"지역: {', '.join(self.regions)}")
        if self.story_keywords:
            parts.append(f"스토리 키워드: {', '.join(self.story_keywords)}")
        if self.other_keywords:
            parts.append(f"기타 키워드: {', '.join(self.other_keywords)}")
        
        return "\n".join(f"  {part}" for part in parts) if parts else "  (추출된 정보 없음)"
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "actors": self.actors,
            "genres": self.genres,
            "years": self.years,
            "directors": self.directors,
            "movie_titles": self.movie_titles,
            "regions": self.regions,
            "story_keywords": self.story_keywords,
            "other_keywords": self.other_keywords
        }


 


class QwenBasedNER:
    """Qwen LLM 기반 Named Entity Recognition 모델"""
    
    def __init__(self, config: Optional[NERConfig] = None, yaml_path: Optional[str] = None):
        """
        QwenBasedNER 초기화
        
        Args:
            config: NERConfig 객체 (None이면 YAML에서 로드)
            yaml_path: YAML 파일 경로 (config가 None일 때 사용)
        """
        # 설정 로드
        if config is None:
            self.config = NERConfig.from_yaml(yaml_path)
        else:
            self.config = config
        
        # 모델명 검증
        if self.config.model_name not in self.config.allowed_models:
            raise ValueError(
                f"허용된 모델명만 입력할 수 있습니다: {self.config.allowed_models}. "
                f"입력된 값: '{self.config.model_name}'"
            )
        
        self.model_name = self.config.model_name
        self._load_models()
    
    def _load_models(self):
        """모델 및 토크나이저 로드"""
        logger.info(f"🔄 모델 로드 중: {self.model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        # 패딩 토큰 미설정 시 EOS로 지정하여 패딩 관련 경고/비용 최소화
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # 디바이스 및 dtype 설정
        # - CUDA: float16 + device_map="auto"
        # - MPS(Apple Silicon): float16 권장 (bfloat16은 성능 저하 가능) + device_map="auto"
        # - CPU: float32 + device_map=None
        use_cuda = torch.cuda.is_available()
        use_mps = torch.backends.mps.is_available()
        if use_cuda:
            dtype = torch.float16
            device_map = "auto"
        elif use_mps:
            dtype = torch.float16
            # 가속기 자동 매핑(기본) 또는 단일 MPS 디바이스 강제(옵션)
            device_map = None if getattr(self.config, 'mps_single_device', False) else "auto"
        else:
            dtype = torch.float32
            device_map = None  # CPU에서는 전체를 CPU로 로드

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=dtype,
            device_map=device_map,
            low_cpu_mem_usage=True,  # 메모리 최적화
            # trust_remote_code=True,  # Qwen 전용 최적화를 사용할 때 활성화 고려(환경 보안 정책 확인 필요)
        )
        # MPS 단일 디바이스 강제 시 전체를 MPS로 이동 (메모리 여유 필요)
        if use_mps and getattr(self.config, 'mps_single_device', False):
            self.model.to('mps')
        self.model.eval()

        logger.info("✅ 모델 로드 완료")
    
    def _parse_and_format_response(self, response: str, verbose: bool = True) -> NERResult:
        """
        모델 응답을 파싱하고 포맷팅
        
        Args:
            response: 모델의 원본 응답 문자열
            verbose: 상세 출력 여부
            
        Returns:
            NERResult 객체
        """
        if verbose:
            print("\n🎬 모델 응답:")
            print(response)

        # JSON 파싱 (NER 결과 추출)
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        
        if json_match:
            try:
                extracted_dict = json.loads(json_match.group())
                
                # 딕셔너리를 NERResult로 변환
                ner_result = NERResult.from_dict(extracted_dict)
                
                if verbose:
                    print("\n📊 추출된 정보 (구조화된 데이터):")
                    print(json.dumps(ner_result.to_dict(), ensure_ascii=False, indent=2))
                    
                    # 개별 필드 출력
                    print("\n📋 상세 정보:")
                    print(ner_result)
                
                if verbose:
                    print("\n✅ 완료!")
                
                return ner_result
                
            except json.JSONDecodeError as e:
                logger.error(f"⚠️ JSON 파싱 실패: {e}")
                if verbose:
                    print(f"\n⚠️ JSON 파싱 실패: {e}")
                    print("원본 응답을 확인하세요.")
                return NERResult()
        else:
            logger.warning("⚠️ JSON 형식의 응답을 찾을 수 없습니다.")
            if verbose:
                print("\n⚠️ JSON 형식의 응답을 찾을 수 없습니다.")
            return NERResult()
    
    def run(self, text: str, verbose: bool = True) -> NERResult:
        """
        텍스트에서 엔티티 추출
        
        Args:
            text: 사용자 쿼리 텍스트
            verbose: 상세 출력 여부
            
        Returns:
            NERResult 객체 (추출된 엔티티 정보)
        """
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": text},
        ]
        
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
                
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # 텍스트 생성
        if verbose:
            logger.info("⚡ 텍스트 생성 중... (이 작업은 몇 분 걸릴 수 있습니다)")
        
        with torch.inference_mode():
            # generate 인자 구성 (조기 종료 제거)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.config.max_new_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                do_sample=self.config.do_sample,
                pad_token_id=self.tokenizer.eos_token_id,
                use_cache=True,
                return_dict_in_generate=False,
                output_scores=False,
            )
        
        # 결과 디코딩
        response = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[-1]:], 
            skip_special_tokens=True
        )
        
        # 후처리: JSON 파싱 및 포맷팅
        return self._parse_and_format_response(response, verbose)


# 사용 예시
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # YAML 파일에서 설정 로드
    config = NERConfig.from_yaml()
    
    # NER 모델 초기화
    ner = QwenBasedNER(config=config)
    
    # 테스트 쿼리
    test_query = "박정민이 나오는 영화 중에 로맨스 영화 추천해줘"
    print(f"\n🔍 쿼리: {test_query}\n")
    
    # 엔티티 추출
    result = ner.run(test_query, verbose=True)
    
    # NERResult 객체로 접근 예시
    print("\n" + "="*50)
    print("📝 NERResult 객체 사용 예시")
    print("="*50)
    print(f"배우 목록: {result.actors}")
    print(f"장르 목록: {result.genres}")
    print(f"연도 목록: {result.years}")
    print(f"감독 목록: {result.directors}")
    print(f"\n전체 정보:\n{result}")
