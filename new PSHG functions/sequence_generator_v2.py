from synthetic_birefringence import SyntheticRetarder, find_retarder_settings

# ---------------------------------------------------------------------------
# Target synthetic retarder
# ---------------------------------------------------------------------------
delta_waves   = 0.25
fast_axis_deg = 60          # re-sweep this now that handedness is enforced —
                            # the optimum should be broad, not a 5 deg spike.

# ---------------------------------------------------------------------------
# Handedness oracle settings
# ---------------------------------------------------------------------------
# The calibration stores only |S3|, so the search used to pick handedness at
# random on the near-circular steps.  These options force the chosen (HWP, QWP)
# to carry the handedness the target actually needs.
handedness_oracle = True    # set False to reproduce the old |S3|-only behaviour
gen_input_deg     = 0.0     # linear angle feeding the HWP+QWP generator (0 = horizontal;
                            # set 90 if your generator is fed vertical light)
oracle_sign       = +1      # flip to -1 if enabling the oracle makes the
                            # correction worse everywhere (S3 sign convention flipped)

hwp, qwp, results = find_retarder_settings(
    cal_dir='.',
    delta_waves=delta_waves,
    fa_deg=fast_axis_deg,
    handedness_oracle=handedness_oracle,
    gen_input_deg=gen_input_deg,
    oracle_sign=oracle_sign,
)

import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

wb = Workbook()
ws = wb.active
ws.title = 'HWP QWP Angles'

header_font   = Font(name='Arial', bold=True, size=11)
header_fill   = PatternFill('solid', start_color='D9E1F2')
pred_fill     = PatternFill('solid', start_color='EAF3DE')   # soft green for predicted cols
hand_fill     = PatternFill('solid', start_color='FCE4D6')   # soft coral for handedness col
centre        = Alignment(horizontal='center')
header_border = Border(bottom=Side(style='medium', color='4472C4'))

headers = [
    ('C', 'HWP',     header_fill),
    ('D', 'QWP',     header_fill),
    ('E', 'ψ pred',  pred_fill),
    ('F', 'χ pred',  pred_fill),
    ('G', 'DOLP',    pred_fill),
    ('H', 'Δ match', pred_fill),
    ('I', 'hand',    hand_fill),    # informational only; acquisition reads C & D
]

for col_letter, label, fill in headers:
    cell           = ws[f'{col_letter}3']
    cell.value     = label
    cell.font      = header_font
    cell.fill      = fill
    cell.alignment = centre
    cell.border    = header_border

value_font      = Font(name='Arial', size=11)
value_font_pred = Font(name='Arial', size=11, italic=True,
                       color='3B6D11')   # muted green to distinguish from inputs
value_font_hand = Font(name='Arial', size=11, italic=True, color='9C4221')

for i, r in enumerate(results):
    row      = 4 + i
    is_last  = (i == len(results) - 1)
    bot_side = Side(style='thin', color='8EA9C1') if is_last else Side()

    # HWP and QWP (integer degrees)
    for col_letter, key in (('C', 'hwp'), ('D', 'qwp')):
        cell           = ws[f'{col_letter}{row}']
        cell.value     = int(round(r[key]))
        cell.font      = value_font
        cell.alignment = centre
        cell.border    = Border(
            left=Side(style='thin', color='B8CCE4'),
            right=Side(style='thin', color='B8CCE4'),
            bottom=bot_side,
        )

    # Predicted ellipse parameters (1 dp) and match error (4 dp)
    pred_values = [
        ('E', round(r['alpha_target'], 1)),
        ('F', round(r['chi_target'],   1)),
        ('G', round(r['dolp_target'],  3)),
        ('H', round(r['match_error'],  4)),
    ]
    for col_letter, value in pred_values:
        cell           = ws[f'{col_letter}{row}']
        cell.value     = value
        cell.font      = value_font_pred
        cell.alignment = centre
        cell.border    = Border(
            left=Side(style='thin', color='C0DD97'),
            right=Side(style='thin', color='C0DD97'),
            bottom=bot_side,
        )

    # Handedness of the produced state (R = right, L = left, - = ~linear)
    sign = r.get('gen_s3_sign', 0)
    hand = 'R' if sign > 0 else 'L' if sign < 0 else '-'
    cell           = ws[f'I{row}']
    cell.value     = hand
    cell.font      = value_font_hand
    cell.alignment = centre
    cell.border    = Border(
        left=Side(style='thin', color='F2C2A6'),
        right=Side(style='thin', color='F2C2A6'),
        bottom=bot_side,
    )

for col_letter, width in (('C',10),('D',10),('E',10),('F',10),('G',9),('H',10),('I',7)):
    ws.column_dimensions[col_letter].width = width

path     = os.path.abspath(os.getcwd())
fileName = f'delta_waves={delta_waves:.3f}_fast_axis={fast_axis_deg:2.0f}.xlsx'
wb.save(os.path.join(path, fileName))
print(f'Saved: {os.path.join(path, fileName)}')
