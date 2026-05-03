# 프로젝트 전용 커스텀 예외 클래스
# 비즈니스 로직 예외는 이 클래스를 raise 한다.
#
# 사용 예시:
#   raise AppException(status_code=404, message="문제를 찾을 수 없습니다.")


class AppException(Exception):
    """HTTP 상태코드와 메시지를 함께 가지는 애플리케이션 예외"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)
