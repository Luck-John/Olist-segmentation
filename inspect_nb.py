import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('notebooks/Segmentation_03_modelisation.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Print output text of key cells
for idx in [9, 14, 15, 19, 21]:
    cell = nb['cells'][idx]
    src = ''.join(cell['source'])
    header = [l.strip() for l in src.split('\n') if 'SECTION' in l or 'MEILLEUR' in l]
    print(f"=== Cell {idx}: {header[0] if header else 'unknown'} ===")
    
    for o in cell.get('outputs', []):
        if o.get('output_type') == 'stream':
            txt = ''.join(o['text'])
            print(txt[:1000])
    print()
    print("---")
    print()
