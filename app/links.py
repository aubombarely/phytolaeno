"""External links for species pages."""
from __future__ import annotations

from urllib.parse import quote


def species_links(name: str, taxid: int | None) -> list[tuple[str, str]]:
    """(label, url) pairs: NCBI Taxonomy and GoaT need a TaxID; Wikispecies uses the name."""
    links: list[tuple[str, str]] = []
    if taxid:
        links.append(("NCBI Taxonomy",
                      f"https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={taxid}"))
        links.append(("GoaT",
                      f"https://goat.genomehubs.org/record?recordId={taxid}&result=taxon&taxonomy=ncbi"))
    page = quote(" ".join(name.replace("_", " ").split()[:2]).replace(" ", "_"))
    links.append(("Wikispecies", f"https://species.wikimedia.org/wiki/{page}"))
    return links
