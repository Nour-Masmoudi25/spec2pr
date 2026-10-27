"""Machine-readable pytest outcomes for the trusted task validator."""
import json
from pathlib import Path


def pytest_addoption(parser):
    parser.addoption("--case-report", required=True)


def pytest_configure(config):
    config._benchmark_results = {"collected": [], "cases": {}, "collection_errors": []}


def pytest_collection_finish(session):
    session.config._benchmark_results["collected"] = [item.nodeid for item in session.items]


def pytest_collectreport(report):
    if report.failed:
        # The report hook has no config parameter; pytest passes the session
        # result separately below via the collection error counter as well.
        _collection_errors.append(str(report.longrepr))


_collection_errors = []


def pytest_runtest_logreport(report):
    _case_reports.setdefault(report.nodeid, {})[report.when] = report.outcome


_case_reports = {}


def pytest_sessionfinish(session, exitstatus):
    result = session.config._benchmark_results
    result["cases"] = _case_reports
    result["collection_errors"] = _collection_errors
    result["exit_code"] = int(exitstatus)
    Path(session.config.getoption("--case-report")).write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
