"""The committed demo tables (built by scripts/build_demo_data.py) are complete and consistent."""
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "demo" / "data"

REFERENCES = {
    "Araport11", "TAIR10", "TAIR12", "RefSeq GCF_000001735.4",
    "MSU r7 (osa1_r7)", "RefSeq GCF_034140825.1",
    "ChineseLong v3 (CuGenDB)", "RefSeq GCF_000004075.3",
}


def _read(name: str) -> list[dict]:
    with open(DATA / name, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_benchmark_counts():
    rows = _read("benchmark_3species.tsv")
    assert len(rows) == 41
    per_species = {}
    for r in rows:
        per_species[r["Species"]] = per_species.get(r["Species"], 0) + 1
    assert per_species == {"Arabidopsis_thaliana": 16, "Oryza_sativa": 12, "Cucumis_sativus": 13}
    assert len({r["assembly_key"] for r in rows}) == 5
    assert len({r["annotation_key"] for r in rows}) == 41


def test_references_flagged():
    rows = _read("benchmark_3species.tsv")
    refs = {r["display_name"] for r in rows if r["is_reference"] == "True"}
    assert refs == REFERENCES
    egapx = [r for r in rows if r["tool_name"] == "EGAPx"]
    assert egapx and all(r["is_reference"] == "False" for r in egapx)


def test_display_names_unique_per_assembly():
    rows = _read("benchmark_3species.tsv")
    seen = set()
    for r in rows:
        key = (r["assembly_key"], r["display_name"])
        assert key not in seen, key
        seen.add(key)


def test_tair10_merged():
    rows = _read("benchmark_3species.tsv")
    ath = [r for r in rows if r["Species"] == "Arabidopsis_thaliana"
           and r["Assembly_Version"] in ("Athaliana_447_Araport11", "TAIR10_chr_all")]
    assert ath and all(r["assembly_key"] == "TAIR10" for r in ath)


def test_assembly_metrics_values():
    rows = {r["assembly_key"]: r for r in _read("assembly_metrics.tsv")}
    assert set(rows) == {"TAIR10", "GCA_978657495.1_TAIR12_genomic", "Osativa_204",
                         "ChineseLong_v3", "GCF_000004075.3_Cucumber_9930_V3_genomic"}
    tair12 = rows["GCA_978657495.1_TAIR12_genomic"]
    assert tair12["assembly_type"] == "T2T gapless"
    assert int(tair12["n_sequences"]) == 5
    assert float(tair12["ns_per_100kbp"]) == 0.0
    assert rows["ChineseLong_v3"]["plastid"] == "not identified"
    assert rows["GCF_000004075.3_Cucumber_9930_V3_genomic"]["mitochondrion"] == "yes"


def test_downloads_cover_tool_runs():
    bench = _read("benchmark_3species.tsv")
    tool_runs = {r["annotation_key"] for r in bench if r["is_reference"] == "False"}
    downloads = _read("downloads.tsv")
    assert {r["annotation_key"] for r in downloads} == tool_runs
    assert all(r["zenodo_url"] == "" for r in downloads)


def test_sorted():
    rows = _read("benchmark_3species.tsv")
    keys = [(r["Species"], r["assembly_key"], r["annotation_key"]) for r in rows]
    assert keys == sorted(keys)
