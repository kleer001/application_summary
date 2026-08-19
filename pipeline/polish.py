"""Refresh the Overview stats and write the Methodology sheet."""
import openpyxl
from openpyxl.styles import Font, Alignment

XL = "/home/menser/Dropbox/BIZ/from_stantec/A-2020-02093-MRV-FINAL_pdf/DFO_2021_FAA_offsetting_summary_WORKING_v2.xlsx"

DOC = [
 ("Source", "A-2020-02093-MRV-FINAL.pdf, 1,842 scanned pages, released under Access to Information request A-2020-02093."),
 ("Text layer", "Produced with ocrmypdf (Tesseract, languages eng+fra) at the source scan resolution of 400 dpi. "
                "The searchable PDF is A-2020-02093-MRV-FINAL_OCR_engfra.pdf; the page-separated plain text used for "
                "extraction is A-2020-02093-MRV-FINAL_OCR_engfra.txt. French pages need the fra language data - "
                "English-only OCR strips the accents and breaks proponent and place names."),
 ("Document segmentation", "Each authorization is located by its title block (\"...Fisheries Act Authorization\" / "
                "\"Autorisation aux termes des alineas...\" / \"Autorisation visee a l'alinea...\") plus an "
                "\"Authorization issued to\" / \"Autorisation accordee a\" line. A document runs from its title page to the "
                "page before the next title page. Its identifier is the PATH/SAPH number stamped on its own first page."),
 ("Row mapping", "A row is tied to a document by DFO_File_or_PATH, then by the Quebec authorisation number "
                "(\"N. d'autorisation: YYYY-NNN\"), then by proponent name. Where a row's identifier could not be tied to a "
                "title page, Source_Page_Anchor records the pages where the identifier appears and says so."),
 ("Page anchors", "PDF_Page_Start / PDF_Page_End are 1-based page numbers in the combined 1,842-page PDF. "
                "Bates_Start / Bates_End are the stamped numbers printed on the pages themselves; the two run in step for "
                "roughly the first 670 pages and differ by 4 thereafter, so both are recorded."),
 ("Auto-filled text", "Contingency_Measures, Monitoring_Requirements, Offsetting_Measures and Authorized_Impact_Summary are "
                "verbatim quotes of the corresponding numbered condition sections. Auto_Filled_Fields lists which columns a "
                "row received. Cells that already held a value were never overwritten."),
 ("Numeric area figures", "HADD_Destruction_m2, HADD_Alteration_m2 and HADD_Disturbance_m2 were deliberately NOT auto-filled. "
                "Impact clauses list components that must be summed, cap figures with \"up to\", and sometimes state a net "
                "figure after subtracting habitat created, so automatic extraction agreed with known-good values only about "
                "two thirds of the time for destruction. Candidate values, the components found, and the source sentence are "
                "in Numeric_Review_Queue for confirmation by hand."),
 ("Authorization dates", "Dates were not auto-filled. The issue date is a stamp that OCR does not reliably capture, and the "
                "dates nearest the top of a document are usually condition periods rather than the date of issue."),
 ("Offsetting split", "Offsetting_Required and Offsetting_Provided hold the original free text. Offsetting_Required_Value / "
                "_Unit and Offsetting_Provided_Value / _Unit hold the parsed amount where the text states a plain quantity. "
                "Ratio-style commitments are recorded in the unit column as \"ratio N:1\"."),
 ("Source_Reference_ID", "Now holds the page anchor. The prior workbook's values were web-search citation tokens "
                "(turn40search*) that referenced nothing in this PDF; they are preserved in Legacy_Reference_ID."),
 ("Record_Type", "Each document filed under a file number gets its own row. The first is the "
                 "authorization; later documents under the same number are marked amendment and carry "
                 "their own page anchor."),
 ("Inferred values", "A value ending in \"(i)\" was reasoned from the document text rather than quoted "
                 "from it - Aquatic_Setting and Project_Type from vocabulary in the project description, "
                 "Source_Part from where the known parts begin. Treat these as leads, not citations."),
 ("Confidence", "Set on rows added by this pass. confirmed: file number read from the page header and "
                 "three or more numbered condition sections recognised. probable: the file number needed "
                 "OCR letter-for-digit repair, or fewer than three sections were recognised. tentative: no "
                 "legible PATH/SAPH number, identified only by the provincial authorisation number."),
 ("Verification_Status", "Per-row roll-up of what the Discrepancies sheet holds for that row. "
                 "\"no discrepancies found\" means every figure checked matched the document, not that the "
                 "row is complete."),
 ("Discrepancies sheet", "One entry per disputed value. Type is contradiction (figures differ), "
                 "reconcilable (differ but explained - rounding, one component of a sum, net versus gross), "
                 "or unverified (the document states no figure). Evidence_Favours says which side the text "
                 "supports: if the workbook figure is written somewhere in the document, the extraction is "
                 "the suspect party; if it appears nowhere, the workbook figure is."),
 ("Extracted_HADD_* columns", "What this pass read from the document, kept beside the original rather than "
                 "replacing it. Measured against figures already in the workbook, extraction agrees 76% of "
                 "the time on destruction, 93% on alteration and 75% on disturbance, so neither column is "
                 "authoritative on its own."),
 ("Redaction_Exemptions", "Access to Information exemptions cited on the document's pages - s.19(1) is "
                 "personal information, s.20(1)(b) and (c) are third-party commercial information. "
                 "118 of the 1,842 pages carry one. A blank caused by redaction will stay blank."),
 ("Derived_Fields", "Names any value that is arithmetic rather than a quotation. HADD_Total_m2 is usually "
                 "the sum of the destruction and alteration figures and is not written in the document."),
 ("Province", "Spellings were normalised (Quebec, Ontario) so the column groups cleanly."),
 ("Known gaps", "Rows whose identifier appears nowhere in the PDF, and rows describing appended supporting material rather "
                "than an authorization, keep an empty page anchor. Authorizations found in the PDF with no matching row were "
                "appended and carry QA_Flag \"AUTO-ADDED\"; their non-quoted fields still need review."),
]


def main():
    wb = openpyxl.load_workbook(XL)
    ws = wb["Authorization_Summary"]
    hdr = [c.value for c in ws[1]]
    idx = {h: i + 1 for i, h in enumerate(hdr)}
    n = ws.max_row - 1

    def count(col, pred=lambda v: v not in (None, "")):
        return sum(1 for r in range(2, ws.max_row + 1) if pred(ws.cell(row=r, column=idx[col]).value))

    added = count("QA_Flag", lambda v: str(v or "").startswith("AUTO-ADDED"))
    stats = [
        ("Rows in Authorization_Summary", n),
        ("  carried over from the prior workbook", n - added),
        ("  added from the source PDF", added),
        ("Supporting documents", wb["Supporting_Documents"].max_row - 1),
        ("Rows flagged Include in 2021 = Yes", count("Include_in_2021_Request",
                                                     lambda v: str(v or "").strip().lower().startswith("yes"))),
        ("Rows with QA_Flag", count("QA_Flag")),
        ("Rows with a page anchor", count("Source_Page_Anchor")),
        ("Entries in Numeric_Review_Queue", wb["Numeric_Review_Queue"].max_row - 1),
        ("Source PDF", "A-2020-02093-MRV-FINAL.pdf (1,842 pages)"),
        ("Source text", "A-2020-02093-MRV-FINAL_OCR_engfra.txt (OCR, English + French)"),
        ("Note", "Values written into Contingency_Measures, Monitoring_Requirements, Offsetting_Measures and "
                 "Authorized_Impact_Summary are verbatim quotes from the page range in Source_Page_Anchor. "
                 "HADD area figures were not auto-filled; candidates are in Numeric_Review_Queue. See Methodology."),
    ]

    ov = wb["Overview"]
    for r in range(ov.max_row, 0, -1):
        ov.delete_rows(r)
    ov.append(["Metric", "Value"])
    for k, v in stats:
        ov.append([k, v])

    if "Methodology" in wb.sheetnames:
        del wb["Methodology"]
    me = wb.create_sheet("Methodology")
    me.append(["Topic", "Detail"])
    for k, v in DOC:
        me.append([k, v])

    for sheet, widths in ((ov, (48, 100)), (me, (26, 120))):
        for c in sheet[1]:
            c.font = Font(bold=True)
        sheet.column_dimensions["A"].width = widths[0]
        sheet.column_dimensions["B"].width = widths[1]
        for r in range(2, sheet.max_row + 1):
            sheet.cell(row=r, column=1).alignment = Alignment(vertical="top")
            sheet.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(XL)
    print(f"Overview refreshed: {n} rows ({added} added), sheets={wb.sheetnames}")


if __name__ == "__main__":
    main()
