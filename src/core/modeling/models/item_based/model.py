"""
Item-Based Collaborative Filtering 영화 추천 시스템 파이프라인
"""

import logging
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.sparse import csr_matrix, lil_matrix
from sklearn.metrics.pairwise import cosine_similarity

# 프로젝트 루트를 sys.path에 추가 (직접 실행 시 필요)
# 현재 파일: modeling/models/svd/model.py
# 프로젝트 루트: modeling/의 부모 디렉토리
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent  # svd -> models -> modeling -> project_root
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from core.modeling.utils.data import preprocess_id_mapping

# Logger 설정
logger = logging.getLogger(__name__)


class ItemBasedModel:
    """
    Item-Based Collaborative Filtering 추천 시스템

    주요 기능:
    - 아이템 간 유사도 행렬 계산 (코사인 유사도)
    - Top-K 유사도 최적화 (메모리 효율성)
    - 유사한 영화 추천
    - 모델 저장/로드
    """

    def __init__(self, config: dict):
        """
        Args:
            config: 모델 설정 (None이면 기본값 사용)
        """
        self.config = config
        self.item_similarity_matrix = None
        self.id_mapping = None

        logger.info("✅ ItemBasedModel 초기화 완료")
        logger.info(str(self.config))

    def fit(self, df_filtered: pd.DataFrame = None):
        """
        학습 데이터로 아이템 유사도 행렬 생성

        Args:
            df_filtered: 평점 데이터프레임 (None이면 자동 로드)
        """
        logger.info("\n" + "=" * 50)
        logger.info("📊 Item-Based CF 학습 시작")
        logger.info("=" * 50)

        logger.info("ID 매핑 중...")
        df_mapped, self.id_mapping = preprocess_id_mapping(df_filtered, verbose=True)

        # 4. 유사도 행렬 생성
        logger.info("아이템 유사도 행렬 생성 중...")
        self._build_similarity_matrix(df_mapped)

        logger.info("\n" + "=" * 50)
        logger.info("✅ 학습 완료!")
        logger.info("=" * 50)

    def _build_similarity_matrix(self, df_mapped: pd.DataFrame):
        """아이템 간 유사도 행렬 생성"""
        n_users = df_mapped["user_idx"].nunique()
        n_movies = df_mapped["movie_idx"].nunique()

        logger.info(f"사용자-아이템 행렬 생성 중... ({n_users} x {n_movies})")

        # User-Item 행렬 생성 (Sparse Matrix)
        user_item_matrix = csr_matrix(
            (df_mapped["rating"].values, (df_mapped["user_idx"].values, df_mapped["movie_idx"].values)),
            shape=(n_users, n_movies),
        )

        # Item-User 행렬 (전치)
        item_user_matrix = user_item_matrix.T

        logger.info("코사인 유사도 계산 중...")
        start_time = time.time()

        # 아이템 간 코사인 유사도 계산
        item_similarity = cosine_similarity(item_user_matrix, dense_output=False)

        elapsed = time.time() - start_time
        logger.info(f"✅ 유사도 계산 완료 (소요 시간: {elapsed:.2f}초)")

        # Top-K 최적화
        self.item_similarity_matrix = self._build_topk_similarity(item_similarity, k=self.config.get("top_k", 500))

    def _build_topk_similarity(self, similarity_matrix, k: int):
        """
        Top-K 유사도 행렬 생성 (메모리 최적화)

        Args:
            similarity_matrix: 전체 유사도 행렬 (sparse matrix)
            k: 각 아이템당 유지할 상위 K개

        Returns:
            Top-K만 포함하는 sparse matrix
        """
        # 변환 전 크기 출력
        original_memory = similarity_matrix.data.nbytes / (1024**2)
        original_nnz = similarity_matrix.nnz

        logger.info("\n=== 변환 전 크기 ===")
        logger.info(f"  Non-zero 요소 수: {original_nnz:,}")
        logger.info(f"  메모리 크기: {original_memory:.2f} MB")
        logger.info(f"  행렬 크기: {similarity_matrix.shape}")

        n_items = similarity_matrix.shape[0]
        topk_similarity = lil_matrix(similarity_matrix.shape)

        logger.info(f"\nTop-{k} 유사도 행렬 생성 중...")
        start_time = time.time()

        for i in range(n_items):
            if i % 1000 == 0:
                logger.info(f"  진행: {i}/{n_items} ({100 * i / n_items:.1f}%)")

            row = similarity_matrix.getrow(i).toarray().flatten()
            row[i] = -1  # 자기 자신 제외

            # Top-K 선택
            if len(row) > k:
                top_k_indices = np.argpartition(row, -k)[-k:]
                top_k_indices = top_k_indices[row[top_k_indices] > 0]
            else:
                top_k_indices = np.where(row > 0)[0]

            if len(top_k_indices) > 0:
                topk_similarity[i, top_k_indices] = row[top_k_indices]

        elapsed_time = time.time() - start_time
        logger.info(f"✅ 완료! (소요 시간: {elapsed_time:.2f}초)")

        # CSR로 변환
        topk_similarity_csr = topk_similarity.tocsr()

        # 변환 후 크기 출력
        optimized_memory = topk_similarity_csr.data.nbytes / (1024**2)
        optimized_nnz = topk_similarity_csr.nnz
        logger.info("\n=== 변환 후 크기 ===")
        logger.info(f"  Non-zero 요소 수: {optimized_nnz:,}")
        logger.info(f"  메모리 크기: {optimized_memory:.2f} MB")
        logger.info(f"  행렬 크기: {topk_similarity_csr.shape}")

        # 절감률 출력
        memory_reduction = (1 - optimized_memory / original_memory) * 100
        nnz_reduction = (1 - optimized_nnz / original_nnz) * 100
        logger.info("\n=== 최적화 효과 ===")
        logger.info(f"  메모리 절감률: {memory_reduction:.2f}%")
        logger.info(f"  Non-zero 요소 감소율: {nnz_reduction:.2f}%")

        return topk_similarity_csr

    def predict(
        self,
        movie_id: str,
        top_n: int = 10,
        return_scores: bool = False,
    ):
        """
        특정 영화와 유사한 영화 추천

        Args:
            movie_id: 영화 ID (문자열)
            top_n: 추천할 영화 개수
            return_scores: 유사도 점수 포함 여부 (False면 movie_id 리스트만 반환)

        Returns:
            return_scores=True: 추천 영화 정보 DataFrame (movie_id, similarity_score)
            return_scores=False: 추천 영화 ID 리스트
        """
        if self.item_similarity_matrix is None:
            raise ValueError("모델이 학습되지 않았습니다. fit()을 먼저 실행하세요.")

        # movie_id를 movie_idx로 변환
        if movie_id not in self.id_mapping.movie_to_idx:
            logger.warning(f"❌ 영화 ID '{movie_id}'를 찾을 수 없습니다.")
            return None

        movie_idx = self.id_mapping.movie_to_idx[movie_id]

        # 유사도 추출
        similarities = self.item_similarity_matrix[movie_idx].toarray().flatten()

        # 유사도가 0보다 큰 영화들만 선택 (자기 자신 제외)
        similar_items = []
        for idx, sim in enumerate(similarities):
            if idx != movie_idx and sim > 0:
                similar_items.append((idx, sim))

        # 유사도 기준으로 정렬 (높은 순)
        similar_items.sort(key=lambda x: x[1], reverse=True)

        if len(similar_items) == 0:
            logger.warning("\n⚠️ 유사한 영화를 찾을 수 없습니다.")
            return None

        # 모든 유사 영화의 ID 추출
        movie_indices = [idx for idx, _ in similar_items]
        scores = [score for _, score in similar_items]
        recommended_movie_ids = [self.id_mapping.idx_to_movie[idx] for idx in movie_indices]

        # top_n개만 선택
        if len(recommended_movie_ids) > top_n:
            recommended_movie_ids = recommended_movie_ids[:top_n]
            scores = scores[:top_n]

        # return_scores에 따라 결과 반환
        if return_scores:
            result = pd.DataFrame({"movie_id": recommended_movie_ids, "similarity_score": scores})
            return result
        else:
            return recommended_movie_ids

    def save_model(self, filepath: str = None):
        """
        학습된 모델 저장

        Args:
            filepath: 저장할 파일 경로 (.pkl). None이면 기본 경로 사용 (model-data/item_based_model.pkl)
        """
        if filepath is None:
            default_dir = Path(__file__).parent.parent.parent.parent.parent / "assets"
            filepath = default_dir / "item_based_model.pkl"

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            "config": self.config,
            "item_similarity_matrix": self.item_similarity_matrix,
            "id_mapping": self.id_mapping,
        }

        logger.info(f"💾 모델 저장 시작: {filepath}")
        with open(filepath, "wb") as f:
            pickle.dump(model_data, f)
        logger.info(f"✅ 모델 저장 완료: {filepath}")

    @classmethod
    def load(cls, filepath: str = None, config: dict = None):
        """
        저장된 모델 로드 (클래스 메서드)

        Args:
            filepath: 저장된 파일 경로 (.pkl). None이면 기본 경로 사용 (model-data/item_based_model.pkl)
            config: 모델 설정 (None이면 저장된 config 사용)

        Returns:
            로드된 ItemBasedModel 인스턴스
        """
        if filepath is None:
            default_dir = Path(__file__).parent.parent.parent.parent.parent / "assets"
            filepath = default_dir / "item_based_model.pkl"

        filepath = Path(filepath)
        logger.info(f"📂 모델 로드 시작: {filepath}")

        with open(filepath, "rb") as f:
            model_data = pickle.load(f)

        # config 처리
        if config is None:
            config = model_data.get("config")

        # 인스턴스 생성
        instance = cls(config=config)
        instance.item_similarity_matrix = model_data.get("item_similarity_matrix")
        instance.id_mapping = model_data.get("id_mapping")

        logger.info(f"✅ 모델 로드 완료: {filepath}")
        return instance

    def save(self, filepath: str = None):
        """
        학습된 모델 저장 (save_model 별칭)

        Args:
            filepath: 저장할 파일 경로 (.pkl). None이면 기본 경로 사용
        """
        return self.save_model(filepath)


if __name__ == "__main__":
    """
    Item-Based CF 파이프라인 실행
    - 데이터 로드 (캐시 지원)
    - 모델 학습
    - 모델 저장
    - 모델 로드 테스트
    - 추천 예측 테스트
    """
    try:
        print("=" * 80)
        print("🎬 Item-Based Collaborative Filtering 파이프라인 실행")
        print("=" * 80)

        # Config 로드
        config_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "modeling.yaml"
        print(f"\n📄 Config 파일 로드: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        item_based_config = config_dict.get("item_based", {})
        print(f"  - top_k: {item_based_config.get('top_k', 500)}")
        print(f"  - verbose: {item_based_config.get('verbose', True)}")

        # 데이터 로드
        from dataloader import load_data

        df_filtered = load_data(refresh=False)

        # 모델 학습
        print("\n" + "=" * 80)
        print("📊 모델 학습 시작")
        print("=" * 80)
        model = ItemBasedModel(config=item_based_config)
        model.fit(df_filtered)

        # 모델 저장
        print("\n" + "=" * 80)
        print("💾 모델 저장")
        print("=" * 80)
        model.save()  # 기본 경로에 저장

        # 모델 로드 테스트
        print("\n" + "=" * 80)
        print("📂 모델 로드 테스트")
        print("=" * 80)
        loaded_model = ItemBasedModel.load()

        # 추천 예측 테스트
        print("\n" + "=" * 80)
        print("🎯 추천 예측 테스트")
        print("=" * 80)

        # 첫 번째 영화 ID로 추천 테스트
        if df_filtered is not None and len(df_filtered) > 0:
            test_movie_id = df_filtered["movie_id"].iloc[0]
            print(f"\n테스트 영화 ID: {test_movie_id}")

            # movie_id 리스트 반환 (return_scores=False)
            recommendations = loaded_model.predict(movie_id=test_movie_id, top_n=10, return_scores=False)
            print("\n추천 영화 ID 리스트 (상위 10개):")
            for i, movie_id in enumerate(recommendations, 1):
                print(f"  {i}. {movie_id}")

            # DataFrame 반환 (return_scores=True)
            print("\n추천 영화 점수 포함 (상위 5개):")
            recommendations_df = loaded_model.predict(movie_id=test_movie_id, top_n=5, return_scores=True)
            print(recommendations_df.to_string(index=False))

        print("\n" + "=" * 80)
        print("✅ 파이프라인 실행 완료!")
        print("=" * 80)

        # 로거 핸들러 정리
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\n⚠️  사용자에 의해 중단되었습니다.")
        # 로거 핸들러 정리
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        sys.exit(1)

    except Exception as e:
        logger.error(f"\n❌ 오류가 발생했습니다: {str(e)}", exc_info=True)
        # 로거 핸들러 정리
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        sys.exit(1)
