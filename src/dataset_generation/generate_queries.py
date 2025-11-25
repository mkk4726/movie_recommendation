#!/usr/bin/env python3
"""
영화 데이터셋에 대한 쿼리 생성 배치 스크립트

Usage:
    python generate_queries.py

    # nohup으로 백그라운드 실행:
    nohup python generate_queries.py > generate_queries.log 2>&1 &
"""

import logging
import os
import sys
from datetime import datetime

from tqdm import tqdm

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("generate_queries_batch.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dataset_generation.llm import LLM
from dataset_generation.query_generator import QueryGenerator
from dataset_generation.utils import (
    append_query_to_jsonl,
    get_queries_file_path,
    load_queries_from_jsonl,
    parse_row_to_dict,
)
from src.data_scraping.common import load_movie_cast, load_movie_data


def main():
    """메인 실행 함수"""
    logger.info("=" * 80)
    logger.info("쿼리 생성 배치 프로세스 시작")
    logger.info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    # 1. LLM 모델 로드
    logger.info("[1/5] LLM 모델 로드 중...")
    try:
        llm = LLM()
        query_generator = QueryGenerator(llm=llm)
        logger.info("✅ LLM 모델 로드 완료")
    except Exception as e:
        logger.error(f"❌ LLM 모델 로드 실패: {e}")
        return 1

    # 2. 영화 데이터 로드
    logger.info("[2/5] 영화 데이터 로드 중...")
    try:
        movie_data = load_movie_data()
        cast_data = load_movie_cast()
        logger.info(f"✅ 영화 데이터 로드 완료: 총 {len(movie_data)}개 영화")
    except Exception as e:
        logger.error(f"❌ 영화 데이터 로드 실패: {e}")
        return 1

    # 3. 기존 생성된 쿼리 확인
    logger.info("[3/5] 기존 생성 쿼리 확인 중...")
    try:
        output_file_path = get_queries_file_path(project_root)

        # 파일이 존재하면 로드
        if os.path.exists(output_file_path):
            df_queries_existing = load_queries_from_jsonl(output_file_path)
            existing_movie_ids = set(df_queries_existing["movie_id"])
            logger.info(f"✅ 기존 쿼리 발견: {len(existing_movie_ids)}개 영화에 대한 쿼리 존재")
        else:
            existing_movie_ids = set()
            logger.info("✅ 기존 쿼리 없음. 새로 생성합니다.")
            logger.info(f"   출력 경로: {output_file_path}")

        # 처리할 영화 ID 목록 생성 (아직 쿼리가 생성되지 않은 영화들)
        all_movie_ids = set(movie_data["movie_id"])
        movie_id_list = list(all_movie_ids - existing_movie_ids)

        logger.info(f"   전체 영화: {len(all_movie_ids)}개")
        logger.info(f"   처리 완료: {len(existing_movie_ids)}개")
        logger.info(f"   처리 대상: {len(movie_id_list)}개")

    except Exception as e:
        logger.warning(f"⚠️  기존 쿼리 확인 실패: {e}")
        logger.warning("   전체 영화를 대상으로 처리합니다.")
        movie_id_list = list(movie_data["movie_id"])

    # 처리할 영화가 없으면 종료
    if len(movie_id_list) == 0:
        logger.info("✅ 모든 영화에 대한 쿼리가 이미 생성되었습니다!")
        logger.info(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return 0

    # 4. 쿼리 생성 및 저장
    logger.info(f"[4/5] 쿼리 생성 시작 (총 {len(movie_id_list)}개 영화)")
    logger.info("-" * 80)

    total_queries_generated = 0
    failed_movies = []

    try:
        for movie_id in tqdm(movie_id_list, desc="Generating queries"):
            try:
                # 영화 데이터 가져오기
                row = movie_data.loc[movie_data["movie_id"] == movie_id].squeeze()
                row_dict = parse_row_to_dict(cast_data, row)

                # QueryGenerator로 쿼리 생성
                queries = query_generator.generate_queries(row_dict)

                # 각 쿼리를 생성하자마자 바로 파일에 추가 (실시간 저장)
                for query_info in queries:
                    query_with_id = {
                        "movie_id": int(movie_id),
                        "query": query_info["query"],
                        "query_type": query_info["query_type"],
                        "language": query_info["language"],
                    }
                    append_query_to_jsonl(query_with_id, output_file_path)
                    total_queries_generated += 1

            except Exception as e:
                logger.warning(f"⚠️  Movie ID {movie_id} 처리 중 오류: {e}")
                failed_movies.append((movie_id, str(e)))
                continue

    except KeyboardInterrupt:
        logger.warning("\n⚠️  사용자에 의해 중단되었습니다.")
        logger.warning(f"지금까지 생성된 쿼리: {total_queries_generated}개")

    logger.info("-" * 80)
    logger.info(f"✅ 쿼리 생성 완료: 총 {total_queries_generated}개 쿼리 생성")

    # 5. 결과 요약
    logger.info("[5/5] 결과 요약")
    logger.info("=" * 80)
    logger.info(f"처리 대상 영화: {len(movie_id_list)}개")
    logger.info(f"성공: {len(movie_id_list) - len(failed_movies)}개")
    logger.info(f"실패: {len(failed_movies)}개")
    logger.info(f"생성된 쿼리: {total_queries_generated}개")
    logger.info(f"출력 파일: {output_file_path}")

    if failed_movies:
        logger.info("\n실패한 영화 목록:")
        for movie_id, error in failed_movies[:10]:  # 처음 10개만 표시
            logger.info(f"  - Movie ID {movie_id}: {error}")
        if len(failed_movies) > 10:
            logger.info(f"  ... 외 {len(failed_movies) - 10}개")

    logger.info(f"\n종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
