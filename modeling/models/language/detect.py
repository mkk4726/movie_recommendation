from langdetect import detect


class LanguageDetector:
    def detect_language(self, text: str) -> str:
        try:
            return detect(text)  # 'ko', 'en', 'ja', ...
        except Exception:
            return "unknown"


if __name__ == "__main__":
    detector = LanguageDetector()
    print(detector.detect_language("밝은 여름 느낌의 영화 sum"))  # ko
    print(detector.detect_language("A dark dramatic movie 포스터"))  # en