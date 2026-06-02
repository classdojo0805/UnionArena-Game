# 模組 4-C：高級流程控制 (抉擇與分歧)
DICT_FLOW_ADV = """
【🧰 高級流程控制字典 (DICT_FLOW_ADV)】
1. 條件分歧 (conditional_branch):
   - `{"type": "conditional_branch", "condition": {條件}, "if_true": [動作陣列], "if_false": [動作陣列]}`
   - 💡 應用：處理「...的情況下，改為...」，將修改後的動作放 `if_true`。

2. 替代代價 (alternative_cost):
   - `{"type": "alternative_cost", "original_cost": {"type": "pay_ap", "amount": 1}, "new_cost": {替代動作積木}}`
   - 💡 應用：處理「發動效果時，可以不支付 AP 改為將手牌...」。

3. 效果賦予與複製 (gain_effect):
   - `{"type": "gain_effect", "target": {選取器}, "gained_trigger": "main_act"|"on_play"等, "effects": [動作陣列]}`
   - 💡 應用：處理「獲得被選擇角色的 1 個主起動效果」或「賦予其他卡片新的能力」。
4. 抉擇效果 (choose_effect):
   - `{"type": "choose_effect", "player": "self"|"opponent", "amount": 數字, "modifier": "exact"|"up_to", "options": [ [動作陣列1], [動作陣列2] ]}`
   - 💡 應用：處理「選擇以下其中一項：」或「從以下選擇 X 項：」。請將各個選項的執行動作分別包裝成獨立陣列，放入 options 中。
"""