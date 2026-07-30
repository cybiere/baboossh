import os

from baboossh.extensions import Extensions


def test_load_populates_all_extension_types():
    Extensions.auths.clear()
    Extensions.payloads.clear()
    Extensions.exports.clear()
    Extensions.imports.clear()

    Extensions.load()

    assert len(Extensions.auths) > 0
    assert len(Extensions.payloads) > 0
    assert len(Extensions.exports) > 0
    assert len(Extensions.imports) > 0


def test_load_registers_one_entry_per_extension_file():
    Extensions.auths.clear()
    Extensions.payloads.clear()
    Extensions.exports.clear()
    Extensions.imports.clear()

    ext_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "baboossh", "ext_dir")
    expected_count = len([
        f for f in os.listdir(ext_dir)
        if os.path.isfile(os.path.join(ext_dir, f)) and f[0] != "."
    ])

    Extensions.load()

    total_loaded = (
        len(Extensions.auths)
        + len(Extensions.payloads)
        + len(Extensions.exports)
        + len(Extensions.imports)
    )
    assert total_loaded == expected_count


def test_load_is_idempotent_and_does_not_duplicate_entries():
    Extensions.auths.clear()
    Extensions.payloads.clear()
    Extensions.exports.clear()
    Extensions.imports.clear()

    Extensions.load()
    counts_after_first = {
        "auths": len(Extensions.auths),
        "payloads": len(Extensions.payloads),
        "exports": len(Extensions.exports),
        "imports": len(Extensions.imports),
    }

    Extensions.load()
    counts_after_second = {
        "auths": len(Extensions.auths),
        "payloads": len(Extensions.payloads),
        "exports": len(Extensions.exports),
        "imports": len(Extensions.imports),
    }

    assert counts_after_first == counts_after_second
