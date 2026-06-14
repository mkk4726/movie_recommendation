import random


def get_random_popular_movies(popular_movie_ids, df_movies, n_movies=10, exclude_movie_ids=None):
    """
    인기 있는 영화 중에서 랜덤하게 선택하는 함수

    Args:
        popular_movie_ids: 인기 영화 ID 리스트 (get_popular_movie_ids()로 얻은 결과)
        df_movies: 영화 정보 데이터프레임
        n_movies: 선택할 영화 개수
        exclude_movie_ids: 제외할 영화 ID들 (이미 보여준 영화들)

    Returns:
        selected_movies: 선택된 영화들의 데이터프레임
        remaining_movie_ids: 남은 인기 영화 ID들
    """
    lot_rated_movie_ids = set(popular_movie_ids)

    # 제외할 영화 ID들 제거
    if exclude_movie_ids:
        lot_rated_movie_ids = lot_rated_movie_ids - set(exclude_movie_ids)

    # 랜덤하게 선택
    if len(lot_rated_movie_ids) < n_movies:
        selected_movie_ids = list(lot_rated_movie_ids)
    else:
        selected_movie_ids = random.sample(list(lot_rated_movie_ids), n_movies)

    # 선택된 영화들의 정보 가져오기
    selected_movies = df_movies[df_movies["movie_id"].isin(selected_movie_ids)]

    # 남은 영화 ID들 업데이트
    remaining_movie_ids = lot_rated_movie_ids - set(selected_movie_ids)

    return selected_movies, remaining_movie_ids


# 테스트용 코드 (기존 코드 유지)
if __name__ == "__main__":
    from core.data_scraping.common.data_loader import load_ratings_data
    df_ratings = load_ratings_data()
    lot_rated_movie_ids = set(df_ratings.value_counts(subset="movie_id").sort_values(ascending=False).values[:200])

    # 여기 있는 영화를 보셨나요?
    selected_movie_ids = set(random.sample(lot_rated_movie_ids, 10))
    lot_rated_movie_ids = lot_rated_movie_ids - selected_movie_ids

    # 버튼 다시 누르면 기존에 보여줬던거 뺴고 뽑아서 보여주기
    selected_movie_ids = set(random.sample(lot_rated_movie_ids, 10))
