# 공통 응답 스키마 — 모든 API 응답은 이 포맷을 따른다.
#
# 사용 예시:
#   return BaseResponse.ok(data=my_dto)
#   return BaseResponse.fail("문제를 찾을 수 없습니다.")

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "success") -> "BaseResponse[T]":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str) -> "BaseResponse[None]":
        return BaseResponse[None](success=False, message=message, data=None)
