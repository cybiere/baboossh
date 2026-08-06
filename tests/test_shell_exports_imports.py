def test_export_list_shows_available_exporters(shell, capsys):
    shell.onecmd_plus_hooks("export list")
    out = capsys.readouterr().out
    assert "comprograph" in out


def test_export_comprograph_writes_file(shell, tmp_path, capsys):
    outfile = tmp_path / "graph.dot"
    shell.onecmd_plus_hooks(f"export comprograph {outfile}")
    out = capsys.readouterr().out
    assert "Export saved" in out
    assert outfile.exists()


def test_import_list_shows_available_importers(shell, capsys):
    shell.onecmd_plus_hooks("import list")
    out = capsys.readouterr().out
    assert "textlist" in out
