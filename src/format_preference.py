"""Make ChimeraX's built-in AutoDock PDBQT reader the default for .pdbqt.

ChimeraX's data-format manager evaluates DataFormat.default_for *before* its
saved suffix_to_format_name preference. Consequently, merely changing the
saved preference cannot override a competing default provided by another installed format bundle. This module updates the current session's format records so the
native AutoDock PDBQT format is the preferred default and a competing legacy
format no longer claims .pdbqt as its default. That legacy format remains registered
for its own suffix and can still be selected explicitly if its provider is installed.
"""

NATIVE_PDBQT_FORMAT_NAME = "AutoDock PDBQT"
PDBQT_SUFFIX = ".pdbqt"
LEGACY_PDBT_FORMAT_NAME = "pdbt"


def _suffixes(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def prefer_native_pdbqt(formats_manager, *, force=True):
    """Make native AutoDock PDBQT the unique preferred default for .pdbqt.

    Updates the live data-format records *and* the persistent suffix preference.
    The live records matter because ChimeraX checks ``default_for`` before
    ``settings.suffix_to_format_name``. ``force`` is retained for compatibility
    with earlier VinaGridBox releases; native PDBQT is now deliberately forced
    because the goal is to make normal .pdbqt opening deterministic.

    Returns ``(changed, previous_saved_preference)``. Raises LookupError if
    ChimeraX's native AutoDock PDBQT format is not registered in this session.
    """
    settings = formats_manager.settings
    mapping = settings.suffix_to_format_name
    previous = mapping.get(PDBQT_SUFFIX)

    # FormatsManager's suffix dispatch uses these exact DataFormat objects.
    suffix_table = getattr(formats_manager, "_suffix_to_formats", {})
    suffix_formats = list(suffix_table.get(PDBQT_SUFFIX, ()))
    if not suffix_formats:
        suffix_formats = [
            fmt for fmt in getattr(formats_manager, "formats", ())
            if PDBQT_SUFFIX in [s.lower() for s in _suffixes(getattr(fmt, "suffixes", ()))]
        ]

    native = next(
        (
            fmt for fmt in suffix_formats
            if str(getattr(fmt, "name", "")).strip().casefold()
            == NATIVE_PDBQT_FORMAT_NAME.casefold()
        ),
        None,
    )
    if native is None:
        raise LookupError(
            "ChimeraX's native 'AutoDock PDBQT' data format is not registered. "
            "Check that the built-in ViewDock bundle is available."
        )

    changed = False
    # Make the native reader the default for .pdbqt.
    native_defaults = _suffixes(getattr(native, "default_for", ()))
    if not any(s.lower() == PDBQT_SUFFIX for s in native_defaults):
        native_defaults.append(PDBQT_SUFFIX)
        native.default_for = native_defaults
        changed = True

    # Remove only the .pdbqt default claim from the legacy PDBT format. Keep
    # its native suffix/registration intact. This is necessary because the
    # ChimeraX format manager returns a sole declared default before checking
    # suffix_to_format_name, so a saved preference alone cannot override it.
    for fmt in suffix_formats:
        if fmt is native:
            continue
        name = str(getattr(fmt, "name", "")).strip().casefold()
        nicknames = {str(n).strip().casefold() for n in getattr(fmt, "nicknames", ())}
        is_legacy_pdbt = name == LEGACY_PDBT_FORMAT_NAME or LEGACY_PDBT_FORMAT_NAME in nicknames
        if not is_legacy_pdbt:
            continue
        old_defaults = _suffixes(getattr(fmt, "default_for", ()))
        new_defaults = [s for s in old_defaults if s.lower() != PDBQT_SUFFIX]
        if new_defaults != old_defaults:
            fmt.default_for = new_defaults
            changed = True

    # The settings comparison uses the official DataFormat.name, not a nickname.
    if mapping.get(PDBQT_SUFFIX) != native.name:
        mapping[PDBQT_SUFFIX] = native.name
        settings.save()
        changed = True

    # Format choices may have been cached after an earlier ambiguous chooser.
    cache = getattr(formats_manager, "_user_response_cache", None)
    if cache is not None:
        if PDBQT_SUFFIX in cache:
            cache.pop(PDBQT_SUFFIX, None)
            changed = True

    return changed, previous
