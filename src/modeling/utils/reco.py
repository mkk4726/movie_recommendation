import pandas as pd
from abc import ABC, abstractmethod

class AbstractRecommenderModel(ABC):
    @abstractmethod
    def predict(self, user_id: str, movie_id: str):
        """
        user_id와 movie_id를 받아 예측 결과 객체(혹은 점수)를 반환
        """
        pass

def recommend_movies(
    user_id: str,
    recommender_model: AbstractRecommenderModel,
    df_ratings: pd.DataFrame,
    df_movies: pd.DataFrame,
    n: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    특정 user_id에 대해 아직 보지 않은 영화 중 예측 평점이 높은 n개 추천.
    - user_id: 추천 받을 유저의 id
    - recommender_model: predict(user_id, movie_id)를 갖는 추천 모델(추상클래스 상속)
    - df_ratings: 평점 데이터프레임 (user_id, movie_id, rating ...)
    - df_movies: 영화 정보 데이터프레임 (movie_id, movie_title ...)
    - n: 추천 개수
    """

    # 아직 안 본 영화 id 뽑기
    unseen_movie_ids = set(df_ratings['movie_id']) - set(df_ratings.loc[df_ratings['user_id'] == user_id, 'movie_id'])

    # 아직 안 본 영화에 대해 예측 평점 산출
    predictions = []
    for movie_id in unseen_movie_ids:
        pred = recommender_model.predict(user_id, movie_id)
        # pred.est가 있다면(예: surprise SVD), 아니면 pred 그 자체가 평점일 수도 있음
        rating = getattr(pred, 'est', pred)
        predictions.append((movie_id, rating))

    # movie_id로 타이틀 붙이기
    reco = pd.DataFrame(predictions, columns=['movie_id', 'predicted_rating'])
    reco = pd.merge(reco, df_movies, on='movie_id')

    # 본 영화 중 평점 높은 n개 (참고용)
    top_watched = (
        pd.merge(df_ratings.loc[df_ratings['user_id'] == user_id], df_movies, on='movie_id')
        .sort_values(by='rating', ascending=False)
        .head(n)
    )
    
    # 추천 n개
    recommendations = reco.sort_values(by='predicted_rating', ascending=False).head(n)
    
    return top_watched, recommendations


import surprise

class SVDRecommender(AbstractRecommenderModel):
    def __init__(self, svd: surprise.prediction_algorithms.matrix_factorization.SVD):
        self.svd = svd
    def predict(self, user_id, movie_id):
        return self.svd.predict(user_id, movie_id)