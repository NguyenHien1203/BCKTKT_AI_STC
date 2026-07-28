"""Unit test cho UC-09 (application layer) dùng fake in-memory repository."""
import pytest

from app.application.use_cases.manage_audit_log import AuditLogService
from app.domain.entities import AuditLogEntry
from app.domain.exceptions import InvalidAuditLogEntry, InvalidAuditLogFilter
from app.domain.repositories import AuditLogRepository, AuditReportGenerator


class FakeAuditLogRepository(AuditLogRepository):
    def __init__(self):
        self._data = []
        self._next_id = 1

    def add(self, entry: AuditLogEntry) -> AuditLogEntry:
        entry.id = self._next_id
        self._next_id += 1
        self._data.append(entry)
        return entry

    def list(self, username=None, time_from=None, time_to=None):
        result = self._data
        if username:
            result = [e for e in result if e.username == username]
        if time_from:
            result = [e for e in result if e.created_at >= time_from]
        if time_to:
            result = [e for e in result if e.created_at <= time_to]
        return sorted(result, key=lambda e: (e.created_at, e.id), reverse=True)


class FakeAuditReportGenerator(AuditReportGenerator):
    def __init__(self):
        self.calls = []

    def generate(self, entries, time_from, time_to, generated_at):
        self.calls.append((entries, time_from, time_to, generated_at))
        return b"%PDF-fake"


@pytest.fixture
def repo():
    return FakeAuditLogRepository()


@pytest.fixture
def report_generator():
    return FakeAuditReportGenerator()


@pytest.fixture
def service(repo, report_generator):
    return AuditLogService(repo, report_generator)


def test_record_happy_path(service):
    entry = service.record(
        username="admin",
        action="CREATE",
        resource_type="USER",
        resource_id="42",
        detail="Tạo người dùng mới",
        ip_address="10.0.0.1",
    )
    assert entry.id == 1
    assert entry.username == "admin"
    assert entry.action == "CREATE"
    assert entry.status == "SUCCESS"
    assert entry.created_at is not None


def test_record_blank_username_raises(service):
    with pytest.raises(InvalidAuditLogEntry):
        service.record(username="  ", action="CREATE", resource_type="USER")


def test_record_invalid_status_raises(service):
    with pytest.raises(InvalidAuditLogEntry):
        service.record(username="admin", action="CREATE", resource_type="USER", status="OOPS")


def test_list_logs_returns_all_when_no_filter(service):
    service.record(username="admin", action="CREATE", resource_type="USER")
    service.record(username="auditor1", action="VIEW", resource_type="ORG_UNIT")
    logs = service.list_logs()
    assert len(logs) == 2


def test_list_logs_filter_by_account(service):
    service.record(username="admin", action="CREATE", resource_type="USER")
    service.record(username="auditor1", action="VIEW", resource_type="ORG_UNIT")
    logs = service.list_logs(username="auditor1")
    assert len(logs) == 1
    assert logs[0].username == "auditor1"


def test_list_logs_filter_by_time_range(service):
    service.record(username="admin", action="CREATE", resource_type="USER")
    logs = service.list_logs(time_from="2999-01-01T00:00:00+00:00")
    assert logs == []


def test_list_logs_invalid_time_range_raises(service):
    with pytest.raises(InvalidAuditLogFilter):
        service.list_logs(time_from="2026-12-31", time_to="2026-01-01")


def test_list_logs_newest_first(service):
    first = service.record(username="admin", action="CREATE", resource_type="USER")
    second = service.record(username="admin", action="UPDATE", resource_type="USER")
    logs = service.list_logs()
    assert logs[0].id == second.id
    assert logs[1].id == first.id


def test_generate_security_report_calls_generator_with_filtered_entries(service, report_generator):
    service.record(username="admin", action="CREATE", resource_type="USER")
    pdf_bytes = service.generate_security_report(time_from=None, time_to=None)
    assert pdf_bytes == b"%PDF-fake"
    assert len(report_generator.calls) == 1
    entries, time_from, time_to, generated_at = report_generator.calls[0]
    assert len(entries) == 1
    assert generated_at is not None


def test_generate_security_report_invalid_time_range_raises(service):
    with pytest.raises(InvalidAuditLogFilter):
        service.generate_security_report(time_from="2026-12-31", time_to="2026-01-01")