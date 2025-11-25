"""
Firebase Authentication 기반 사용자 인증 시스템
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

from .firebase_config import FirestoreCollections, get_firebase_manager

# Logger 설정
logger = logging.getLogger(__name__)


class FirebaseAuthManager:
    """Firebase Authentication 관리 클래스"""

    def __init__(self, cookies=None):
        self.firebase_manager = get_firebase_manager()
        self.db = None
        self.auth = None
        # 쿠키 매니저 초기화 (전역 인스턴스 사용)
        if cookies is None:
            raise ValueError("cookies 매개변수가 필요합니다. 전역 쿠키 인스턴스를 전달해주세요.")
        self.cookies = cookies

    def _get_firebase_services(self):
        """Firebase 서비스 가져오기"""
        if not self.firebase_manager.initialized:
            raise ValueError("Firebase가 초기화되지 않았습니다.")

        if self.db is None:
            self.db = self.firebase_manager.get_firestore()
        if self.auth is None:
            self.auth = self.firebase_manager.get_auth()

        return self.db, self.auth

    def init_session_state(self):
        """세션 상태 초기화"""
        # 쿠키가 준비되지 않았으면 대기
        if not self.cookies.ready():
            st.stop()

        # 세션 상태 초기화 (기존 값이 있으면 유지)
        if "firebase_user" not in st.session_state:
            st.session_state.firebase_user = None
        if "user_uid" not in st.session_state:
            st.session_state.user_uid = None
        if "is_logged_in" not in st.session_state:
            st.session_state.is_logged_in = False
        if "user_profile" not in st.session_state:
            st.session_state.user_profile = None
        if "auth_token" not in st.session_state:
            st.session_state.auth_token = None

        # 쿠키에서 세션 복원
        self._restore_session_from_cookies()

    def is_logged_in(self) -> bool:
        """로그인 상태 확인"""
        is_logged_in = st.session_state.get("is_logged_in", False)
        logger.info(f"로그인 상태 확인: {is_logged_in}")
        return is_logged_in

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """현재 로그인된 사용자 정보 반환"""
        if not self.is_logged_in():
            return None

        try:
            db, auth = self._get_firebase_services()

            # Firestore에서 사용자 정보 조회
            user_doc = db.collection(FirestoreCollections.USERS).document(st.session_state.user_uid).get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                return user_data
            else:
                # Firestore에 사용자 정보가 없으면 Firebase Auth에서 가져오기
                try:
                    firebase_user = auth.get_user(st.session_state.user_uid)
                    return {
                        "uid": firebase_user.uid,
                        "email": firebase_user.email,
                        "display_name": firebase_user.display_name,
                        "photo_url": firebase_user.photo_url,
                        "created_at": datetime.now().isoformat(),
                        "is_active": True,
                    }
                except Exception as e:
                    logger.error(f"Firebase Auth 사용자 조회 실패: {e}")
                    return None
        except Exception as e:
            logger.error(f"사용자 정보 조회 실패: {e}")
            return None

    def create_user_profile(self, uid: str, email: str, display_name: str = None) -> bool:
        """사용자 프로필 생성"""
        try:
            db, _ = self._get_firebase_services()

            user_data = {
                "uid": uid,
                "email": email,
                "display_name": display_name or email.split("@")[0],
                "photo_url": "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "profile_data": {
                    "preferred_genres": [],
                    "preferred_years": [],
                    "notification_settings": {"email_notifications": True, "recommendation_notifications": True},
                },
                "is_active": True,
            }

            # Firestore에 사용자 정보 저장
            db.collection(FirestoreCollections.USERS).document(uid).set(user_data)

            logger.info(f"✅ 사용자 프로필 생성 완료: {uid}")
            return True

        except Exception as e:
            logger.error(f"❌ 사용자 프로필 생성 실패: {e}")
            return False

    def update_user_profile(self, uid: str, profile_data: Dict[str, Any]) -> bool:
        """사용자 프로필 업데이트"""
        try:
            db, _ = self._get_firebase_services()

            update_data = {**profile_data, "updated_at": datetime.now().isoformat()}

            db.collection(FirestoreCollections.USERS).document(uid).update(update_data)

            logger.info(f"✅ 사용자 프로필 업데이트 완료: {uid}")
            return True

        except Exception as e:
            logger.error(f"❌ 사용자 프로필 업데이트 실패: {e}")
            return False

    def login_with_email(self, email: str, password: str) -> bool:
        """이메일/비밀번호 로그인 (클라이언트 사이드에서는 직접 구현 불가)"""
        st.warning("Firebase Auth는 클라이언트 사이드에서 직접 로그인을 지원하지 않습니다.")
        st.info("Firebase Web SDK를 사용하거나 Firebase Admin SDK로 사용자 인증을 구현해야 합니다.")
        return False

    def signup_with_email(self, email: str, password: str, display_name: str = None) -> bool:
        """이메일/비밀번호 회원가입"""
        try:
            db, auth = self._get_firebase_services()

            # 먼저 이메일 중복 체크
            try:
                auth.get_user_by_email(email)
                # 사용자가 이미 존재하는 경우
                st.error("❌ 이미 존재하는 이메일입니다.")
                st.info("다른 이메일을 사용하거나 로그인을 시도해주세요.")
                return False
            except Exception:
                # 사용자가 존재하지 않는 경우 (정상)
                pass

            # Firebase Auth에 사용자 생성
            user_record = auth.create_user(
                email=email, password=password, display_name=display_name or email.split("@")[0]
            )

            # 세션 상태 설정
            st.session_state.user_uid = user_record.uid
            st.session_state.is_logged_in = True
            st.session_state.firebase_user = {
                "uid": user_record.uid,
                "email": user_record.email,
                "display_name": user_record.display_name,
            }

            # Firestore에 사용자 프로필 생성
            self.create_user_profile(user_record.uid, user_record.email, user_record.display_name)

            logger.info(f"✅ 회원가입 성공: {user_record.email}")
            return True

        except Exception as e:
            logger.error(f"❌ 회원가입 실패: {e}")
            return False

    def login_with_email_password(self, email: str, password: str) -> bool:
        """이메일/비밀번호 로그인 (Firebase Admin SDK)"""
        try:
            db, auth = self._get_firebase_services()

            # Firebase Admin SDK로는 직접 로그인 불가
            # 대신 사용자 존재 여부 확인
            try:
                user_record = auth.get_user_by_email(email)

                # 사용자가 존재하는 경우 로그인 성공
                # 실제 비밀번호 검증은 Firebase Web SDK에서만 가능하므로
                # 여기서는 사용자 존재 여부만 확인

                # 세션 상태 설정
                st.session_state.user_uid = user_record.uid
                st.session_state.is_logged_in = True
                st.session_state.firebase_user = {
                    "uid": user_record.uid,
                    "email": user_record.email,
                    "display_name": user_record.display_name,
                }

                # 데모용 토큰 생성 및 저장
                demo_token = f"demo_token_{user_record.uid}"
                st.session_state.auth_token = demo_token

                # 쿠키에 인증 정보 저장 (세션 지속성)
                self.cookies["auth_token"] = demo_token
                self.cookies["user_uid"] = user_record.uid
                self.cookies.save()

                # 사용자 프로필이 없으면 생성
                if not self.get_current_user():
                    self.create_user_profile(user_record.uid, user_record.email, user_record.display_name)

                logger.info(f"✅ 로그인 성공: {user_record.email}")
                return True

            except Exception as e:
                logger.error(f"사용자를 찾을 수 없습니다: {e}")
                st.error("❌ 로그인에 실패했습니다.")
                st.info("이메일이 등록되지 않았습니다. 회원가입을 먼저 해주세요.")
                return False

        except Exception as e:
            logger.error(f"로그인 실패: {e}")
            return False

    def login_with_custom_token(self, custom_token: str) -> bool:
        """커스텀 토큰으로 로그인 (서버 사이드)"""
        try:
            db, auth = self._get_firebase_services()

            # 커스텀 토큰 검증 (실제 구현에서는 JWT 검증 필요)
            # 여기서는 간단한 예시
            if custom_token == "demo_token":
                # 데모용 사용자
                demo_uid = "demo_user_123"
                st.session_state.user_uid = demo_uid
                st.session_state.is_logged_in = True
                st.session_state.firebase_user = {
                    "uid": demo_uid,
                    "email": "demo@example.com",
                    "display_name": "Demo User",
                }

                # 토큰 저장
                st.session_state.auth_token = custom_token

                # 쿠키에 인증 정보 저장 (세션 지속성)
                self.cookies["auth_token"] = custom_token
                self.cookies["user_uid"] = demo_uid
                self.cookies.save()

                # 사용자 프로필이 없으면 생성
                if not self.get_current_user():
                    self.create_user_profile(demo_uid, "demo@example.com", "Demo User")

                logger.info("✅ 데모 로그인 성공")
                return True
            else:
                logger.warning("❌ 잘못된 토큰")
                return False

        except Exception as e:
            logger.error(f"로그인 실패: {e}")
            return False

    def _restore_session_from_cookies(self):
        """쿠키에서 세션 복원"""
        try:
            # 이미 로그인되어 있으면 스킵
            if st.session_state.get("is_logged_in", False):
                logger.info("이미 로그인되어 있음")
                return

            # 쿠키에서 인증 정보 확인
            auth_token = self.cookies.get("auth_token")
            user_uid = self.cookies.get("user_uid")

            logger.info(f"쿠키에서 토큰 확인: {auth_token}, UID: {user_uid}")

            # 쿠키에 인증 정보가 있는 경우
            if auth_token and user_uid:
                logger.info(f"쿠키에서 토큰 발견: {auth_token}, UID: {user_uid}")

                # 토큰이 유효한지 확인
                if auth_token.startswith("demo_token_") and user_uid:
                    logger.info(f"유효한 토큰으로 자동 로그인 시도: {auth_token}")

                    # 세션 상태 복원
                    st.session_state.auth_token = auth_token
                    st.session_state.user_uid = user_uid
                    st.session_state.is_logged_in = True

                    # 사용자 정보 복원
                    try:
                        db, _ = self._get_firebase_services()
                        user_doc = db.collection("users").document(user_uid).get()
                        if user_doc.exists:
                            user_data = user_doc.to_dict()
                            st.session_state.firebase_user = {
                                "uid": user_uid,
                                "email": user_data.get("email", ""),
                                "display_name": user_data.get("display_name", "User"),
                            }
                            logger.info("✅ Firestore에서 사용자 정보 복원 성공")
                        else:
                            # 기본 사용자 정보 설정
                            st.session_state.firebase_user = {
                                "uid": user_uid,
                                "email": "user@example.com",
                                "display_name": "User",
                            }
                            logger.info("✅ 기본 사용자 정보로 설정")
                    except Exception as e:
                        logger.warning(f"사용자 정보 복원 실패: {e}")
                        # 기본 사용자 정보로 설정
                        st.session_state.firebase_user = {
                            "uid": user_uid,
                            "email": "user@example.com",
                            "display_name": "User",
                        }
                        logger.info("✅ 기본 사용자 정보로 설정")

                    logger.info("✅ 쿠키 기반 자동 로그인 성공")
                else:
                    logger.info(f"유효하지 않은 토큰: {auth_token}")
            else:
                logger.info("쿠키에 인증 정보 없음")

        except Exception as e:
            logger.warning(f"쿠키 기반 세션 복원 실패: {e}")

    def logout(self):
        """사용자 로그아웃"""
        # 쿠키 삭제
        if "auth_token" in self.cookies:
            del self.cookies["auth_token"]
        if "user_uid" in self.cookies:
            del self.cookies["user_uid"]
        self.cookies.save()

        # 세션 상태 초기화
        st.session_state.firebase_user = None
        st.session_state.user_uid = None
        st.session_state.is_logged_in = False
        st.session_state.user_profile = None
        st.session_state.auth_token = None

        logger.info("✅ 로그아웃 완료")

    def get_user_ratings_count(self, uid: str) -> int:
        """사용자 평점 수 조회"""
        try:
            db, _ = self._get_firebase_services()

            ratings_ref = db.collection(FirestoreCollections.USER_RATINGS)
            ratings_query = ratings_ref.where("user_id", "==", uid)

            # 평점 수 계산
            ratings = list(ratings_query.stream())
            return len(ratings)

        except Exception as e:
            logger.error(f"평점 수 조회 실패: {e}")
            return 0


def show_firebase_auth_ui(cookies=None):
    """Firebase 인증 UI 표시 (사이드바 버전)"""
    if cookies is None:
        raise ValueError("cookies 매개변수가 필요합니다. 전역 쿠키 인스턴스를 전달해주세요.")

    auth_manager = FirebaseAuthManager(cookies=cookies)
    auth_manager.init_session_state()

    # 사이드바에서 UI 렌더링
    with st.sidebar:
        st.markdown("### 🔐 로그인 / 회원가입")

        if not auth_manager.firebase_manager.initialized:
            st.info("Firebase 설정이 필요합니다.")
            return

        if auth_manager.is_logged_in():
            user = auth_manager.get_current_user()
            if user:
                st.write(f"👤 **{user.get('display_name', 'User')}님**")
                st.caption(f"📧 {user.get('email', 'N/A')}")
                st.caption(f"가입일: {user.get('created_at', 'N/A')}")

                ratings_count = auth_manager.get_user_ratings_count(st.session_state.user_uid)
                st.caption(f"평점 수: {ratings_count}개")

                if st.button("로그아웃", type="secondary"):
                    auth_manager.logout()
                    st.rerun()

        else:
            # 로그인/회원가입 선택
            auth_type = st.radio("선택", ["로그인", "회원가입"], horizontal=True)

            if auth_type == "로그인":
                email = st.text_input("이메일", placeholder="example@email.com")
                password = st.text_input("비밀번호", type="password")
                if st.button("로그인"):
                    if email and password:
                        if auth_manager.login_with_email_password(email, password):
                            st.success("로그인 성공!")
                            st.rerun()
                        else:
                            st.error("로그인 실패: 이메일 또는 비밀번호를 확인하세요.")
                    else:
                        st.warning("이메일과 비밀번호를 입력하세요.")

            else:  # 회원가입
                signup_email = st.text_input("이메일", placeholder="example@email.com")
                signup_password = st.text_input("비밀번호", type="password", placeholder="6자 이상 입력")
                signup_password_confirm = st.text_input("비밀번호 확인", type="password")
                signup_display_name = st.text_input("닉네임 (선택)")
                if st.button("회원가입"):
                    if signup_password != signup_password_confirm:
                        st.error("비밀번호가 일치하지 않습니다.")
                    elif len(signup_password) < 6:
                        st.error("비밀번호는 6자 이상이어야 합니다.")
                    else:
                        if auth_manager.signup_with_email(signup_email, signup_password, signup_display_name):
                            st.success("회원가입 성공!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("회원가입 실패: 이미 존재하는 이메일일 수 있습니다.")


def require_firebase_auth(cookies=None):
    """Firebase 인증 필수 데코레이터"""
    if cookies is None:
        raise ValueError("cookies 매개변수가 필요합니다. 전역 쿠키 인스턴스를 전달해주세요.")

    auth_manager = FirebaseAuthManager(cookies=cookies)
    auth_manager.init_session_state()

    if not auth_manager.is_logged_in():
        st.error("이 기능을 사용하려면 로그인이 필요합니다.")
        st.info("위의 로그인 버튼을 클릭해주세요.")
        st.stop()

    return auth_manager.get_current_user()


# 편의 함수들
def get_current_user_uid() -> Optional[str]:
    """현재 로그인된 사용자 UID 반환"""
    if st.session_state.get("is_logged_in", False):
        return st.session_state.get("user_uid")
    return None


def get_current_user_email() -> Optional[str]:
    """현재 로그인된 사용자 이메일 반환"""
    if st.session_state.get("is_logged_in", False):
        user = st.session_state.get("firebase_user", {})
        return user.get("email")
    return None


if __name__ == "__main__":
    # 테스트 코드
    st.title("Firebase Authentication 테스트")

    # 전역 CookieManager 생성
    test_cookies = EncryptedCookieManager(password="movie_recommendation_secret_key_2024", prefix="firebase_")

    auth_manager = FirebaseAuthManager(cookies=test_cookies)
    auth_manager.init_session_state()

    if auth_manager.is_logged_in():
        st.success(f"로그인됨: {auth_manager.get_current_user()}")
        if st.button("로그아웃"):
            auth_manager.logout()
            st.rerun()
    else:
        st.info("로그인이 필요합니다.")
        show_firebase_auth_ui(cookies=test_cookies)
