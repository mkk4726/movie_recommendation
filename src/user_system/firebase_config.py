"""
Firebase 설정 및 초기화
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    from firebase_admin import credentials
    from google.cloud import firestore as google_firestore
except ImportError:
    st.error("Firebase 라이브러리가 설치되지 않았습니다. 'pip install firebase-admin'을 실행해주세요.")
    st.stop()

# Logger 설정
logger = logging.getLogger(__name__)


class FirebaseManager:
    """Firebase 관리 클래스"""

    def __init__(self):
        self.app = None
        self.db = None
        self.initialized = False

    def initialize(self, service_account_path: Optional[str] = None):
        """Firebase 초기화"""
        try:
            # 이미 초기화된 경우
            if self.initialized:
                logger.info("Firebase가 이미 초기화되어 있습니다.")
                return True

            # 서비스 계정 키 파일 경로
            if service_account_path is None:
                service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

            # 자동으로 서비스 계정 키 파일 찾기
            if not service_account_path or not os.path.exists(service_account_path):
                # 프로젝트 루트에서 Firebase 서비스 계정 키 파일 찾기
                project_root = Path(__file__).parent.parent.resolve()
                possible_paths = [
                    project_root / "movie-recommendation-5bf7f-firebase-adminsdk-fbsvc-9818879c1d.json",
                    project_root / "firebase-service-account.json",
                    project_root / "service-account-key.json",
                    project_root / "firebase-adminsdk.json",
                ]

                logger.info(f"서비스 계정 키 파일 찾는 중... 프로젝트 루트: {project_root}")
                for path in possible_paths:
                    logger.info(f"확인 중: {path} (존재: {path.exists()})")
                    if path.exists():
                        service_account_path = str(path)
                        logger.info(f"✅ Firebase 서비스 계정 키 파일 발견: {service_account_path}")
                        break

            if not service_account_path or not os.path.exists(service_account_path):
                error_msg = "Firebase 서비스 계정 키 파일이 필요합니다."
                logger.error(error_msg)
                if st:
                    st.error(error_msg)
                    st.info("Firebase Console에서 서비스 계정 키를 다운로드하고 경로를 설정해주세요.")

                    # 환경변수 설정 안내
                    st.code("""
# 환경변수 설정
export FIREBASE_SERVICE_ACCOUNT_PATH="/path/to/your/service-account-key.json"
                    """)
                return False

            # 서비스 계정에서 프로젝트 ID 추출
            logger.info(f"서비스 계정 키 파일 읽는 중: {service_account_path}")
            with open(service_account_path, "r") as f:
                service_account_data = json.load(f)
                project_id = service_account_data.get("project_id")

            if not project_id:
                error_msg = "서비스 계정 키 파일에서 project_id를 찾을 수 없습니다."
                logger.error(error_msg)
                if st:
                    st.error(error_msg)
                return False

            logger.info(f"프로젝트 ID: {project_id}")

            # Firebase 앱 초기화
            if not firebase_admin._apps:
                logger.info("Firebase Admin 앱 초기화 중...")
                cred = credentials.Certificate(service_account_path)

                # projectId와 databaseId를 명시적으로 지정하여 초기화
                try:
                    self.app = firebase_admin.initialize_app(
                        cred,
                        {
                            "projectId": project_id,
                            "databaseId": "(default)",  # 명시적으로 default 데이터베이스 지정
                        },
                    )
                    logger.info(
                        f"✅ Firebase Admin 앱 초기화 완료 - 프로젝트 ID: {project_id}, 데이터베이스 ID: (default)"
                    )
                except Exception as init_error:
                    error_msg = f"Firebase Admin 앱 초기화 실패: {init_error}"
                    logger.error(error_msg, exc_info=True)
                    if st:
                        st.error(error_msg)
                    return False
            else:
                logger.info("Firebase Admin 앱이 이미 초기화되어 있습니다.")

            # Firestore 클라이언트 초기화 (google.cloud.firestore 직접 사용)
            # 서비스 계정 키를 사용하여 인증
            logger.info("Firestore 클라이언트 초기화 중...")
            try:
                from google.oauth2 import service_account

                firestore_credentials = service_account.Credentials.from_service_account_file(service_account_path)
                self.db = google_firestore.Client(
                    project=project_id, database="(default)", credentials=firestore_credentials
                )
                logger.info("✅ Firestore 클라이언트 초기화 완료")
            except Exception as firestore_error:
                error_msg = f"Firestore 클라이언트 초기화 실패: {firestore_error}"
                logger.error(error_msg, exc_info=True)
                if st:
                    st.error(error_msg)
                return False

            self.initialized = True
            logger.info("✅ Firebase 전체 초기화 완료")
            return True

        except json.JSONDecodeError as e:
            error_msg = f"서비스 계정 키 파일 JSON 파싱 실패: {e}"
            logger.error(error_msg, exc_info=True)
            if st:
                st.error(error_msg)
                st.info("서비스 계정 키 파일이 유효한 JSON 형식인지 확인해주세요.")
            return False
        except FileNotFoundError as e:
            error_msg = f"서비스 계정 키 파일을 찾을 수 없습니다: {e}"
            logger.error(error_msg, exc_info=True)
            if st:
                st.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"❌ Firebase 초기화 실패: {type(e).__name__}: {e}"
            logger.error(error_msg, exc_info=True)
            if st:
                st.error(error_msg)
                import traceback

                st.code(traceback.format_exc())
            return False

    def get_firestore(self):
        """Firestore 클라이언트 반환"""
        if not self.initialized:
            raise ValueError("Firebase가 초기화되지 않았습니다.")
        return self.db

    def get_auth(self):
        """Firebase Auth 클라이언트 반환"""
        if not self.initialized:
            raise ValueError("Firebase가 초기화되지 않았습니다.")
        return firebase_auth


# 전역 Firebase 매니저 인스턴스
firebase_manager = FirebaseManager()


def get_firebase_manager() -> FirebaseManager:
    """Firebase 매니저 인스턴스 반환"""
    return firebase_manager


def init_firebase(service_account_path: Optional[str] = None) -> bool:
    """Firebase 초기화 (편의 함수)"""
    return firebase_manager.initialize(service_account_path)


# Firestore 컬렉션 구조 정의
class FirestoreCollections:
    """Firestore 컬렉션 구조"""

    # 사용자 컬렉션
    USERS = "users"

    # 사용자 평점 컬렉션
    USER_RATINGS = "user_ratings"

    # 영화 메타데이터 컬렉션
    MOVIE_METADATA = "movie_metadata"

    # 사용자 세션 컬렉션 (선택사항)
    USER_SESSIONS = "user_sessions"


# Firestore 문서 구조 정의
class DocumentSchemas:
    """Firestore 문서 스키마"""

    @staticmethod
    def user_schema() -> Dict[str, Any]:
        """사용자 문서 스키마"""
        return {
            "uid": str,  # Firebase Auth UID
            "email": str,
            "display_name": str,
            "photo_url": str,
            "created_at": str,  # ISO timestamp
            "updated_at": str,
            "profile_data": dict,  # 사용자 선호도, 설정 등
            "is_active": bool,
        }

    @staticmethod
    def user_rating_schema() -> Dict[str, Any]:
        """사용자 평점 문서 스키마"""
        return {
            "user_id": str,  # Firebase Auth UID
            "movie_id": str,  # 영화 ID
            "rating": float,  # 0.5 ~ 5.0
            "created_at": str,  # ISO timestamp
            "updated_at": str,
        }

    @staticmethod
    def movie_metadata_schema() -> Dict[str, Any]:
        """영화 메타데이터 문서 스키마"""
        return {
            "movie_id": str,
            "title": str,
            "year": int,
            "genre": str,
            "country": str,
            "runtime": int,
            "age_rating": str,
            "avg_score": float,
            "popularity": int,
            "review_count": int,
            "plot": str,
            "cast": str,
            "created_at": str,
        }


# Firebase 설정 도우미 함수들
def setup_firebase_config():
    """Firebase 설정 도우미"""
    # 이미 초기화된 경우
    if firebase_manager.initialized:
        logger.info("Firebase가 이미 초기화되어 있습니다.")
        return True

    # 먼저 자동으로 서비스 계정 키 파일 찾기
    project_root = Path(__file__).parent.parent.resolve()
    possible_paths = [
        project_root / "movie-recommendation-5bf7f-firebase-adminsdk-fbsvc-9818879c1d.json",
        project_root / "firebase-service-account.json",
        project_root / "service-account-key.json",
        project_root / "firebase-adminsdk.json",
    ]

    logger.info(f"Firebase 설정 시작 - 프로젝트 루트: {project_root}")

    # 자동으로 키 파일 찾기
    service_account_path = None
    for path in possible_paths:
        if path.exists():
            service_account_path = str(path)
            logger.info(f"✅ 서비스 계정 키 파일 발견: {path.name}")
            break

    # 자동으로 Firebase 초기화 시도
    if service_account_path:
        logger.info(f"Firebase 초기화 시도 중... 키 파일: {service_account_path}")
        success = init_firebase(service_account_path)
        if success:
            logger.info("✅ Firebase 설정 완료")
        else:
            logger.error("❌ Firebase 초기화 실패")
        return success
    else:
        logger.warning("⚠️ 서비스 계정 키 파일을 찾을 수 없습니다.")
        logger.info(f"검색한 경로들: {[str(p) for p in possible_paths]}")

    # 자동으로 찾지 못한 경우
    return False


def check_firebase_connection() -> bool:
    """Firebase 연결 상태 확인"""
    try:
        if firebase_manager.initialized:
            # 간단한 Firestore 쿼리로 연결 테스트
            db = firebase_manager.get_firestore()
            # 빈 쿼리로 연결 테스트
            list(db.collection("test").limit(1).stream())
            return True
    except Exception as e:
        logger.error(f"Firebase 연결 확인 실패: {e}")

    return False


if __name__ == "__main__":
    # 테스트 코드
    st.title("Firebase 설정 테스트")

    if setup_firebase_config():
        st.success("Firebase 설정이 완료되었습니다!")

        if check_firebase_connection():
            st.success("Firebase 연결이 정상입니다!")
        else:
            st.error("Firebase 연결에 문제가 있습니다.")
    else:
        st.info("Firebase 서비스 계정 키 파일을 업로드해주세요.")
