from pathlib import Path
import sys

SRC = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(SRC))
from format_preference import prefer_native_pdbqt


class FakeSettings:
    def __init__(self, mapping):
        self.suffix_to_format_name = dict(mapping)
        self.saved = 0

    def save(self):
        self.saved += 1


class FakeFormat:
    def __init__(self, name, suffixes, default_for=(), nicknames=()):
        self.name = name
        self.suffixes = list(suffixes)
        self.default_for = list(default_for)
        self.nicknames = list(nicknames)


class FakeFormats:
    def __init__(self, mapping, include_pdbt=True):
        self.settings = FakeSettings(mapping)
        self.native = FakeFormat(
            "AutoDock PDBQT", [".pdbqt"], default_for=(), nicknames=["pdbqt"]
        )
        self.pdbt = FakeFormat(
            "PDBT", [".pdbt", ".pdbqt"], default_for=[".pdbt", ".pdbqt"], nicknames=["pdbt"]
        )
        self.formats = [self.native] + ([self.pdbt] if include_pdbt else [])
        self._suffix_to_formats = {".pdbqt": list(self.formats)}
        self._user_response_cache = {".pdbqt": self.pdbt}


def test_native_becomes_unique_default_over_legacy_pdbt():
    formats = FakeFormats({".pdbqt": "PDBT"})
    changed, previous = prefer_native_pdbqt(formats, force=True)
    assert changed is True
    assert previous == "PDBT"
    assert ".pdbqt" in formats.native.default_for
    assert ".pdbt" in formats.pdbt.default_for
    assert ".pdbqt" not in formats.pdbt.default_for
    assert formats.settings.suffix_to_format_name[".pdbqt"] == "AutoDock PDBQT"
    assert formats.settings.saved == 1
    assert ".pdbqt" not in formats._user_response_cache


def test_native_default_is_repaired_even_if_preference_already_looks_correct():
    formats = FakeFormats({".pdbqt": "AutoDock PDBQT"})
    formats.native.default_for = []
    changed, previous = prefer_native_pdbqt(formats, force=True)
    assert changed is True
    assert previous == "AutoDock PDBQT"
    assert ".pdbqt" in formats.native.default_for
    assert ".pdbqt" not in formats.pdbt.default_for


def test_no_competing_pdbt_format_still_sets_native_default():
    formats = FakeFormats({}, include_pdbt=False)
    changed, previous = prefer_native_pdbqt(formats, force=True)
    assert changed is True
    assert previous is None
    assert ".pdbqt" in formats.native.default_for
    assert formats.settings.suffix_to_format_name[".pdbqt"] == "AutoDock PDBQT"


def test_missing_native_format_is_reported_instead_of_false_success():
    formats = FakeFormats({".pdbqt": "PDBT"})
    formats._suffix_to_formats[".pdbqt"] = [formats.pdbt]
    try:
        prefer_native_pdbqt(formats, force=True)
    except LookupError as err:
        assert "native 'AutoDock PDBQT'" in str(err)
    else:
        raise AssertionError("Expected LookupError when native PDBQT provider is absent")
