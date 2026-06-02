# 模組 4-D：屬性變更與特殊關鍵字
DICT_KEYWORDS_EXT = """
【🧰 屬性變更與特殊關鍵字字典 (DICT_KEYWORDS_EXT)】
1. 關鍵字獲得 (gain_keyword):
   - `{"type": "gain_keyword", "target": {選取器}, "keywords": {關鍵字物件}, "duration": "turn"|"continuous"}`
   - 【關鍵字物件內容 (全量定義)】：
     - `"impact": 數字` (衝擊)
     - `"damage": 數字` (傷害)
     - `"twice_attack": true` (2次攻擊 / 兩次攻擊)
     - `"twice_block": true` (2次阻擋 / 兩次阻擋)
     - `"impact_nullify": true` (衝擊無效)
     - `"step": true` (步進)
     - `"snipe": true` (狙擊)
     - `"must_block": true` (必須要阻擋)
     - `"cannot_be_blocked": true` (不能被阻擋)
     - `"targeting_cost": {代價積木}` (指定抗性代價：例如若不丟牌則不能選擇)

2. 能源與AP消耗變更 (cost_reduction):
   - `{"type": "cost_reduction", "target": {選取器}, "attribute": "energy"|"ap", "value": 數字, "duration": "turn"|"continuous"}`
   - 【動態數值格式】：若減費數值不固定，將 value 改為：
     `"value": {"dynamic": {"multiplier": 數字, "factor": {"target": {選取器}, "eval_type": "card_count"|"unique_energy_requirement"}}}`

3. 其他屬性與效果賦予：
   - `{"type": "treat_as_name", "target": {選取器}, "name": "卡名"}`
   - `{"type": "treat_as_color", "target": {選取器}, "color": "all"|顏色}`
   - `{"type": "treat_energy_req_as_color", "target": {選取器}, "color": "all"|顏色}` (💡 應用：處理「此卡的能源需求也被視為全部顏色」)
   - `{"type": "gain_effect", "target": {選取器}, "gained_trigger": "觸發時機", "effects": [動作陣列]}`
   - `{"type": "apply_player_restriction", "player": "self"|"opponent", "restriction": "cannot_play_from_hand", "duration": "turn"}`
"""
