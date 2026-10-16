from chimerax.core.commands import CmdDesc, Float3Arg, FloatArg, StringArg

from .box import VinaBoxModel


def _tool(session):
    """Return the existing Vina Grid Box tool instance, if any."""
    for tool in session.tools.list():
        if tool.__class__.__name__ == "VinaGridBoxTool":
            return tool
    return None


def _get_or_create_tool(session, *, show=False):
    """Get the tool singleton, creating it through ChimeraX's tools API.

    Do not call ChimeraX UI methods that are not present in the 1.12 API. Directly constructing the tool can also produce
    multiple instances. tools.get_singleton() handles both cold-start and
    already-open/hidden cases.
    """
    tool = _tool(session)
    if tool is None:
        from chimerax.core import tools
        from .tool import VinaGridBoxTool
        tool = tools.get_singleton(
            session, VinaGridBoxTool, "Vina Grid Box", create=True
        )
    if tool is None:
        raise RuntimeError("Could not create the Vina Grid Box tool")
    if show:
        tool.display(True)
    return tool


def cmd_vinabox(session, action, center=None, size=None, spacing=0.375, padding=4.0):
    """Execute a VinaGridBox CLI action.

    Canonical selection actions are ``bounds`` and ``centroid``. GUI actions
    are explicitly named ``showgui`` and ``hidegui``. Longer names from the
    previous release remain accepted as backwards-compatible aliases.
    """
    tool = _tool(session)

    # Explicit GUI actions. Keep short/old spellings as compatibility aliases,
    # but document showgui/hidegui as the preferred forms.
    if action in ("showgui", "guishow", "show"):
        _get_or_create_tool(session, show=True)
    elif action in ("hidegui", "guihide", "hide"):
        if tool is not None:
            tool.display(False)
    elif action == "clear":
        if tool is not None:
            tool.clear_box()
    elif action == "set":
        if center is None or size is None:
            raise ValueError("set requires center and size")
        tool = _get_or_create_tool(session, show=True)
        tool.set_box_from_cli(center, size, spacing)
    elif action in ("bounds", "centroid", "from-selection-bounds", "from-selection-vina"):
        if not 0.0 <= padding <= 50.0:
            raise ValueError("padding must be between 0 and 50 Å")
        tool = _get_or_create_tool(session, show=True)
        method = "bounds" if action in ("bounds", "from-selection-bounds") else "vina"
        message = tool.from_selection(method=method, padding=padding)
        if message:
            session.logger.info(message)
    elif action == "report":
        if tool is None or tool.box is None:
            session.logger.info("No Vina box")
        else:
            tool.report()
    else:
        raise ValueError(
            "Unknown vinabox action. Use set, bounds, centroid, showgui, "
            "hidegui, report, or clear. GUI aliases: guishow/guihide. "
            "Legacy aliases are also accepted: from-selection-bounds, "
            "from-selection-vina, show, hide."
        )


vinabox_desc = CmdDesc(
        required=[("action", StringArg)],
        keyword=[("center", Float3Arg), ("size", Float3Arg), ("spacing", FloatArg), ("padding", FloatArg)],
        synopsis="set a Vina box, derive from selected atoms, show/hide the GUI, report, or clear",
    )
