from chimerax.core.toolshed import BundleAPI


class _VinaGridBoxAPI(BundleAPI):
    api_version = 1

    @staticmethod
    def start_tool(session, bi, ti):
        if ti.name != "Vina Grid Box":
            raise ValueError(f"Unknown tool name: {ti.name}")
        from .tool import VinaGridBoxTool
        return VinaGridBoxTool(session, ti.name)

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
