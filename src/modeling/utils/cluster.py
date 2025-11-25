def print_cluster_profiles(user_features, n_clusters=None):
    """
    클러스터별 프로파일과 장르 선호도를 출력하는 함수

    Args:
        user_features (pd.DataFrame): 사용자 특성 데이터프레임 (cluster 컬럼 포함)
        n_clusters (int, optional): 클러스터 개수. None일 경우 데이터에서 추론.
    """
    if "cluster" not in user_features.columns:
        raise ValueError("user_features 데이터프레임에 'cluster' 컬럼이 없습니다.")

    if n_clusters is None:
        n_clusters = user_features["cluster"].nunique()

    # 클러스터별 프로파일 생성
    cluster_profiles = (
        user_features.groupby("cluster")
        .agg({"avg_rating": "mean", "std_rating": "mean", "num_ratings": "mean"})
        .round(3)
    )

    print("=" * 60)
    print("클러스터별 통계 프로파일")
    print("=" * 60)
    print(cluster_profiles)

    # 클러스터별 장르 선호도
    genre_columns = [
        col
        for col in user_features.columns
        if col not in ["user_id", "avg_rating", "std_rating", "num_ratings", "cluster"]
    ]
    cluster_genre_prefs = user_features.groupby("cluster")[genre_columns].mean()

    print("\n" + "=" * 60)
    print("클러스터별 장르 선호도 (상위 10개)")
    print("=" * 60)
    for cluster_id in range(n_clusters):
        if cluster_id in cluster_genre_prefs.index:
            top_genres = cluster_genre_prefs.loc[cluster_id].sort_values(ascending=False).head(10)
            print(f"\nCluster {cluster_id}:")
            for genre, score in top_genres.items():
                print(f"  {genre}: {score:.3f}")
