"""
Builds results/ai_mcq_pilot_results.xlsx: a multi-sheet workbook with a
"Raw Data" sheet (the full 996-question dataset, one row per question,
exactly as in questions_v2.csv) and several summary sheets that compute
every number with live COUNTIFS formulas against Raw Data -- nothing is
hardcoded, so the workbook recalculates if the raw data sheet is edited.
"""
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
CSV_PATH = os.path.join(RESULTS_DIR, "questions_v2.csv")
COST_CSV_PATH = os.path.join(RESULTS_DIR, "cost_log.csv")
OUT_PATH = os.path.join(RESULTS_DIR, "ai_mcq_pilot_results.xlsx")

FONT_NAME = "Arial"
HEADER_FONT = Font(name=FONT_NAME, bold=True, color="FFFFFF", size=10)
HEADER_FILL = PatternFill("solid", fgColor="2A78D6")
BODY_FONT = Font(name=FONT_NAME, size=10)
BOLD_FONT = Font(name=FONT_NAME, bold=True, size=10)
TITLE_FONT = Font(name=FONT_NAME, bold=True, size=13)
NOTE_FONT = Font(name=FONT_NAME, italic=True, size=9, color="595857")
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

CATEGORIES = ["output", "variable_state", "loop_trace", "control_flow",
              "call_count", "edge_case", "code_modification", "data_structure_state"]

MODELS = [
    "GPT-6 Luna (reasoning: none)",
    "GPT-6 Luna (reasoning: medium)",
    "GPT-6 Astra (reasoning: low)",
    "Claude Haiku 5.5 (thinking: off)",
    "Claude Haiku 5.5 (thinking: on)",
    "Claude Opus 5 (thinking: off)",
    "Claude Opus 5 (thinking: on)",
]


def style_header_row(ws, row, n_cols):
    for c in range(1, n_cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER


def autosize(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def write_raw_data_sheet(wb, df):
    ws = wb.active
    ws.title = "Raw Data"
    headers = list(df.columns)
    for j, h in enumerate(headers, start=1):
        ws.cell(row=1, column=j, value=h)
    style_header_row(ws, 1, len(headers))

    for i, row in enumerate(df.itertuples(index=False), start=2):
        for j, val in enumerate(row, start=1):
            if pd.isna(val):
                val = None
            cell = ws.cell(row=i, column=j, value=val)
            cell.font = BODY_FONT
    ws.freeze_panes = "A2"
    widths = [10, 20, 12, 18, 55] + [22, 22, 22, 22] + [12, 18, 14, 30]
    widths += [28, 10, 9] * len(MODELS)
    autosize(ws, widths[:len(headers)])
    return ws, headers


def col_letter(headers, name):
    return get_column_letter(headers.index(name) + 1)


def main():
    df = pd.read_csv(CSV_PATH)
    n = len(df)
    last_row = n + 1  # data rows are 2..last_row

    wb = Workbook()
    raw_ws, headers = write_raw_data_sheet(wb, df)

    cat_col = col_letter(headers, "category")
    gt_col = col_letter(headers, "ground_truth_option")
    key_ok_col = col_letter(headers, "key_is_correct")

    def rng(col):
        return f"'Raw Data'!${col}$2:${col}${last_row}"

    # ---------------- Overall Ranking ----------------
    ws = wb.create_sheet("Overall Ranking")
    ws["A1"] = "Overall accuracy, ranked (live formulas over Raw Data)"
    ws["A1"].font = TITLE_FONT
    headers_row = ["Model / setting", "Valid answers", "Valid %",
                   "Headline accuracy\n(unparseable = wrong)",
                   "Accuracy among\nparseable answers only",
                   "Questions w/ ground truth"]
    for j, h in enumerate(headers_row, start=1):
        ws.cell(row=3, column=j, value=h)
    style_header_row(ws, 3, len(headers_row))

    for i, model in enumerate(MODELS, start=4):
        corr_col = col_letter(headers, f"{model}_correct")
        valid_col = col_letter(headers, f"{model}_valid")
        ws.cell(row=i, column=1, value=model).font = BODY_FONT
        ws.cell(row=i, column=2,
                value=f'=COUNTIF({rng(valid_col)},TRUE)&"/{n}"').font = BODY_FONT
        ws.cell(row=i, column=3,
                value=f'=COUNTIF({rng(valid_col)},TRUE)/{n}').number_format = "0.0%"
        ws.cell(row=i, column=4,
                value=(f'=COUNTIFS({rng(gt_col)},"<>",{rng(corr_col)},TRUE)'
                       f'/COUNTIFS({rng(gt_col)},"<>")')).number_format = "0.0%"
        ws.cell(row=i, column=5,
                value=(f'=IFERROR(COUNTIFS({rng(gt_col)},"<>",{rng(valid_col)},TRUE,{rng(corr_col)},TRUE)'
                       f'/COUNTIFS({rng(gt_col)},"<>",{rng(valid_col)},TRUE),"n/a")')).number_format = "0.0%"
        ws.cell(row=i, column=6,
                value=f'=COUNTIFS({rng(gt_col)},"<>")').font = BODY_FONT
        for c in [3, 4, 5]:
            ws.cell(row=i, column=c).font = BODY_FONT
        for c in range(1, 7):
            ws.cell(row=i, column=c).border = BORDER

    ws["A12"] = ("Note: 'Headline accuracy' scores an unparseable (invalid) response as wrong, matching the "
                 "project's primary ranking. 'Accuracy among parseable answers only' excludes invalid "
                 "responses from both numerator and denominator -- see results_summary.md, 'A genuine "
                 "surprise' section, for why this matters (Claude Opus 5 in particular).")
    ws["A12"].font = NOTE_FONT
    ws.merge_cells("A12:F13")
    ws["A12"].alignment = Alignment(wrap_text=True, vertical="top")
    autosize(ws, [32, 14, 10, 16, 18, 16])
    for r in (3,):
        ws.row_dimensions[r].height = 30

    # ---------------- Accuracy by Category ----------------
    ws2 = wb.create_sheet("Accuracy by Category")
    ws2["A1"] = "Accuracy by category x model (live formulas over Raw Data)"
    ws2["A1"].font = TITLE_FONT
    header_row = ["Category"] + MODELS
    for j, h in enumerate(header_row, start=1):
        ws2.cell(row=3, column=j, value=h)
    style_header_row(ws2, 3, len(header_row))
    ws2.row_dimensions[3].height = 40

    for i, cat in enumerate(CATEGORIES, start=4):
        ws2.cell(row=i, column=1, value=cat).font = BODY_FONT
        ws2.cell(row=i, column=1).border = BORDER
        for j, model in enumerate(MODELS, start=2):
            corr_col = col_letter(headers, f"{model}_correct")
            cell = ws2.cell(
                row=i, column=j,
                value=(f'=IFERROR(COUNTIFS({rng(cat_col)},$A{i},{rng(gt_col)},"<>",{rng(corr_col)},TRUE)'
                       f'/COUNTIFS({rng(cat_col)},$A{i},{rng(gt_col)},"<>"),"n/a")'))
            cell.number_format = "0.0%"
            cell.font = BODY_FONT
            cell.border = BORDER
    autosize(ws2, [20] + [20] * len(MODELS))

    # ---------------- Generator Reliability ----------------
    ws3 = wb.create_sheet("Generator Reliability")
    ws3["A1"] = "Question generation reliability, by category (live formulas over Raw Data)"
    ws3["A1"].font = TITLE_FONT
    header_row = ["Category", "Questions generated", "With verifiable ground truth",
                  "Verifiable %", "Generator's answer key wrong", "Wrong key % (of verifiable)"]
    for j, h in enumerate(header_row, start=1):
        ws3.cell(row=3, column=j, value=h)
    style_header_row(ws3, 3, len(header_row))
    ws3.row_dimensions[3].height = 30

    for i, cat in enumerate(CATEGORIES, start=4):
        ws3.cell(row=i, column=1, value=cat).font = BODY_FONT
        ws3.cell(row=i, column=2, value=f'=COUNTIF({rng(cat_col)},$A{i})').font = BODY_FONT
        ws3.cell(row=i, column=3, value=f'=COUNTIFS({rng(cat_col)},$A{i},{rng(gt_col)},"<>")').font = BODY_FONT
        ws3.cell(row=i, column=4,
                 value=f'=IFERROR(C{i}/B{i},"n/a")').number_format = "0.0%"
        ws3.cell(row=i, column=5,
                 value=f'=COUNTIFS({rng(cat_col)},$A{i},{rng(key_ok_col)},FALSE)').font = BODY_FONT
        ws3.cell(row=i, column=6,
                 value=f'=IFERROR(E{i}/C{i},"n/a")').number_format = "0.0%"
        for c in range(1, 7):
            ws3.cell(row=i, column=c).border = BORDER
            if c not in (4, 6):
                ws3.cell(row=i, column=c).font = BODY_FONT

    # totals row
    tr = 4 + len(CATEGORIES)
    ws3.cell(row=tr, column=1, value="TOTAL").font = BOLD_FONT
    ws3.cell(row=tr, column=2, value=f"=SUM(B4:B{tr-1})").font = BOLD_FONT
    ws3.cell(row=tr, column=3, value=f"=SUM(C4:C{tr-1})").font = BOLD_FONT
    ws3.cell(row=tr, column=4, value=f"=C{tr}/B{tr}").number_format = "0.0%"
    ws3.cell(row=tr, column=4).font = BOLD_FONT
    ws3.cell(row=tr, column=5, value=f"=SUM(E4:E{tr-1})").font = BOLD_FONT
    ws3.cell(row=tr, column=6, value=f"=E{tr}/C{tr}").number_format = "0.0%"
    ws3.cell(row=tr, column=6).font = BOLD_FONT
    for c in range(1, 7):
        ws3.cell(row=tr, column=c).border = BORDER
    autosize(ws3, [20, 18, 22, 14, 22, 20])

    # ---------------- Cost Log (imported, not formula-derived -- real billed amounts) ----------------
    if os.path.exists(COST_CSV_PATH):
        cost_df = pd.read_csv(COST_CSV_PATH, header=None, skip_blank_lines=False)
        ws4 = wb.create_sheet("Cost Log")
        ws4["A1"] = "Real per-call spend (from provider batch API usage -- not a formula; these are the actual billed token counts)"
        ws4["A1"].font = TITLE_FONT
        ws4.merge_cells("A1:H1")
        for i, row in enumerate(cost_df.itertuples(index=False), start=3):
            for j, val in enumerate(row, start=1):
                if pd.isna(val):
                    continue
                cell = ws4.cell(row=i, column=j, value=val)
                cell.font = HEADER_FONT if i == 3 else BODY_FONT
                if i == 3:
                    cell.fill = HEADER_FILL
        autosize(ws4, [24, 32, 10, 14, 14, 16, 16, 18])

    wb.save(OUT_PATH)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
