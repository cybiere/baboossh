def test_payload_list_shows_available_payloads(shell, capsys):
    shell.onecmd_plus_hooks("payload list")
    out = capsys.readouterr().out
    assert "exec" in out


def test_payload_no_args_lists_payloads(shell, capsys):
    shell.onecmd_plus_hooks("payload")
    out = capsys.readouterr().out
    assert "Available payloads" in out
