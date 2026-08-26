# Evidence behind claims made in the records

Scripts here are kept because a number in `spec_defects.md` or
`known_bad_values.md` cites them. They are not part of the pipeline and nothing
runs them on a schedule. Run from the repository root.

- `source_probe.py` — counts, per pass-A read, how many quotes are absent from
  the OCR layer, which is the only positive proof a reader used the scan.
  Produces the table in `spec_defects.md` under "`source` asserts something
  nothing can check".
- `multi_authorization_split.py` — checks that a letter granting several
  authorizations comes apart into one row per authorization, each carrying only
  the figures the document files under it. Exercises `19-HCAA-01437#429`, the
  only such letter in the release.
- `seam_furniture.py` — measures what stripping page furniture off both sides of
  a page break admits, and what it costs. Takes a built workbook as its argument.
  The rule in `verify.strip_edges` rests on the `lost` column being zero, and the
  conditions it still rejects are the ones whose text straddles a redaction
  marker.
- `page_break_matches.py` — sorts every condition and field entry that fails its
  own page but passes when that page is joined to the next, by what the join is
  doing for it: hiding a mis-citation, spanning a real page break, or supplying a
  doubled pool of words for the fuzzy threshold. The numbers in
  `verify.on_cited_page` come from here.
