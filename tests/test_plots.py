"""Filterable plots, GAQET radar and GAS weights."""
import json
import re

from app.plot_data import parse_plot_params
from demo_helpers import fetch, ids


def _figure(html: str, key: str) -> dict:
    m = re.search(rf'renderPlot\("plot_{key}",\s*(\{{.*?\}})\);\s*$', html, re.S | re.M)
    assert m, f"figure {key} not found"
    return json.loads(m.group(1))


def test_parse_plot_params_defaults_and_notices():
    p = parse_plot_params(None, None, None, None, None)
    assert (p.species_id, p.assembly_id, p.annotation_ids, p.metric, p.weights, p.notices) == \
        (None, None, [], "gas", None, [])
    p = parse_plot_params("abc", "7", "1,x,3", "nonsense", "busco:abc")
    assert p.species_id is None and p.assembly_id == 7 and p.annotation_ids == [1, 3]
    assert p.metric == "gas" and p.weights is None and len(p.notices) >= 3
    p = parse_plot_params(None, None, None, None, "busco:40,omark:10")
    assert p.weights == {"busco": 40.0, "omark": 10.0} and p.notices == []
    p = parse_plot_params(None, None, None, None,
                          "busco:0,omark:0,homology:0,psauron:0,detenga:0,agat:0")
    assert p.weights is None and p.notices


def test_plots_default_renders():
    page = fetch(["/plots"])["/plots"]
    assert page["status"] == 200
    assert 'id="plot_radar"' in page["text"]
    radar = _figure(page["text"], "radar")
    assert radar["data"][0]["type"] == "scatterpolar"


def test_plots_filter_species():
    i = ids()
    rice = i["species:Oryza sativa"]
    page = fetch([f"/plots?species_id={rice}"])[f"/plots?species_id={rice}"]
    within = _figure(page["text"], "within")
    names = set(within["data"][0]["y"]) if within["data"] else set()
    assert "MSU r7 (osa1_r7)" in names
    assert "Araport11" not in names and "ChineseLong v3 (CuGenDB)" not in names


def test_weights_change_radar_order():
    i = ids()
    asm = i["assembly:TAIR10"]
    a = f"/plots?assembly_id={asm}&weights=busco:100"
    b = f"/plots?assembly_id={asm}&weights=agat:100"
    pages = fetch([a, b])
    order_a = [t["name"] for t in _figure(pages[a]["text"], "radar")["data"]]
    order_b = [t["name"] for t in _figure(pages[b]["text"], "radar")["data"]]
    assert sorted(order_a) == sorted(order_b) and len(order_a) == 15
    assert order_a != order_b


def test_plots_bad_params_fall_back():
    paths = ["/plots?species_id=abc", "/plots?assembly_id=99999", "/plots?weights=busco:abc",
             "/plots?weights=busco:0,omark:0,homology:0,psauron:0,detenga:0,agat:0"]
    pages = fetch(paths)
    for p in paths:
        assert pages[p]["status"] == 200, p
        assert 'class="alert alert-warning' in pages[p]["text"], p


def test_species_page_embeds_plots():
    i = ids()
    path = f"/species/{i['species:Arabidopsis thaliana']}"
    html = fetch([path])[path]["text"]
    assert 'id="plot_radar"' in html and 'id="plot_within"' in html


def test_within_is_dot_plot_not_zero_based_bars():
    i = ids()
    path = f"/plots?species_id={i['species:Oryza sativa']}"
    within = _figure(fetch([path])[path]["text"], "within")
    assert within["data"][0]["type"] == "scatter"
    assert within["data"][0]["mode"] == "markers"
