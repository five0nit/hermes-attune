"""Use Hermes' actual profile/namespace contract, never guess its directory name."""


def default_root():
    from hermes_cli.plugins_state import PluginState
    return PluginState("attune").data_dir
