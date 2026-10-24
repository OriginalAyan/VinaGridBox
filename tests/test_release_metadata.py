from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).parents[1]


def test_bundle_uses_native_pdbqt_opener_without_registering_a_duplicate_provider():
    root = ET.parse(ROOT / "bundle_info.xml").getroot()
    assert root.attrib["version"] == "2.0.0"
    assert root.attrib.get("customInit") == "true"
    assert root.find("./Categories/Category").attrib["name"] == "Binding Analysis"
    assert root.find('./Providers[@manager="data formats"]') is None
    assert root.find('./Providers[@manager="open command"]') is None
    api = (ROOT / "src" / "__init__.py").read_text(encoding="utf-8")
    assert "run_provider" not in api
    assert not (ROOT / "src" / "pdbqt_reader.py").exists()
    tool = (ROOT / "src" / "tool.py").read_text(encoding="utf-8")
    commands = (ROOT / "src" / "commands.py").read_text(encoding="utf-8")
    assert 'format pdbqt' not in tool
    assert 'format pdbqt' not in commands
    assert 'Open PDBQT / docking results' not in tool
    assert 'open_pdbqt_dialog' not in tool
    assert 'openpdbqt' not in commands
    help_html = (ROOT / 'src' / 'docs' / 'user' / 'tools' / 'vinagridbox.html').read_text(encoding='utf-8')
    assert 'openpdbqt' not in help_html
    assert 'Open PDBQT / docking results' not in help_html
    assert 'QFileDialog' not in tool
    assert 'action in ("nativepdbqt", "setpdbqtdefault")' in commands
    assert 'suffix_to_format_name' in (ROOT / "src" / "format_preference.py").read_text(encoding="utf-8")
    api = (ROOT / "src" / "__init__.py").read_text(encoding="utf-8")
    assert "def initialize(session, bundle_info)" in api
    assert "prefer_native_pdbqt(session.data_formats, force=True)" in api
    helper = (ROOT / "src" / "format_preference.py").read_text(encoding="utf-8")
    assert 'NATIVE_PDBQT_FORMAT_NAME = "AutoDock PDBQT"' in helper
    assert "native.default_for = native_defaults" in helper
    assert "fmt.default_for = new_defaults" in helper
    assert '".pdbqt"' in helper


def test_reused_code_license_and_attribution_are_present():
    assert "GNU LESSER GENERAL PUBLIC LICENSE" in (ROOT / "LICENSE.txt").read_text(encoding="utf-8")
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "ChimeraX-Vinardock" in notices
    assert "Rodrigo Quiroga" in notices
    assert "mousemode.py" in notices
    assert "pdbt.py" not in notices


def test_gui_documents_drag_and_edge_occlusion_modes():
    tool = (ROOT / "src" / "tool.py").read_text(encoding="utf-8")
    box = (ROOT / "src" / "box.py").read_text(encoding="utf-8")
    assert "Enable mouse move / resize" in tool
    assert "Draw box on top (show edges through structure)" in tool
    assert "surf.on_top = self._draw_on_top" in box
    assert "edge.on_top = self._draw_on_top" in box


def test_undo_support_is_wired_for_geometry_color_clear_and_mouse_drag():
    undo = (ROOT / "src" / "undo_support.py").read_text(encoding="utf-8")
    tool = (ROOT / "src" / "tool.py").read_text(encoding="utf-8")
    mouse = (ROOT / "src" / "mousemode.py").read_text(encoding="utf-8")
    assert "class VinaBoxUndoAction(UndoAction)" in undo
    assert "undo_manager.register(action)" in undo
    for expected in ("Edit Vina box", "Set Vina box", "Create box from selection", "Clear Vina box", "Change Vina box color"):
        assert expected in tool
    assert "record_state_change(self.session, self._undo_before, after, self._undo_name)" in mouse
    assert "display(True)" not in undo and "display(False)" not in undo
