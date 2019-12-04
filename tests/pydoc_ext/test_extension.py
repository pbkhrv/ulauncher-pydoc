from pydoc_ext.extension import search_modules


def test_dont_show_deeper_names():
    _, items = search_modules(
        "mod.submod", ["mod", "mod.submod", "mod.submod.subsubmod"]
    )
    names = [i.name for i in items]
    assert "mod" in names
    assert "mod.submod" in names
    assert "mod.submod.subsubmod" not in names


def test_exact_basename_match_is_ranked_higher():
    best_match = search_modules("http.", ["http.server", "httplib2.iri2uri"])[1][0]
    assert best_match.name == "http.server"


def test_exact_name_match_is_ranked_higher():
    best_match = search_modules("http", ["http", "httplib2"])[1][0]
    assert best_match.name == "http"
