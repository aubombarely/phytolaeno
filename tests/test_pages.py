"""Species → Assemblies → Annotations pages: links, metrics, tags, GAS order."""
import re

from app import models
from app.database import SessionLocal
from app.links import species_links
from demo_helpers import fetch, ids


def _section(html: str, start_marker: str, end_marker: str) -> str:
    i = html.index(start_marker)
    j = html.find(end_marker, i + len(start_marker))
    return html[i:] if j == -1 else html[i:j]


def test_species_links_function():
    links = dict(species_links("Arabidopsis thaliana", 3702))
    assert links["NCBI Taxonomy"] == "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=3702"
    assert links["GoaT"] == "https://goat.genomehubs.org/record?recordId=3702&result=taxon&taxonomy=ncbi"
    assert links["Wikispecies"] == "https://species.wikimedia.org/wiki/Arabidopsis_thaliana"
    assert [label for label, _ in species_links("Foo bar", None)] == ["Wikispecies"]


def test_species_page_links_and_metrics():
    i = ids()
    page = fetch([f"/species/{i['species:Arabidopsis thaliana']}"])
    html = next(iter(page.values()))["text"]
    assert "wwwtax.cgi?id=3702" in html
    assert "goat.genomehubs.org" in html
    assert "species.wikimedia.org/wiki/Arabidopsis_thaliana" in html
    assert "T2T gapless" in html and "155.60" in html


def test_no_utr_tag_on_tool_not_reference():
    i = ids()
    html = next(iter(fetch([f"/species/{i['species:Arabidopsis thaliana']}"]).values()))["text"]
    table = _section(html, 'data-assembly="TAIR10"', "</table>")
    rows = {m.group(1): m.group(0) for m in
            re.finditer(r'<tr data-annotation="([^"]+)".*?</tr>', table, re.S)}
    assert "No UTRs" in rows["ANNEVO v2.2 (Embryophyta)"]
    assert "No UTRs" not in rows["Araport11"]


def test_annotations_sorted_by_gas():
    i = ids()
    html = next(iter(fetch([f"/species/{i['species:Oryza sativa']}"]).values()))["text"]
    table = _section(html, 'data-assembly="Osativa_204"', "</table>")
    gas = [float(x) for x in re.findall(r'data-gas="([\d.]+)"', table)]
    assert len(gas) == 12
    assert gas == sorted(gas, reverse=True)


def test_detail_pages_render_with_breadcrumbs():
    i = ids()
    asm, gm = i["assembly:TAIR10"], i["gm:TAIR10:ANNEVO v2.2 (Embryophyta)"]
    pages = fetch([f"/assemblies/{asm}", f"/annotations/gm/{gm}"])
    for p in pages.values():
        assert p["status"] == 200
        assert "Arabidopsis thaliana" in p["text"]          # breadcrumb back to species
    ann = pages[f"/annotations/gm/{gm}"]["text"]
    assert "No UTRs" in ann and "GAS" in ann


def test_species_page_without_new_fields(client):
    db = SessionLocal()
    try:
        sp = models.Species(name="Legacyus plantae", ncbi_taxid=None)
        db.add(sp)
        db.flush()
        asm = models.Assembly(species_id=sp.id, version="Legacy_v1")
        db.add(asm)
        db.commit()
        sp_id, asm_id = sp.id, asm.id
    finally:
        db.close()
    for path in (f"/species/{sp_id}", f"/assemblies/{asm_id}"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert ">None<" not in r.text and "None</" not in r.text, path


def test_assembly_size_from_quast():
    i = ids()
    html = next(iter(fetch([f"/species/{i['species:Arabidopsis thaliana']}"]).values()))["text"]
    assert "119.67 Mb" in html and "142.48 Mb" in html
