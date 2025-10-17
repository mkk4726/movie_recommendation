# 셋팅

- 랜더링 느리면 직접 정의해주기   
    크롬 드라이버 다운로드   
    https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json


# 데이터 구하는 순서

1. 고유 id를 구해야 함.
- user_id
- movie_id

2. user_id는 유저가 남긴 리뷰를 타고 들어가서 확인할 수 있음   
https://pedia.watcha.com/en-KR/users/ld0q0ldVPq6Xn    
이런 링크의 맨 마지막에 있는 값이 user id


3. movie_id는 유저가 본 영화목록이나 검색을 통해 확인할 수 있음   


# 이슈

유저 아이디가 너무 많으니까, 다 구하기는 어려움.
차라리 영화를 기준으로 리뷰들을 긁어오고, 이를 통해 아이디를 구하는게 어떨까?

근데 이러면 영화id를 알아야하는데.... 둘 중에 하나라도 일단 알아야한다.

가장 간단한 아이디어는 유저 사이트 -> 영화 레이팅 기록 -> 영화 id 구하고 -> 영화 id로 영화 들어가서 -> 리뷰 긁어와서 user id구하고
이걸 반복하는 것.