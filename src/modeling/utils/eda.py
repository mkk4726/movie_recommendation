import matplotlib.pyplot as plt
import seaborn as sns
import warnings

def explore_user_ratings(df_ratings, verbose=True):
    """
    사용자별/영화별 평점 수, 평균 평점의 통계와 분포를 시각화하는 함수
    """
    # Ignore matplotlib font warnings
    warnings.filterwarnings("ignore", category=UserWarning, module='matplotlib')

    # Show statistics for number of ratings per user
    user_rating_counts = df_ratings.groupby('user_id').size().reset_index(name='count')
    if verbose:
        print("\n[사용자별 평점 수 통계(describe)]")
        print(user_rating_counts.describe())
    
    # Visualization: distribution of number of ratings per user
    plt.figure(figsize=(10,5))
    sns.histplot(user_rating_counts['count'], bins=40, kde=True)
    plt.title('Distribution of Number of Ratings per User')
    plt.xlabel('Number of Ratings')
    plt.ylabel('User Count')
    plt.show()

    # Show statistics for mean rating per user
    user_mean_ratings = df_ratings.groupby('user_id')['rating'].mean().reset_index(name='mean_rating')
    if verbose:
        print("\n[사용자별 평균 평점 통계(describe)]")
        print(user_mean_ratings.describe())
    
    # Visualization: distribution of mean ratings per user
    plt.figure(figsize=(10,5))
    sns.histplot(user_mean_ratings['mean_rating'], bins=40, kde=True)
    plt.title('Distribution of Mean Ratings per User')
    plt.xlabel('Mean Rating')
    plt.ylabel('User Count')
    plt.show()

    # Show statistics for number of ratings per movie
    movie_rating_counts = df_ratings.groupby('movie_id').size().reset_index(name='count')
    if verbose:
        print("\n[영화별 평점 수 통계(describe)]")
        print(movie_rating_counts.describe())
    
    # Visualization: distribution of number of ratings per movie
    plt.figure(figsize=(10,5))
    sns.histplot(movie_rating_counts['count'], bins=40, kde=True)
    plt.title('Distribution of Number of Ratings per Movie')
    plt.xlabel('Number of Ratings')
    plt.ylabel('Movie Count')
    plt.show()

    # Show statistics for mean rating per movie
    movie_mean_ratings = df_ratings.groupby('movie_id')['rating'].mean().reset_index(name='mean_rating')
    if verbose:
        print("\n[영화별 평균 평점 통계(describe)]")
        print(movie_mean_ratings.describe())
    
    # Visualization: distribution of mean ratings per movie
    plt.figure(figsize=(10,5))
    sns.histplot(movie_mean_ratings['mean_rating'], bins=40, kde=True)
    plt.title('Distribution of Mean Ratings per Movie')
    plt.xlabel('Mean Rating')
    plt.ylabel('Movie Count')
    plt.show()