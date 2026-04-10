import json
import os

# 讀取剛剛爬下來的陣列版 JSON
input_file = r"C:\Users\wei\Documents\UA_APP0.1\Log_jason\backend\data\cgh_final_structured.json"
output_file = r"C:\Users\wei\Documents\UA_APP0.1\Log_jason\backend\data\CGH_final_structured.json"

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

for card in data:
    # 將被改成陣列的標籤，全部還原回原本的單一值
    for key in ['color', 'type', 'ap', 'energy', 'bp', 'gen_energy']:
        if key in card and isinstance(card[key], list):
            # 取出陣列裡的第一個值，還原為原本的字串或數字格式
            card[key] = card[key][0] if len(card[key]) > 0 else ""

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✨ 格式已成功還原，並存為 {output_file}！")