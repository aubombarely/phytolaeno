from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Species(Base):
    __tablename__ = "species"

    id             = Column(Integer, primary_key=True, index=True)
    species_number = Column(Integer)
    name           = Column(String, nullable=False, index=True)
    ncbi_taxid     = Column(Integer)
    family         = Column(String)
    lineage        = Column(String)
    description    = Column(Text)

    assemblies = relationship("Assembly", back_populates="species",
                              cascade="all, delete-orphan")


class Assembly(Base):
    __tablename__ = "assemblies"

    id         = Column(Integer, primary_key=True, index=True)
    species_id = Column(Integer, ForeignKey("species.id"), nullable=False)
    version    = Column(String, nullable=False, index=True)
    source     = Column(String)
    size_gb    = Column(Float)
    status     = Column(String)

    # Assembly-level BUSCO — viridiplantae_odb10
    busco_viridi_raw        = Column(String)
    busco_viridi_complete   = Column(Float)
    busco_viridi_single     = Column(Float)
    busco_viridi_duplicated = Column(Float)
    busco_viridi_fragmented = Column(Float)
    busco_viridi_missing    = Column(Float)

    # Assembly-level BUSCO — embryophyta_odb10
    busco_embryo_raw        = Column(String)
    busco_embryo_complete   = Column(Float)
    busco_embryo_single     = Column(Float)
    busco_embryo_duplicated = Column(Float)
    busco_embryo_fragmented = Column(Float)
    busco_embryo_missing    = Column(Float)

    pub_doi              = Column(String)
    prev_version_pub_doi = Column(String)
    prev_version_annot   = Column(String)

    # Assembly metrics (QUAST) and provenance
    assembly_type        = Column(String)    # T2T gapless / Chromosome-level / ... / Contigs
    n_sequences          = Column(Integer)
    n90_bp               = Column(Integer)
    l90                  = Column(Integer)
    ns_per_100kbp        = Column(Float)
    total_length_ge10kb  = Column(Integer)
    plastid              = Column(String)    # yes / no / not identified
    mitochondrion        = Column(String)    # yes / no / not identified
    description          = Column(Text)
    source_url           = Column(String)

    species        = relationship("Species", back_populates="assemblies")
    re_annotations = relationship("RepeatAnnotation", back_populates="assembly",
                                  cascade="all, delete-orphan")
    gm_annotations = relationship("GeneModelAnnotation", back_populates="assembly",
                                  cascade="all, delete-orphan")


class AnnotationProtocol(Base):
    __tablename__ = "annotation_protocols"

    id           = Column(Integer, primary_key=True, index=True)
    tool         = Column(String, nullable=False)
    tool_version = Column(String)
    commands     = Column(Text)
    date_run     = Column(Date)
    notes        = Column(Text)

    re_annotations = relationship("RepeatAnnotation", back_populates="protocol")
    gm_annotations = relationship("GeneModelAnnotation", back_populates="protocol")


class RepeatAnnotation(Base):
    __tablename__ = "repeat_annotations"

    id          = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.id"), nullable=False)
    protocol_id = Column(Integer, ForeignKey("annotation_protocols.id"), nullable=False)
    rank        = Column(Integer)
    version_label = Column(String)
    total_pct   = Column(Float)       # overall repeat % (EarlGrey)
    raw_output  = Column(Text)        # full string from the table
    parsed_results = Column(JSON)     # dict of class → % (EarlGrey) or counts (Barrnap/tRNA)

    assembly = relationship("Assembly", back_populates="re_annotations")
    protocol = relationship("AnnotationProtocol", back_populates="re_annotations")


class GeneModelAnnotation(Base):
    __tablename__ = "gm_annotations"

    id          = Column(Integer, primary_key=True, index=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.id"), nullable=False)
    protocol_id = Column(Integer, ForeignKey("annotation_protocols.id"), nullable=False)
    pid         = Column(String)
    ref_type    = Column(Integer)
    rank        = Column(Integer)
    version_label = Column(String)
    methodology = Column(Text)

    # Gene model counts
    gene_models_n             = Column(Integer)
    transcript_models_n       = Column(Integer)
    cds_models_n              = Column(Integer)
    exons_n                   = Column(Integer)
    utr5_n                    = Column(Integer)
    utr3_n                    = Column(Integer)
    both_utrs_n               = Column(Integer)
    overlapping_gene_models_n = Column(Integer)
    single_exon_gene_models_n = Column(Integer)
    single_exon_transcripts_n = Column(Integer)

    # Lengths and space
    total_gene_space_mb      = Column(Float)
    mean_gene_model_length_bp = Column(Float)
    mean_cds_length_bp        = Column(Float)
    mean_exon_length_bp       = Column(Float)
    mean_intron_length_bp     = Column(Float)
    longest_gene_model_bp     = Column(Float)
    longest_cds_bp            = Column(Float)
    longest_intron_bp         = Column(Float)
    shortest_gene_model_bp    = Column(Float)
    shortest_cds_bp           = Column(Float)
    shortest_intron_bp        = Column(Float)

    # Quality flags
    models_early_stop        = Column(Integer)
    models_start_missing     = Column(Integer)
    models_stop_missing      = Column(Integer)
    models_start_stop_missing = Column(Integer)

    # Annotation BUSCO — viridiplantae_odb10
    busco_viridi_raw        = Column(String)
    busco_viridi_complete   = Column(Float)
    busco_viridi_single     = Column(Float)
    busco_viridi_duplicated = Column(Float)
    busco_viridi_fragmented = Column(Float)
    busco_viridi_missing    = Column(Float)

    # Annotation BUSCO — embryophyta_odb10
    busco_embryo_raw        = Column(String)
    busco_embryo_complete   = Column(Float)
    busco_embryo_single     = Column(Float)
    busco_embryo_duplicated = Column(Float)
    busco_embryo_fragmented = Column(Float)
    busco_embryo_missing    = Column(Float)

    # OMArk
    omark_completeness_raw   = Column(Text)
    omark_consistency_raw    = Column(Text)
    omark_species_composition = Column(String)

    # Other QC
    psauron_score          = Column(Float)
    detenga_fpv_raw        = Column(Text)
    detenga_fp_pct_raw     = Column(Text)
    proteins_swissprot_pct = Column(Float)
    proteins_trembl_pct    = Column(Float)
    gaqet_plot_area        = Column(Float)

    # Comparison metrics
    f1_score_base  = Column(Float)
    f1_score_locus = Column(Float)
    missed_loci    = Column(Float)
    new_loci       = Column(Float)

    # Presentation, provenance and derived scores
    display_name   = Column(String)
    tool_name      = Column(String)
    is_reference   = Column(Boolean, default=False, nullable=True)
    description    = Column(Text)
    source_url     = Column(String)
    zenodo_url     = Column(String)
    micro_exon_pct = Column(Float)     # % transcripts with micro-exons (filled later)
    gas_score      = Column(Float)     # Global Annotation Score (GAQET), default weights

    assembly = relationship("Assembly", back_populates="gm_annotations")
    protocol = relationship("AnnotationProtocol", back_populates="gm_annotations")
