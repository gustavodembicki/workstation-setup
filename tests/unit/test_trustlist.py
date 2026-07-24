from workstation_setup.registry.catalog import all_specs
from workstation_setup.registry.trustlist import TRUSTLIST

ALL_SPECS = list(all_specs())
ALL_IDS = {spec.id for spec in ALL_SPECS}


_BREW_KINDS = ("brew_cask", "brew_formula")


def _needs_a_link(spec):
    return any(method.kind not in _BREW_KINDS for method in spec.linux)


def test_every_spec_needing_a_link_has_a_trustlist_entry():
    for spec in ALL_SPECS:
        if not _needs_a_link(spec):
            continue
        assert spec.id in TRUSTLIST, f"{spec.id} has a Linux install method but no TRUSTLIST entry"
        links = TRUSTLIST[spec.id]
        assert links.download_url or links.gpg_key_url or links.apt_repo_line


def test_no_orphan_trustlist_entries():
    for app_id in TRUSTLIST:
        assert app_id in ALL_IDS, f"TRUSTLIST has an entry for {app_id!r} but no matching AppSpec"


def test_all_links_are_well_formed_urls():
    for app_id, links in TRUSTLIST.items():
        for field_name in ("download_url", "gpg_key_url", "apt_repo_line"):
            value = getattr(links, field_name)
            if value is None:
                continue
            if field_name == "apt_repo_line":
                # Not a bare URL - a `deb [...] <url> <suite> <component>` line -
                # just make sure the embedded repo URL uses a real scheme.
                assert " https://" in value, f"{app_id}: {value!r}"
            else:
                is_url = value.startswith("https://")
                assert is_url, f"{app_id}.{field_name}: {value!r}"
