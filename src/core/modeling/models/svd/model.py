"""
SVD 모델 저장 및 로드 클래스

노트북에서 작업한 내용을 기반으로, SVD 모델의 파라미터를 효율적으로 저장하고 로드합니다.
전체 모델 객체를 저장하는 것보다 파라미터만 저장하는 방식이 훨씬 빠릅니다.
"""

import logging
import random
import sys
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import yaml
from surprise import SVD, accuracy
from surprise.trainset import Trainset

# 프로젝트 루트를 sys.path에 추가 (직접 실행 시 필요)
# 현재 파일: modeling/models/svd/model.py
# 프로젝트 루트: modeling/의 부모 디렉토리
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent  # svd -> models -> modeling -> project_root
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from core.modeling.models.svd import dataloader

# Logger 설정
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class SVDModel:
    """
    SVD 모델 저장 및 로드 클래스

    모델 파라미터를 효율적으로 저장/로드하고,
    필요시 모델 객체를 재구성합니다.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: config.yaml 파일 경로 (None이면 기본 경로 사용)
        """
        logger.info("=" * 80)
        logger.info("🔧 SVDModel 초기화 시작")

        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "modeling.yaml"
        logger.info(f"📄 Config 파일 경로: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            model_config_dict = yaml.safe_load(f)
        self.config = model_config_dict["svd"]
        self.model: Optional[SVD] = None
        self.testset: Optional[list] = None

        # Config 출력
        self._print_config()

        logger.info("✅ SVDModel 초기화 완료")
        logger.info("=" * 80)

    def _print_config(self):
        """모델 설정 출력"""
        logger.info("\n📋 모델 설정:")
        for key, value in self.config.items():
            logger.info(f"  - {key}: {value}")

    @staticmethod
    def save_params(model: SVD, filepath: Optional[Path | str] = None) -> None:
        """
        학습된 SVD 모델의 파라미터만 저장 (빠른 저장)

        Args:
            model: 학습된 SVD 모델 객체
            filepath: 저장할 파일 경로 (.npz). None이면 기본 경로 사용 (svd/model-data/svd_params.npz)
        """
        if filepath is None:
            default_dir = Path(__file__).parent.parent.parent.parent.parent / "assets"
            filepath = default_dir / "svd_params.npz"

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"💾 파라미터 저장 시작: {filepath}")

        np.savez_compressed(
            str(filepath),
            pu=model.pu,  # 사용자 잠재벡터
            qi=model.qi,  # 아이템 잠재벡터
            bu=model.bu,  # 사용자 bias
            bi=model.bi,  # 아이템 bias
            global_mean=model.trainset.global_mean,  # 전역 평균
        )
        logger.info(f"✅ SVD 파라미터 저장 완료: {filepath}")

    def create_model(self, use_total_data: bool = True) -> SVD:
        """
        SVD 모델 객체 생성 및 trainset 주입

        Args:
            use_total_data: True면 전체 데이터셋 사용, False면 train/test 분할

        Returns:
            SVD 모델 객체 (trainset 주입됨)
        """
        logger.info(f"🔨 모델 객체 생성 중... (use_total_data={use_total_data})")

        model = SVD(
            n_factors=self.config["n_factors"],
            n_epochs=self.config["n_epochs"],
            lr_all=self.config["lr_all"],
            reg_all=self.config["reg_all"],
            random_state=self.config.get("random_state", 42),
            verbose=self.config.get("verbose", True),
        )

        # trainset 주입
        if use_total_data:
            logger.info("📥 전체 데이터셋 로드 중...")
            model.trainset = dataloader.load_totalset()
            self.testset = None  # 전체 데이터 사용 시 testset 없음
        else:
            logger.info("📥 Train/Test 데이터셋 로드 중...")
            trainset, testset = dataloader.load_trainset_testset()
            model.trainset = trainset
            self.testset = testset
            logger.info(f"✅ 테스트셋 저장 완료 ({len(testset):,}개)")

        logger.info(f"✅ 모델 객체 생성 완료 (사용자: {model.trainset.n_users}, 아이템: {model.trainset.n_items})")
        self.model = model
        return model

    def load_params(self, filepath: Path | str) -> SVD:
        """
        저장된 파라미터를 로드하여 모델 재구성

        Args:
            filepath: 파라미터 파일 경로 (.npz)

        Returns:
            파라미터가 로드된 SVD 모델 객체
        """
        filepath = Path(filepath)
        logger.info(f"📂 파라미터 로드 시작: {filepath}")

        if self.model is None:
            raise ValueError("모델 객체가 생성되지 않았습니다. create_model()을 먼저 호출하세요.")

        # 파라미터 로드
        data = np.load(str(filepath))
        self.model.pu = data["pu"]
        self.model.qi = data["qi"]
        self.model.bu = data["bu"]
        self.model.bi = data["bi"]
        self.model.global_mean = data["global_mean"].item()

        logger.info(f"✅ SVD 파라미터 로드 완료: {filepath}")
        return self.model

    @classmethod
    def load(
        cls, filepath: Optional[Path | str] = None, config_path: Optional[Path] = None, use_total_data: bool = True
    ) -> SVD:
        """저장된 파라미터를 로드하여 완전한 SVD 모델 객체를 반환합니다.

        Args:
            filepath: 파라미터 파일 경로 (.npz). None이면 기본 경로 사용
            config_path: config.yaml 파일 경로 (None이면 기본 경로 사용)
            use_total_data: True면 전체 데이터셋 사용

        Returns:
            파라미터가 로드된 Surprise SVD 모델 객체
        """
        if filepath is None:
            default_dir = Path(__file__).parent.parent.parent.parent.parent / "assets"
            filepath = default_dir / "svd_params.npz"

        svd_model = cls(config_path=config_path)
        svd_model.create_model(use_total_data=use_total_data)
        return svd_model.load_params(filepath)

    @classmethod
    def load_model(
        cls, filepath: Optional[Path | str] = None, config_path: Optional[Path] = None, use_total_data: bool = True
    ) -> SVD:
        """load()의 별칭 (하위 호환)."""
        return cls.load(filepath=filepath, config_path=config_path, use_total_data=use_total_data)

    def save(self, filepath: Optional[Path | str] = None) -> None:
        """학습된 모델 파라미터를 .npz로 저장합니다.

        Args:
            filepath: 저장할 파일 경로 (.npz). None이면 기본 경로 사용
        """
        if self.model is None:
            raise ValueError("모델이 학습되지 않았습니다. fit()을 먼저 호출하세요.")
        self.save_params(self.model, filepath=filepath)

    def fit(self, trainset: Optional[Trainset] = None) -> SVD:
        """
        모델 학습

        Args:
            trainset: 학습용 trainset (None이면 self.model.trainset 사용)

        Returns:
            학습된 SVD 모델 객체
        """
        if self.model is None:
            raise ValueError("모델 객체가 생성되지 않았습니다. create_model()을 먼저 호출하세요.")

        if trainset is not None:
            self.model.trainset = trainset

        logger.info("🚀 모델 학습 시작...")
        logger.info(f"  - 사용자 수: {self.model.trainset.n_users:,}")
        logger.info(f"  - 아이템 수: {self.model.trainset.n_items:,}")
        logger.info(f"  - 평점 수: {self.model.trainset.n_ratings:,}")

        self.model.fit(self.model.trainset)

        logger.info("✅ 모델 학습 완료")
        return self.model

    def predict(self, uid: str, iid: str):
        """
        평점 예측

        Args:
            uid: 사용자 ID
            iid: 아이템 ID

        Returns:
            Prediction 객체
        """
        if self.model is None:
            raise ValueError("모델 객체가 생성되지 않았습니다.")

        return self.model.predict(uid, iid)

    def evaluate(self, testset: list, sample_size: Optional[int] = 10000, verbose: bool = True) -> Tuple[float, float]:
        """
        테스트셋으로 모델 평가 (샘플링 옵션 제공)

        Args:
            testset: 테스트셋 리스트 [(user_id, item_id, rating), ...]
            sample_size: 샘플 크기 (None이면 전체 사용)
            verbose: 평가 결과 출력 여부

        Returns:
            Tuple[float, float]: (RMSE, MAE)
        """
        if self.model is None:
            raise ValueError("모델 객체가 생성되지 않았습니다.")

        logger.info("📊 모델 평가 시작...")

        # 샘플링 (옵션)
        if sample_size is not None and len(testset) > sample_size:
            sampled_testset = random.sample(testset, sample_size)
            logger.info(f"테스트셋에서 {len(sampled_testset):,}개 샘플 추출하여 평가합니다.")
        else:
            sampled_testset = testset
            logger.info(f"전체 테스트셋 {len(sampled_testset):,}개로 평가합니다.")

        # 예측 및 평가
        logger.info("예측 중...")
        predictions = self.model.test(sampled_testset)
        rmse = accuracy.rmse(predictions, verbose=verbose)
        mae = accuracy.mae(predictions, verbose=verbose)

        logger.info("=" * 80)
        logger.info("📈 평가 결과:")
        logger.info(f"  - RMSE: {rmse:.4f}")
        logger.info(f"  - MAE:  {mae:.4f}")
        logger.info("=" * 80)

        return rmse, mae

    def fit_and_evaluate(
        self,
        trainset: Optional[Trainset] = None,
        testset: Optional[list] = None,
        sample_size: Optional[int] = 10000,
        verbose: bool = True,
    ) -> Tuple[SVD, float, float]:
        """
        모델 학습 후 자동 평가

        Args:
            trainset: 학습용 trainset (None이면 self.model.trainset 사용)
            testset: 테스트셋 (None이면 dataloader에서 로드)
            sample_size: 평가 샘플 크기 (None이면 전체 사용)
            use_total_data: testset이 None일 때, 전체 데이터셋 사용 여부
            verbose: 학습/평가 과정 출력 여부

        Returns:
            Tuple[SVD, float, float]: (학습된 모델, RMSE, MAE)
        """
        logger.info("\n" + "=" * 80)
        logger.info("🎯 학습 및 평가 파이프라인 시작")
        logger.info("=" * 80)

        # 학습
        model = self.fit(trainset=trainset)

        # testset 로드 (제공되지 않은 경우)
        if testset is None:
            # self.testset에 저장된 것이 있으면 사용 (재로드 방지)
            if self.testset is not None:
                testset = self.testset
                logger.info(f"\n✅ 저장된 테스트셋 사용 ({len(testset):,}개)")
            else:
                logger.info("\n📥 테스트셋 로드 중...")
                _, testset = dataloader.load_trainset_testset()
                logger.info(f"✅ 테스트셋 로드 완료 ({len(testset):,}개)")

        # 평가
        rmse, mae = self.evaluate(testset, sample_size=sample_size, verbose=verbose)

        logger.info("✅ 학습 및 평가 파이프라인 완료\n")
        return model, rmse, mae

    def save_params_with_totaldata(self, filepath: Optional[Path | str] = None) -> None:
        """
        파라미터 저장 전에 전체 데이터로 재학습 후 저장

        Args:
            model: 학습된 SVD 모델 객체 (train/test 분할로 학습된 모델)
            filepath: 저장할 파일 경로 (.npz). None이면 기본 경로 사용
            verbose: 과정 출력 여부
        """
        logger.info("\n" + "=" * 80)
        logger.info("🔄 전체 데이터로 재학습 시작 (최종 모델 저장 전)")
        logger.info("=" * 80)

        # 전체 데이터로 재학습
        logger.info("📥 전체 데이터셋 로드 중...")
        totalset = dataloader.load_totalset()

        logger.info("🚀 전체 데이터로 재학습 시작...")
        logger.info(f"  - 사용자 수: {totalset.n_users:,}")
        logger.info(f"  - 아이템 수: {totalset.n_items:,}")
        logger.info(f"  - 평점 수: {totalset.n_ratings:,}")

        # 새로운 모델 생성 (전체 데이터용)
        retrained_model = SVD(
            n_factors=self.config["n_factors"],
            n_epochs=self.config["n_epochs"],
            lr_all=self.config["lr_all"],
            reg_all=self.config["reg_all"],
            random_state=self.config.get("random_state", 42),
        )
        retrained_model.trainset = totalset

        # 학습
        retrained_model.fit(totalset)
        logger.info("✅ 전체 데이터 재학습 완료")

        # 저장
        logger.info("\n💾 재학습된 모델 파라미터 저장 중...")
        self.save_params(retrained_model, filepath=filepath)

        logger.info("=" * 80)
        logger.info("✅ 최종 모델 저장 완료")
        logger.info("=" * 80)


# 사용 예시
if __name__ == "__main__":
    try:
        from pathlib import Path

        # 1. 모델 생성 및 학습
        svd_model = SVDModel()
        model = svd_model.create_model(use_total_data=False)  # train/test 분할 사용

        # 2. 학습 및 평가 (자동)
        model, rmse, mae = svd_model.fit_and_evaluate(
            sample_size=10000,  # 샘플 크기 (None이면 전체)
            verbose=True,
        )

        # 3. 전체 데이터로 재학습 후 저장 (기본 경로: svd/model-data/svd_params.npz)
        svd_model.save_params_with_totaldata()
        # 또는 직접 경로 지정
        # svd_model.save_params_with_retrain(model, Path("custom/path/svd_params.npz"))

        # 4. 저장된 파라미터로 모델 로드 (기본 경로 사용)
        print("\n=== 저장된 모델 로드 ===")
        loaded_model = SVDModel.load_model(use_total_data=True)  # 기본 경로에서 로드
        # 또는 직접 경로 지정
        # loaded_model = SVDModel.load_model(
        #     filepath=Path("custom/path/svd_params.npz"),
        #     use_total_data=True
        # )

        # 5. 예측 사용
        print("\n=== 예측 테스트 ===")
        prediction = loaded_model.predict(uid="123", iid="456")
        print(f"예측 평점: {prediction.est:.2f}")

        # 6. 인스턴스 메서드로도 사용 가능
        print("\n=== 인스턴스 메서드 사용 ===")
        svd_model2 = SVDModel()
        svd_model2.create_model(use_total_data=True)
        svd_model2.load_params(Path(__file__).parent / "model-data" / "svd_params.npz")  # 직접 경로 지정 필요
        prediction2 = svd_model2.predict(uid="789", iid="012")
        print(f"예측 평점: {prediction2.est:.2f}")

        # 모든 작업 완료 후 종료
        logger.info("\n" + "=" * 80)
        logger.info("✅ 모든 작업이 완료되었습니다. 프로그램을 종료합니다.")
        logger.info("=" * 80)

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
