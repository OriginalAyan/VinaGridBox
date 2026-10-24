from chimerax.core.toolshed import BundleAPI


class _VinaGridBoxAPI(BundleAPI):
    api_version = 1

    @staticmethod
    def initialize(session, bundle_info):
        """Make ChimeraX's native PDBQT reader the default for .pdbqt files.

        The format manager checks a provider's ``default_for`` declaration
        before its remembered suffix preference. We therefore repair both the
        live default declarations and the saved preference, rather than only
        changing the preference string.
        """
        from .format_preference import prefer_native_pdbqt

        def apply_preference(log_missing=True):
            try:
                changed, previous = prefer_native_pdbqt(session.data_formats, force=True)
            except LookupError as err:
                if log_missing:
                    session.logger.warning("VinaGridBox could not set the native .pdbqt default yet: %s" % err)
                return False
            if changed:
                session.logger.info(
                    "VinaGridBox: normal .pdbqt opening now defaults to ChimeraX's native "
                    "AutoDock PDBQT reader; a competing legacy format is no longer the .pdbqt default."
                )
            return True

        # Apply immediately, then repeat once after startup's provider
        # registration has settled. The second pass is important if another
        # bundle's format metadata is registered later in the startup order.
        apply_preference(log_missing=False)
        try:
            from Qt.QtCore import QTimer
            QTimer.singleShot(0, apply_preference)
        except Exception as err:
            session.logger.warning("VinaGridBox could not schedule the native PDBQT preference repair: %s" % err)

    @staticmethod
    def start_tool(session, bi, ti):
        if ti.name != "Vina Grid Box":
            raise ValueError(f"Unknown tool name: {ti.name}")
        from chimerax.core import tools
        from .tool import VinaGridBoxTool
        return tools.get_singleton(
            session, VinaGridBoxTool, ti.name, create=True
        )

    @staticmethod
    def register_command(bi, ci, logger):
        if ci.name != "vinabox":
            raise ValueError(f"Unknown command name: {ci.name}")
        from .commands import vinabox_desc, cmd_vinabox
        from chimerax.core.commands import register
        desc = vinabox_desc
        if desc.synopsis is None:
            desc.synopsis = ci.synopsis
        register(ci.name, desc, cmd_vinabox, logger=logger)

    @staticmethod
    def get_class(class_name):
        if class_name == "VinaGridBoxTool":
            from .tool import VinaGridBoxTool
            return VinaGridBoxTool
        raise ValueError(f"Unknown class name '{class_name}'")


bundle_api = _VinaGridBoxAPI()
