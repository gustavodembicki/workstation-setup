from dataclasses import dataclass

from workstation_setup import log


@dataclass
class _FakeStep:
    id: str = "fake-step"
    title: str = "Fake step"
    description: str = "A fake step for log.py tests"


def test_configure_creates_log_file(tmp_path):
    log.configure(dry_run=False, log_dir=tmp_path)

    assert (tmp_path / "run.log").exists()

    log.finalize(success=True)


def test_finalize_success_deletes_log_file(tmp_path):
    log.configure(dry_run=False, log_dir=tmp_path)
    log.info("doing some work")

    log.finalize(success=True)

    assert not (tmp_path / "run.log").exists()


def test_finalize_failure_retains_log_file(tmp_path):
    log.configure(dry_run=False, log_dir=tmp_path)
    log.info("about to fail")

    log.finalize(success=False)

    log_path = tmp_path / "run.log"
    assert log_path.exists()
    assert "about to fail" in log_path.read_text()


def test_mark_failed_then_finalize_success_still_retains_file(tmp_path):
    log.configure(dry_run=False, log_dir=tmp_path)
    log.mark_failed()

    log.finalize(success=True)

    assert (tmp_path / "run.log").exists()


def test_dry_run_never_touches_disk(tmp_path):
    log.configure(dry_run=True, log_dir=tmp_path)
    log.info("preview only")

    log.finalize(success=True)

    assert not (tmp_path / "run.log").exists()
    assert list(tmp_path.iterdir()) == []


def test_finalize_is_idempotent(tmp_path):
    log.configure(dry_run=False, log_dir=tmp_path)

    log.finalize(success=False)
    log_path = tmp_path / "run.log"
    assert log_path.exists()

    # A second finalize() must not reopen/rewrite/crash on the already-closed file.
    log.finalize(success=True)
    assert log_path.exists()


def test_failure_writes_command_and_stderr_to_log(tmp_path):
    log.configure(dry_run=False, log_dir=tmp_path)
    step = _FakeStep()
    error = Exception("boom")
    error.command = ["brew", "install", "thing"]  # type: ignore[attr-defined]
    error.stderr = "no such formula"  # type: ignore[attr-defined]

    log.failure(step, error)
    log.finalize(success=False)

    content = (tmp_path / "run.log").read_text()
    assert "boom" in content
    assert "brew install thing" in content
    assert "no such formula" in content


def test_task_context_manager_runs_body_and_cleans_up(tmp_path):
    log.configure(dry_run=False, log_dir=tmp_path)
    ran = False

    with log.task("Installing thing..."):
        ran = True

    assert ran
    log.finalize(success=True)


def test_nested_task_context_managers(tmp_path):
    log.configure(dry_run=False, log_dir=tmp_path)
    order = []

    with log.task("outer"):
        order.append("outer-start")
        with log.task("inner"):
            order.append("inner")
        order.append("outer-end")

    assert order == ["outer-start", "inner", "outer-end"]
    log.finalize(success=True)


def test_suspend_task_is_noop_without_active_task(tmp_path):
    log.configure(dry_run=False, log_dir=tmp_path)

    with log.suspend_task():
        log.info("no spinner was active, this must not crash")

    log.finalize(success=True)


def test_suspend_task_pauses_and_resumes_active_task(tmp_path):
    log.configure(dry_run=False, log_dir=tmp_path)

    with log.task("running..."):
        with log.suspend_task():
            log.info("interactive subprocess output goes here")

    log.finalize(success=True)


def test_reset_gives_a_clean_recording_console():
    log.reset()
    log.info("hello")

    assert "hello" in log.console_export()

    log.reset()
    assert "hello" not in log.console_export()
