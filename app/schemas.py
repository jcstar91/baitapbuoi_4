from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from typing import Literal


class TicketExtraction(BaseModel):
    ticket_id: str
    intent: Literal["billing", "technical", "account", "other"] = Field(
        description="billing: thanh toán, technical: lỗi kỹ thuật, account: tài khoản, other: việc khác"
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(description="Mức độ khẩn cấp")
    product: str | None = Field(default=None, description="Tên sản phẩm, null nếu khách không nhắc tới")
    summary: str = Field(max_length=200)
    needs_human_review: bool

class ExtractIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=5000)
    
class ConfirmIn(BaseModel):
    ticket_id: int
    extracted: dict = Field(description="Dữ liệu đã được trích xuất từ AI, có thể chỉnh sửa trước khi xác nhận")