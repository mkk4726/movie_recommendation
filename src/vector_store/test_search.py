"""
Vector Store 검색 테스트 스크립트

FAISS 인덱스를 로드하고 다양한 검색 테스트를 수행합니다.
"""

import sys
import time
from pathlib import Path
from typing import Optional, List
from io import BytesIO

import numpy as np
import requests
from PIL import Image

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modeling.models.clip.models.base import BaseClipEncoder
from vector_store import FAISSManager, load_config

try:
    import matplotlib

    # 서버 환경에서는 Agg 백엔드 사용 (GUI 없이 이미지 생성)
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    MATPLOTLIB_AVAILABLE = True

    # 한글 폰트 설정 (우분투 환경)
    def setup_korean_font(silent=False):
        """한글 폰트 설정"""
        try:
            # 우분투에서 사용 가능한 한글 폰트 목록
            korean_fonts = [
                "NanumGothic",
                "NanumBarunGothic",
                "NanumMyeongjo",
                "Noto Sans CJK KR",
                "Noto Serif CJK KR",
                "DejaVu Sans",  # 기본 폰트 (한글 지원 안 함)
            ]

            # 시스템에 설치된 폰트 찾기
            available_fonts = [f.name for f in fm.fontManager.ttflist]

            for font_name in korean_fonts:
                if font_name in available_fonts:
                    plt.rcParams["font.family"] = font_name
                    if not silent:
                        print(f"   한글 폰트 설정: {font_name}")
                    return True

            # 한글 폰트를 찾지 못한 경우
            if not silent:
                print("   ⚠️  한글 폰트를 찾을 수 없습니다. 영어로 표시됩니다.")
                print("   💡 한글 폰트 설치: sudo apt-get install fonts-nanum")
            return False

        except Exception as e:
            if not silent:
                print(f"   ⚠️  폰트 설정 실패: {e}")
            return False

    # 폰트 설정 실행 (조용히)
    setup_korean_font(silent=True)

except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  matplotlib이 설치되지 않았습니다. 이미지 시각화 기능이 비활성화됩니다.")

try:
    import pandas as pd
    from data_scraping.common.data_loader import load_movie_data

    MOVIE_DATA_AVAILABLE = True
except ImportError:
    MOVIE_DATA_AVAILABLE = False
    print(
        "⚠️  영화 데이터 로드 모듈을 찾을 수 없습니다. 포스터 시각화가 비활성화됩니다."
    )


class VectorSearchTester:
    """벡터 검색 테스트 클래스"""

    def __init__(self, config_path: Optional[str] = None):
        """
        초기화

        Args:
            config_path: 설정 파일 경로 (None이면 기본 config.yaml 사용)
        """
        # 설정 로드
        self.config = load_config(config_path)

        # FAISS 매니저 초기화
        print("=" * 80)
        print("FAISS 인덱스 로드 중...")
        print("=" * 80)

        self.manager = FAISSManager(config=self.config)
        self.manager.load()

        print(f"✅ 인덱스 로드 완료: {self.manager.total_vectors:,}개 벡터")
        print(f"   벡터 차원: {self.config['vector']['dim']}")
        print(f"   거리 메트릭: {self.config['vector']['distance_metric']}")

        # CLIP 인코더 초기화 (선택적)
        self.encoder = None

        # 영화 데이터 로드 (선택적)
        self.movie_df = None
        self.movie_ids = None  # FAISS 인덱스 -> movie_id 매핑

    def load_movie_data(self):
        """영화 데이터 로드 (포스터 URL 매핑용)"""
        if not MOVIE_DATA_AVAILABLE:
            print("\n⚠️  영화 데이터 로드 모듈을 사용할 수 없습니다.")
            print(
                "   pandas 또는 data_scraping.common.data_loader를 import할 수 없습니다."
            )
            return

        print("\n영화 데이터 로드 중...")
        try:
            self.movie_df = load_movie_data()
            print(f"✅ 영화 데이터 로드 완료: {len(self.movie_df):,}개")

            # 포스터 통계만 출력 (필터링하지 않음 - movie_id로 검색해야 하므로)
            poster_count = len(self.movie_df[self.movie_df["poster_path"].notna()])
            print(f"   포스터가 있는 영화: {poster_count:,}개")

        except Exception as e:
            print(f"❌ 영화 데이터 로드 실패: {e}")
            import traceback

            traceback.print_exc()
            return

        # movie_ids.json 로드 (FAISS 인덱스 -> movie_id 매핑)
        import json

        # config에서 base_dir 가져오기
        base_dir_str = self.config["index"]["base_dir"]
        base_dir = Path(base_dir_str)

        # 상대 경로인 경우 프로젝트 루트 기준으로 절대 경로 생성
        if not base_dir.is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            base_dir = project_root / base_dir

        movie_ids_path = base_dir / "movie_ids.json"

        print(f"\nmovie_ids 매핑 로드 중...")
        print(f"  경로: {movie_ids_path}")
        print(f"  존재: {movie_ids_path.exists()}")

        if movie_ids_path.exists():
            with open(movie_ids_path, "r") as f:
                self.movie_ids = json.load(f)
            print(f"✅ movie_ids 매핑 로드 완료: {len(self.movie_ids):,}개")
        else:
            print(f"⚠️  movie_ids.json 파일을 찾을 수 없습니다: {movie_ids_path}")
            if base_dir.exists():
                print(f"   디렉토리 내용: {list(base_dir.iterdir())}")

    def get_poster_urls(self, indices: List[int]) -> List[Optional[str]]:
        """
        인덱스 리스트로부터 포스터 URL 가져오기

        Args:
            indices: FAISS 인덱스 리스트

        Returns:
            포스터 URL 리스트 (없으면 None)
        """
        if self.movie_df is None or self.movie_ids is None:
            print("⚠️  movie_df 또는 movie_ids가 로드되지 않았습니다.")
            return [None] * len(indices)

        poster_urls = []
        for faiss_idx in indices:
            # FAISS 인덱스 -> movie_id 변환
            if faiss_idx < len(self.movie_ids):
                movie_id = self.movie_ids[faiss_idx]

                # movie_id 타입 확인 및 변환 (int -> str 또는 그 반대)
                # movie_df의 movie_id 컬럼 타입에 맞춰 변환
                if len(self.movie_df) > 0:
                    df_movie_id_type = type(self.movie_df.iloc[0]["movie_id"])
                    if df_movie_id_type == str and not isinstance(movie_id, str):
                        movie_id = str(movie_id)
                    elif df_movie_id_type == int and not isinstance(movie_id, int):
                        movie_id = int(movie_id)

                # movie_id로 영화 데이터 찾기
                movie_row = self.movie_df[self.movie_df["movie_id"] == movie_id]

                if not movie_row.empty:
                    poster_path = movie_row.iloc[0].get("poster_path")
                    if poster_path and pd.notna(poster_path):
                        poster_url = f"https://image.tmdb.org/t/p/w300/{poster_path}"
                        poster_urls.append(poster_url)
                    else:
                        poster_urls.append(None)
                else:
                    poster_urls.append(None)
            else:
                poster_urls.append(None)

        return poster_urls

    def download_image(self, url: str, timeout: int = 5) -> Optional[Image.Image]:
        """
        URL에서 이미지 다운로드

        Args:
            url: 이미지 URL
            timeout: 타임아웃 (초)

        Returns:
            PIL Image 또는 None
        """
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
        except Exception as e:
            print(f"이미지 다운로드 실패: {url} - {e}")
        return None

    def visualize_results(
        self,
        results: List[dict],
        query_image_path: Optional[str] = None,
        query_text: Optional[str] = None,
        max_display: int = 10,
        cols: int = 5,
    ):
        """
        검색 결과를 이미지 그리드로 시각화

        Args:
            results: 검색 결과 리스트
            query_image_path: 쿼리 이미지 경로 (있으면 함께 표시)
            query_text: 쿼리 텍스트 (파일명에 포함)
            max_display: 최대 표시 개수
            cols: 그리드 열 수
        """
        if not MATPLOTLIB_AVAILABLE:
            print("\n⚠️  matplotlib이 설치되지 않아 시각화할 수 없습니다.")
            return

        if self.movie_df is None:
            print("\n⚠️  영화 데이터가 로드되지 않았습니다.")
            print("   먼저 load_movie_data()를 호출하세요.")
            return

        # 표시할 결과 수 제한
        results = results[:max_display]

        # 포스터 URL 가져오기
        indices = [r["index"] for r in results]
        poster_urls = self.get_poster_urls(indices)

        # 이미지 다운로드
        print(f"\n포스터 이미지 다운로드 중... (최대 {len(results)}개)")
        print(
            f"포스터 URL 개수: {len([u for u in poster_urls if u is not None])}/{len(poster_urls)}"
        )

        images = []
        titles = []
        scores = []

        for i, (result, url) in enumerate(zip(results, poster_urls)):
            if url:
                print(f"  [{i+1}/{len(results)}] 다운로드 중: {url[:50]}...")
                img = self.download_image(url)
                if img:
                    images.append(img)
                    faiss_idx = result["index"]
                    score = result["score"]

                    # 영화 제목 가져오기 (FAISS 인덱스 -> movie_id -> 제목)
                    if faiss_idx < len(self.movie_ids):
                        movie_id = self.movie_ids[faiss_idx]

                        # movie_id 타입 변환
                        if len(self.movie_df) > 0:
                            df_movie_id_type = type(self.movie_df.iloc[0]["movie_id"])
                            if df_movie_id_type == str and not isinstance(
                                movie_id, str
                            ):
                                movie_id = str(movie_id)
                            elif df_movie_id_type == int and not isinstance(
                                movie_id, int
                            ):
                                movie_id = int(movie_id)

                        movie_row = self.movie_df[self.movie_df["movie_id"] == movie_id]

                        if not movie_row.empty:
                            row = movie_row.iloc[0]
                            title = row.get("total_title") or row.get(
                                "title", f"ID: {movie_id}"
                            )
                            title = title[:30] + "..." if len(title) > 30 else title
                        else:
                            title = f"Movie ID: {movie_id}"
                    else:
                        title = f"Index: {faiss_idx}"

                    titles.append(title)
                    scores.append(score)

        if not images:
            print("⚠️  다운로드된 이미지가 없습니다.")
            return

        print(f"✅ {len(images)}개 이미지 다운로드 완료")

        # 그리드 레이아웃 계산
        n_images = len(images)
        rows = (n_images + cols - 1) // cols

        # 쿼리 이미지가 있으면 추가 행 필요
        if query_image_path:
            rows += 1

        print(f"\n그리드 레이아웃: {rows}행 × {cols}열 (이미지 {n_images}개)")

        # 플롯 생성
        try:
            # 한글 폰트 설정 확인 (시각화 시점에만 메시지 출력)
            if MATPLOTLIB_AVAILABLE:
                # 우분투에서 사용 가능한 한글 폰트 목록
                korean_fonts = [
                    "NanumGothic",
                    "NanumBarunGothic",
                    "NanumMyeongjo",
                    "Noto Sans CJK KR",
                    "Noto Serif CJK KR",
                ]

                # 시스템에 설치된 폰트 찾기
                available_fonts = [f.name for f in fm.fontManager.ttflist]

                font_found = False
                for font_name in korean_fonts:
                    if font_name in available_fonts:
                        plt.rcParams["font.family"] = font_name
                        print(f"   한글 폰트 설정: {font_name}")
                        font_found = True
                        break

                if not font_found:
                    print("   ⚠️  한글 폰트를 찾을 수 없습니다. 영어로 표시됩니다.")
                    print("   💡 한글 폰트 설치: sudo apt-get install fonts-nanum")

            fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 4))

            # axes를 항상 2차원 배열로 변환
            if not isinstance(axes, np.ndarray):
                # 단일 subplot인 경우
                axes = np.array([[axes]])
            elif axes.ndim == 1:
                # 1차원 배열인 경우
                if rows == 1:
                    axes = axes.reshape(1, -1)
                else:
                    axes = axes.reshape(-1, 1)

            print(f"axes shape: {axes.shape}")

            # 쿼리 이미지 표시 (있으면)
            start_row = 0
            if query_image_path:
                try:
                    query_img = Image.open(query_image_path)
                    query_col = cols // 2
                    axes[0, query_col].imshow(query_img)
                    axes[0, query_col].set_title(
                        "Query Image", fontsize=12, fontweight="bold"
                    )
                    axes[0, query_col].axis("off")

                    # 나머지 칸 비우기
                    for c in range(cols):
                        if c != query_col:
                            axes[0, c].axis("off")

                    start_row = 1
                    print(f"쿼리 이미지 표시 완료 (행 0, 열 {query_col})")
                except Exception as e:
                    print(f"쿼리 이미지 로드 실패: {e}")

            # 검색 결과 표시
            print(f"검색 결과 이미지 표시 시작...")
            for i, (img, title, score) in enumerate(zip(images, titles, scores)):
                row = start_row + i // cols
                col = i % cols

                try:
                    axes[row, col].imshow(img)
                    axes[row, col].set_title(f"{title}\nScore: {score:.4f}", fontsize=9)
                    axes[row, col].axis("off")
                except Exception as e:
                    print(f"  이미지 {i+1} 표시 실패 (행 {row}, 열 {col}): {e}")

            # 빈 칸 숨기기
            total_cells = rows * cols
            filled_cells = n_images + (1 if query_image_path else 0)
            for i in range(filled_cells, total_cells):
                row = i // cols
                col = i % cols
                if row < rows and col < cols:
                    try:
                        axes[row, col].axis("off")
                    except:
                        pass

            plt.tight_layout()

            # 파일명 생성 (쿼리 텍스트 포함)
            import re
            from datetime import datetime

            if query_text:
                # 파일명에 사용할 수 없는 문자 제거 및 길이 제한
                safe_text = re.sub(r"[^\w\s-]", "", query_text)
                safe_text = safe_text.replace(" ", "_")[
                    :30
                ]  # 공백을 언더스코어로, 30자 제한
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"search_results_{safe_text}_{timestamp}.png"
            elif query_image_path:
                # 이미지 파일명에서 추출
                img_name = Path(query_image_path).stem
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"search_results_image_{img_name}_{timestamp}.png"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"search_results_{timestamp}.png"

            output_path = Path(__file__).parent / filename
            output_path = output_path.resolve()  # 절대 경로로 변환

            print(f"\n이미지 저장 중: {output_path}")
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close(fig)  # 메모리 정리

            # 파일이 실제로 생성되었는지 확인
            if output_path.exists():
                file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                print(f"✅ 시각화 완료!")
                print(f"   파일 경로: {output_path}")
                print(f"   파일 크기: {file_size:.2f} MB")
                if query_text:
                    print(f"   쿼리: {query_text}")
                print(f"\n💡 서버 환경에서는 이미지 파일을 다운로드하거나")
                print(f"   로컬에서 확인할 수 있습니다:")
                print(f"   - 절대 경로: {output_path}")
                print(f"   - 파일명: {filename}")
            else:
                print(f"❌ 파일 저장 실패: {output_path}가 생성되지 않았습니다.")

        except Exception as e:
            print(f"❌ 시각화 중 오류 발생: {e}")
            import traceback

            traceback.print_exc()

    def load_encoder(self, model_key: str = "jina-clip"):
        """
        CLIP 인코더 로드

        Args:
            model_key: 모델 키 (jina-clip, openai-b32 등)
        """
        print(f"\nCLIP 인코더 로드 중... (모델: {model_key})")
        self.encoder = BaseClipEncoder(model_key=model_key)
        print(f"✅ 인코더 로드 완료 (디바이스: {self.encoder.device})")

    def test_random_search(self, k: int = 10, num_queries: int = 5):
        """
        랜덤 벡터로 검색 성능 테스트

        Args:
            k: 검색할 결과 수
            num_queries: 테스트할 쿼리 수
        """
        print("\n" + "=" * 80)
        print(f"랜덤 벡터 검색 테스트 (k={k}, queries={num_queries})")
        print("=" * 80)

        vector_dim = self.config["vector"]["dim"]
        total_time = 0

        for i in range(num_queries):
            # 랜덤 쿼리 벡터 생성 (정규화)
            query_vector = np.random.randn(vector_dim).astype("float32")
            query_vector = query_vector / np.linalg.norm(query_vector)

            # 검색 수행
            start_time = time.time()
            results = self.manager.search(query_vector, k=k)
            elapsed = time.time() - start_time
            total_time += elapsed

            print(f"\n쿼리 {i+1}:")
            print(f"  검색 시간: {elapsed*1000:.2f}ms")
            print(f"  결과 수: {len(results)}개")

            # 상위 3개 결과 출력
            for j, result in enumerate(results[:3], 1):
                idx = result["index"]
                score = result["score"]
                print(f"    {j}. index={idx:6d}, score={score:.4f}")

        avg_time = total_time / num_queries
        print(f"\n평균 검색 시간: {avg_time*1000:.2f}ms")
        print(f"초당 쿼리 수: {1/avg_time:.1f} QPS")

    def test_image_search(self, image_path: str, k: int = 10, visualize: bool = True):
        """
        이미지로 검색 테스트

        Args:
            image_path: 이미지 파일 경로
            k: 검색할 결과 수
            visualize: 결과를 시각화할지 여부
        """
        if self.encoder is None:
            print("\n⚠️  CLIP 인코더가 로드되지 않았습니다.")
            print("   먼저 load_encoder()를 호출하세요.")
            return

        print("\n" + "=" * 80)
        print(f"이미지 검색 테스트: {image_path}")
        print("=" * 80)

        # 이미지 인코딩
        print("\n이미지 인코딩 중...")
        start_time = time.time()
        embedding = self.encoder.encode_image_from_path(image_path)
        encoding_time = time.time() - start_time
        print(f"✅ 인코딩 완료: {encoding_time*1000:.2f}ms")

        # 검색 수행
        query_vector = embedding.cpu().numpy().flatten()
        start_time = time.time()
        results = self.manager.search(query_vector, k=k)
        search_time = time.time() - start_time

        print(f"✅ 검색 완료: {search_time*1000:.2f}ms")
        print(f"\n상위 {len(results)}개 결과:")

        for i, result in enumerate(results, 1):
            idx = result["index"]
            score = result["score"]
            print(f"  {i:2d}. index={idx:6d}, score={score:.4f}")

        total_ms = (encoding_time + search_time) * 1000
        print(f"\n총 처리 시간: {total_ms:.2f}ms")

        # 시각화
        if visualize:
            query_text = Path(image_path).stem if image_path else None
            self.visualize_results(
                results, query_image_path=image_path, query_text=query_text
            )

        return results

    def test_text_search(self, text: str, k: int = 10, visualize: bool = True):
        """
        텍스트로 검색 테스트

        Args:
            text: 검색 텍스트
            k: 검색할 결과 수
            visualize: 결과를 시각화할지 여부
        """
        if self.encoder is None:
            print("\n⚠️  CLIP 인코더가 로드되지 않았습니다.")
            print("   먼저 load_encoder()를 호출하세요.")
            return

        print("\n" + "=" * 80)
        print(f"텍스트 검색 테스트: '{text}'")
        print("=" * 80)

        # 텍스트 인코딩
        print("\n텍스트 인코딩 중...")
        start_time = time.time()
        embedding = self.encoder.encode_text(text)
        encoding_time = time.time() - start_time
        print(f"✅ 인코딩 완료: {encoding_time*1000:.2f}ms")

        # 검색 수행
        query_vector = embedding.cpu().numpy().flatten()
        start_time = time.time()
        results = self.manager.search(query_vector, k=k)
        search_time = time.time() - start_time

        print(f"✅ 검색 완료: {search_time*1000:.2f}ms")
        print(f"\n상위 {len(results)}개 결과:")

        for i, result in enumerate(results, 1):
            idx = result["index"]
            score = result["score"]
            print(f"  {i:2d}. index={idx:6d}, score={score:.4f}")

        total_ms = (encoding_time + search_time) * 1000
        print(f"\n총 처리 시간: {total_ms:.2f}ms")

        # 시각화
        if visualize:
            self.visualize_results(results, query_text=text)

        return results

    def test_batch_search(self, batch_size: int = 100, k: int = 10):
        """
        배치 검색 성능 테스트

        Args:
            batch_size: 배치 크기
            k: 검색할 결과 수
        """
        print("\n" + "=" * 80)
        print(f"배치 검색 테스트 (batch_size={batch_size}, k={k})")
        print("=" * 80)

        vector_dim = self.config["vector"]["dim"]

        # 배치 쿼리 벡터 생성
        print(f"\n{batch_size}개 랜덤 벡터 생성 중...")
        vectors = np.random.randn(batch_size, vector_dim).astype("float32")
        # 정규화
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        query_vectors = vectors / norms

        # 배치 검색 수행
        print("배치 검색 수행 중...")
        start_time = time.time()

        for i, query_vector in enumerate(query_vectors):
            self.manager.search(query_vector, k=k)

            # 진행률 표시 (10%마다)
            if (i + 1) % (batch_size // 10) == 0:
                progress = (i + 1) / batch_size * 100
                print(f"  진행률: {progress:.0f}% ({i+1}/{batch_size})")

        total_time = time.time() - start_time
        avg_time = total_time / batch_size

        print("\n✅ 배치 검색 완료")
        print(f"   총 시간: {total_time:.2f}초")
        print(f"   평균 검색 시간: {avg_time*1000:.2f}ms")
        print(f"   처리량: {batch_size/total_time:.1f} QPS")

    def test_statistics(self):
        """인덱스 통계 정보 출력"""
        print("\n" + "=" * 80)
        print("인덱스 통계 정보")
        print("=" * 80)

        print(f"\n총 벡터 수: {self.manager.total_vectors:,}개")
        print(f"벡터 차원: {self.config['vector']['dim']}")
        print(f"거리 메트릭: {self.config['vector']['distance_metric']}")

        # 인덱스 파일 정보
        index_path = self.manager.index_path
        if index_path and index_path.exists():
            file_size_mb = index_path.stat().st_size / (1024 * 1024)
            per_vector_kb = file_size_mb / self.manager.total_vectors * 1024
            print("\n인덱스 파일:")
            print(f"  경로: {index_path}")
            print(f"  크기: {file_size_mb:.2f} MB")
            print(f"  벡터당 크기: {per_vector_kb:.2f} KB")


def main():
    """메인 함수"""
    print("\n🎬 Vector Store 검색 테스트\n")

    try:
        # 테스터 초기화
        tester = VectorSearchTester()

        # 통계 정보 출력
        tester.test_statistics()

        # 1. 랜덤 벡터 검색 테스트
        tester.test_random_search(k=10, num_queries=5)

        # 2. 배치 검색 테스트
        tester.test_batch_search(batch_size=100, k=10)

        # 3. 영화 데이터 로드 (시각화용)
        try:
            tester.load_movie_data()
        except Exception as e:
            print(f"\n⚠️  영화 데이터 로드 실패: {e}")
            print("   포스터 시각화 기능이 비활성화됩니다.")
            import traceback

            traceback.print_exc()

        # 4. CLIP 인코더 로드 (선택적)
        try:
            tester.load_encoder(model_key="jina-clip")

            # 5. 텍스트 검색 테스트 예제 (시각화 포함)
            test_texts = [
                "action movie with explosions",
                "romantic comedy",
                "dark thriller",
            ]

            for text in test_texts:
                tester.test_text_search(text, k=10, visualize=True)

        except Exception as e:
            print(f"\n⚠️  CLIP 인코더 로드 실패: {e}")
            print("   텍스트/이미지 검색 테스트를 건너뜁니다.")

        print("\n" + "=" * 80)
        print("✅ 모든 테스트 완료!")
        print("=" * 80)

    except FileNotFoundError as e:
        print(f"\n❌ 오류: {e}")
        print("\n먼저 인덱스를 생성하세요:")
        print("  python -m vector_store.create_vector_store")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
