"""
Vector Store 생성 스크립트

영화 포스터 이미지를 CLIP 모델로 임베딩하고 FAISS 인덱스를 생성합니다.

Usage:
    python -m vector_store.create_vector_store
    
설정은 vector_store/config.yaml에서 수정하세요.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import requests
from tqdm import tqdm

# 프로젝트 루트를 sys.path에 추가
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 프로젝트 모듈 import (sys.path 설정 후)
from modeling.models.clip.models.jina import JinaClipEncoder  # noqa: E402
from data_scraping.common.data_loader import load_movie_data  # noqa: E402
from vector_store.build_index import IndexBuilder  # noqa: E402
from vector_store.utils.config import load_config  # noqa: E402

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VectorStoreCreator:
    """Vector Store 생성 클래스"""
    
    def __init__(self, config: Optional[dict] = None):
        """
        Args:
            config: 설정 딕셔너리 (None이면 기본 설정 사용)
        """
        self.config = config or load_config()
        self.timeout = self.config.get('build', {}).get('timeout', 10)
        
        # CLIP 인코더 초기화
        logger.info("CLIP 인코더 초기화 중...")
        self.encoder = JinaClipEncoder()
        logger.info(f"CLIP 인코더 초기화 완료 (device: {self.encoder.device})")
        
        # 인덱스 빌더 초기화
        self.builder = IndexBuilder(
            vector_dim=self.config['vector']['dim'],
            distance_metric=self.config['vector']['distance_metric']
        )
    
    def create(self, output_dir: Optional[Path] = None) -> None:
        """
        Vector Store 생성
        
        Args:
            output_dir: 출력 디렉토리 (None이면 config 사용)
        """
        # 출력 디렉토리 설정 (프로젝트 루트 기준 절대 경로)
        if output_dir is None:
            # 프로젝트 루트 기준으로 vector_store/indices 경로 생성
            base_dir_str = self.config['index']['base_dir']
            output_dir = project_root / base_dir_str
        else:
            output_dir = Path(output_dir)
            # 상대 경로인 경우 프로젝트 루트 기준으로 변환
            if not output_dir.is_absolute():
                output_dir = project_root / output_dir
        
        logger.info("=" * 80)
        logger.info("Vector Store 생성 시작")
        logger.info("=" * 80)
        
        # 1. 영화 데이터 로드
        logger.info("\n[1/3] 영화 데이터 로딩 중...")
        movie_df = load_movie_data()
        logger.info(f"총 {len(movie_df):,}개 영화 로드 완료")
        
        # 2. 포스터가 있는 영화만 필터링
        logger.info("\n[2/3] 포스터 데이터 필터링 중...")
        movie_data = movie_df[['movie_id', 'poster_path']].copy()
        movie_data = movie_data[movie_data['poster_path'].notna()].reset_index(drop=True)
        movie_data['poster_url'] = movie_data['poster_path'].apply(
            lambda x: f"https://image.tmdb.org/t/p/w300/{x}"
        )
        logger.info(f"포스터가 있는 영화: {len(movie_data):,}개")
        
        # 3. 임베딩 생성 및 인덱스 빌드
        logger.info("\n[3/3] 임베딩 생성 및 인덱스 빌드 중...")
        self._process_embeddings(movie_data)
        
        # 4. 인덱스 저장
        logger.info(f"\n인덱스 저장 중: {output_dir}")
        self.builder.save(
            output_dir=output_dir,
            index_name=self.config['index']['index_file'].replace('.index', ''),
            save_embeddings=self.config['build']['save_embeddings']
        )
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Vector Store 생성 완료!")
        logger.info("=" * 80)
    
    def _process_embeddings(self, movie_data) -> None:
        """
        영화 포스터 임베딩 생성 및 인덱스에 추가
        
        Args:
            movie_data: 영화 데이터 (movie_id, poster_url 포함)
        """
        success_count = 0
        error_count = 0
        
        # tqdm으로 진행률 표시
        with tqdm(total=len(movie_data), desc="임베딩 생성", unit="영화") as pbar:
            for idx, row in movie_data.iterrows():
                movie_id = row['movie_id']
                poster_url = row['poster_url']
                
                try:
                    # 포스터 이미지 다운로드
                    response = requests.get(poster_url, timeout=self.timeout)
                    response.raise_for_status()
                    
                    # CLIP 임베딩 생성
                    embedding = self.encoder.encode_image_from_bytes(response.content)
                    
                    # NumPy 배열로 변환 (torch tensor -> numpy)
                    embedding_np = embedding.cpu().numpy().flatten().astype('float32')
                    
                    # 인덱스에 추가
                    self.builder.add_item(
                        embedding=embedding_np,
                        movie_id=int(movie_id)
                    )
                    
                    success_count += 1
                    
                except requests.exceptions.RequestException as e:
                    logger.debug(f"영화 ID {movie_id} 다운로드 실패: {e}")
                    error_count += 1
                    
                except Exception as e:
                    logger.debug(f"영화 ID {movie_id} 처리 실패: {e}")
                    error_count += 1
                
                # 진행률 업데이트
                pbar.update(1)
                pbar.set_postfix({
                    'success': success_count,
                    'error': error_count
                })
        
        logger.info(f"\n처리 완료: 성공 {success_count:,}개, 실패 {error_count:,}개")
        
        if success_count == 0:
            raise RuntimeError("임베딩 생성에 실패했습니다. 네트워크 연결을 확인하세요.")


def main():
    """메인 함수"""
    try:
        # 설정 로드
        logger.info("설정 파일 로딩 중...")
        config = load_config()
        
        # 출력 디렉토리 (프로젝트 루트 기준 절대 경로)
        base_dir_str = config['index']['base_dir']
        output_dir = project_root / base_dir_str
        
        # Vector Store 생성
        creator = VectorStoreCreator(config=config)
        creator.create(output_dir=output_dir)
        
    except KeyboardInterrupt:
        logger.warning("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"\n\n오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

