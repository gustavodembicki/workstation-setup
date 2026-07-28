from factories import make_context


def test_run_command_delegates_to_runner():
    ctx = make_context()

    result = ctx.run_command(["echo", "hi"])

    assert result.ok
    assert ctx.runner.calls == [["echo", "hi"]]


def test_run_command_honors_dry_run_flag():
    ctx = make_context(dry_run=True)

    ctx.run_command(["brew", "install", "zsh"])

    assert ctx.runner.calls == []


def test_read_only_command_runs_during_dry_run():
    ctx = make_context(dry_run=True)

    ctx.run_command(["winget", "list"], read_only=True)

    assert ctx.runner.calls == [["winget", "list"]]
