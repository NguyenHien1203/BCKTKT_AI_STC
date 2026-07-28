"""Unit test cho UC-10 (application layer) dùng fake in-memory repository."""
import pytest

from app.application.use_cases.manage_ai_audit_log import AiAuditLogService
from app.domain.entities import AiAuditLogEntry
from app.domain.exceptions import (
    AiAuditLogNotFound,
    InvalidAiAuditLogEntry,
    InvalidAiAuditLogFilter,
)
from app.domain.repositories import AiAuditLogRepository, AiAuditReportGenerator


class FakeAiAuditLogRepository(AiAuditLogRepository):
    def __init__(self):
        self._data = []
        self._next_id = 1

    def add(self, entry: AiAuditLogEntry) -> AiAuditLogEntry:
        entry.id = self._next_id
        self._next_id += 1
        self._data.append(entry)
        return entry

    def get_by_trace_id(self, trace_id: str):
        for e in self._data:
            if e.trace_id == trace_id:
                return e
        return None

    def list(self, user_id=None, time_from=None, time_to=None):
        result = self._data
        if user_id:
            result = [e for e in result if e.username == user_id]
        if time_from:
            result = [e for e in result if e.created_at >= time_from]
        if time_to:
            result = [e for e in result if e.created_at <= time_to]
        return sorted(result, key=lambda e: (e.created_at, e.id), reverse=True)


class FakeAiAuditReportGenerator(AiAuditReportGenerator):
    def __init__(self):
        self.calls = []

    def generate(self, entries, period, time_from, time_to, generated_at):
        self.calls.append((entries, period, time_from, time_to, generated_at))
        return b"%PDF-fake-ai"


@pytest.fixture
def repo():
    return FakeAiAuditLogRepository()


@pytest.fixture
def report_generator():
    return FakeAiAuditReportGenerator()


@pytest.fixture
def service(repo, report_generator):
    return AiAuditLogService(repo, report_generator)


def test_record_happy_path(service):
    entry = service.record(
        trace_id="trace-001",
        username="canbo1",
        model="gpt-oss-120b",
        prompt="Ngân sách quý 1 là bao nhiêu?",
        response="Ngân sách quý 1 là 100 tỷ đồng.",
        sources=["bao_cao_q1.pdf"],
        permission_snapshot={"sensitivity_level": "INTERNAL"},
        prompt_version="v3",
    )
    assert entry.id == 1
    assert entry.trace_id == "trace-001"
    assert entry.sources == ["bao_cao_q1.pdf"]
    assert entry.permission_snapshot == {"sensitivity_level": "INTERNAL"}
    assert entry.created_at is not None


def test_record_blank_trace_id_raises(service):
    with pytest.raises(InvalidAiAuditLogEntry):
        service.record(trace_id="  ", username="canbo1", model="m", prompt="hỏi gì đó", response="")


def test_record_blank_prompt_raises(service):
    with pytest.raises(InvalidAiAuditLogEntry):
        service.record(trace_id="trace-002", username="canbo1", model="m", prompt="   ", response="")


def test_list_logs_returns_all_when_no_filter(service):
    service.record(trace_id="t1", username="canbo1", model="m", prompt="a", response="b")
    service.record(trace_id="t2", username="canbo2", model="m", prompt="c", response="d")
    logs = service.list_logs()
    assert len(logs) == 2


def test_list_logs_filter_by_user_id(service):
    service.record(trace_id="t1", username="canbo1", model="m", prompt="a", response="b")
    service.record(trace_id="t2", username="canbo2", model="m", prompt="c", response="d")
    logs = service.list_logs(user_id="canbo2")
    assert len(logs) == 1
    assert logs[0].username == "canbo2"


def test_list_logs_invalid_time_range_raises(service):
    with pytest.raises(InvalidAiAuditLogFilter):
        service.list_logs(time_from="2026-12-31", time_to="2026-01-01")


def test_get_by_trace_id_happy_path(service):
    service.record(trace_id="t1", username="canbo1", model="m", prompt="a", response="b")
    entry = service.get_by_trace_id("t1")
    assert entry.trace_id == "t1"


def test_get_by_trace_id_not_found_raises(service):
    with pytest.raises(AiAuditLogNotFound):
        service.get_by_trace_id("khong-ton-tai")


def test_generate_periodic_report_week(service, report_generator):
    service.record(trace_id="t1", username="canbo1", model="m", prompt="a", response="b")
    pdf_bytes = service.generate_periodic_report(period="WEEK")
    assert pdf_bytes == b"%PDF-fake-ai"
    entries, period, time_from, time_to, generated_at = report_generator.calls[0]
    assert period == "WEEK"
    assert len(entries) == 1


def test_generate_periodic_report_invalid_period_raises(service):
    with pytest.raises(InvalidAiAuditLogFilter):
        service.generate_periodic_report(period="YEAR")


def test_generate_periodic_report_invalid_time_range_raises(service):
    with pytest.raises(InvalidAiAuditLogFilter):
        service.generate_periodic_report(period="MONTH", time_from="2026-12-31", time_to="2026-01-01")