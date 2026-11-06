"""New nullable columns exist (assembly metrics, descriptions, links, GAS, tag data)."""
from app import models

NEW_COLUMNS = {
    models.Species: ["description"],
    models.Assembly: ["assembly_type", "n_sequences", "n90_bp", "l90", "ns_per_100kbp",
                      "total_length_ge10kb", "plastid", "mitochondrion", "description",
                      "source_url"],
    models.GeneModelAnnotation: ["display_name", "tool_name", "is_reference", "description",
                                 "source_url", "zenodo_url", "micro_exon_pct", "gas_score"],
}


def test_new_columns_exist():
    for model, cols in NEW_COLUMNS.items():
        names = set(model.__table__.columns.keys())
        missing = [c for c in cols if c not in names]
        assert not missing, f"{model.__name__} missing {missing}"


def test_new_columns_nullable():
    for model, cols in NEW_COLUMNS.items():
        for c in cols:
            assert model.__table__.columns[c].nullable, f"{model.__name__}.{c} must be nullable"
