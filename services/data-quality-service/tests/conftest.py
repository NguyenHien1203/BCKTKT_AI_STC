"""Cấu hình chung cho toàn bộ test của data-quality-service.

Ghi chú hạ tầng: `app/infrastructure/db/session.py` dùng `StaticPool`
cho SQLite `:memory:` để mọi request trong 1 tiến trình dùng chung 1
CSDL (tránh lỗi "no such table" giữa các connection khác nhau). Điều
này đồng nghĩa CSDL được giữ nguyên xuyên suốt CẢ TIẾN TRÌNH pytest --
nếu không reset, quy tắc chất lượng CHUNG (`dataset_id=None`, tạo ở
`test_uc038_quality_rules.py`) sẽ rò rỉ sang các bài test của
`test_uc039_quality_check.py` chạy sau đó (và ngược lại với các UC
khác), gây sai lệch kết quả dù logic nghiệp vụ đúng. Fixture dưới đây
reset schema TRƯỚC MỖI FILE test (scope="module") để mỗi file vẫn giữ
nguyên trạng thái tự-nhất-quán bên trong (nhiều test cùng file vẫn
dùng chung dữ liệu như trước), nhưng không còn ảnh hưởng chéo giữa các
file khác nhau.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402

from app.infrastructure.db.session import Base, engine  # noqa: E402
from app.infrastructure.db import models  # noqa: E402,F401


@pytest.fixture(autouse=True, scope="module")
def _reset_db_per_module():
    if engine.url.get_backend_name() == "sqlite":
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    yield