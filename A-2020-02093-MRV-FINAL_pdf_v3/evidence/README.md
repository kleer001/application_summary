# Evidence behind claims made in the records

Scripts here are kept because a number in `spec_defects.md` or
`known_bad_values.md` cites them. They are not part of the pipeline and nothing
runs them on a schedule. Run from the repository root.

- `source_probe.py` — counts, per pass-A read, how many quotes are absent from
  the OCR layer, which is the only positive proof a reader used the scan.
  Produces the table in `spec_defects.md` under "`source` asserts something
  nothing can check".
