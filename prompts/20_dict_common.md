DICT_COMMON = """
【🧰 通用積木字典 (Common Dictionary)】
1. 條件積木 (Conditions):
   - `{"type": "target_count", "target": {選取器}, "operator": ">="|"<="|"==", "count": 數字}`
   - `{"type": "history", "action": "played_this_turn"|"not_played_this_turn"|"opponent_retired_character_this_turn"}`
   - `{"type": "life_count", "player": "self"|"opponent", "operator": ">="|"<="|"==", "count": 數字}`
   - `{"type": "attack_count", "player": "self"|"opponent", "operator": "==", "count": 數字}`
   - `{"type": "is_self_turn"}`: 判定當前是否為「自己回合」。
   - `{"type": "turn_count", "operator": "==", "count": 1}`: 判定當前是否為第 1 回合。
   - `{"type": "state_check", "target": {選取器}, "state": "active"|"rest"}`: 判定目標當前的激活/休息狀態。
   - `{"type": "history", "action": "retired_by_battle"}`: 判定目標是否因「戰鬥」而退場。
   - `{"type": "history", "action": "added_to_hand_this_turn"}`: 判定本回合是否有卡片加入手牌。
   - `{"type": "history", "action": "rested_by_own_effect_this_turn"` (💡 應用：篩選「在本回合中因自己的效果而變為休息狀態」的卡片)
   - `{"type": "unique_attribute_count", "target": {選取器}, "attribute": "energy_req"|"color"|"trait", "operator": ">="|"<="|"==", "count": 數字}` (💡 應用：處理「能源需求數目有Ｘ種或以上」、「顏色有Ｘ種」)
   - `{"type": "battle_result", "result": "win"|"lose"}`: 判定當前戰鬥的結果。
   - `{"type": "battle_participant", "role": "attacker"|"defender", "filters": {過濾器}}`: 判定參與戰鬥的特定一方是否符合條件。
   - `{"type": "history", "action": "entered_field_this_turn", "target": "self_card"}`: 判定目標是否在「本回合登場」。
   - `{"type": "history", "action": "activated_effect_this_turn", "effect_type": "main_act"}`: 判定本回合是否有發動過特定類型的效果。
   
2. 動作與代價基礎積木 (Actions & Costs):
   - `{"type": "pay_ap", "amount": 1}`
   - `{"type": "activate_ap", "amount": 數字}` (💡恢復「全部AP」請填 3，嚴禁寫 "all")
   - `{"type": "draw", "amount": 數字}`
   - `{"type": "discard", "target": {限hand選取器}, "destination": "outside"|"removed_area"|"bottom_deck"}`
   - `{"type": "retire", "target": {限field選取器}, "to_removal": true/false}`
   - `{"type": "return_to_hand", "target": {選取器}, "on_fail": [動作積木陣列]}`
   - `{"type": "change_state", "target": {選取器}, "state": "active"|"rest"}`
   - `{"type": "play_character", "target": {選取器}, "state": "active"|"rest"}`
   - `{"type": "life_to_hand", "player": "self"|"opponent", "amount": 1, "on_success": [動作積木陣列]}`
   - `{"type": "move_card", "source": {選取器}, "destination": "hand"|"bottom_deck"|"top_deck"|"outside"|"removed_area"|"under_character", "target_character": {選取器}, "amount": 數字, "face_down": true/false}`
   - `{"type": "stat_change", "target": {選取器}, "attribute": "bp"|"ap"|"generated_energy", "value": 數字, "duration": "turn"|"continuous"}`
   - `{"type": "change_state", ..., "on_success": [動作積木]}`: 💡重要：現在 change_state 支援 on_success 用於處理「將其休息。如這樣做...」。
   - `{"type": "move_character", "target": {選取器}, "to_line": "front_line"|"energy_line"|"other"}`: 將角色在前後線之間移動 (支援 "other" 代表移動到另一個戰線)。
   - `{"type": "swap_position", "target1": {選取器}, "target2": {選取器}}`: 讓兩個指定的目標互相調換位置。

3. 💡 動態參數化規範 (Dynamic Parameter Formatting):
   - 遇到「BP少於或等於自己場上[特徵]張數 x 500」等計算邏輯時，禁止填寫純數字。
   - 必須將 `max_bp` 或 `min_bp` 寫成：`{"dynamic": {"multiplier": 數字, "factor": {針對該特徵的選取器}}}`。
   - 範例：`"max_bp": {"dynamic": {"multiplier": 500, "factor": {"player": "self", "location": "field", "filters": {"trait": "CCG"}}}}`。

⚠️ 代價規則：
   - 若文本包含「作為代價」、「如這樣做」、「藉此」，必須將後續效果包進前置動作的 `"on_success"` 陣列中，嚴禁平行放置！

4. 🧪 複雜文本處理規範 (Complex Text Rules):
   - 牌組檢索：
     - 遇到「查看牌庫頂 N 張，選擇 1 張加入手牌，其餘以任意順序放回牌庫底」時：
     - 禁止使用 `move_card` 或 `custom`。
     - 必須統一使用 `look_at_deck`，並將 `remainder` 設為 `"bottom_deck_any_order"`。
   
   - 關鍵字賦予：
     - 遇到「獲得 衝擊」、「獲得 傷害2」、「衝擊無效」等描述時：
     - 絕對禁止使用 `custom` 或自創 type（如 `impact_tag`）。
     - 必須統一使用 `gain_keyword` 函數。
     - 數值型關鍵字（衝擊、傷害）必須填入對應數字，布林型（2次攻擊、衝擊無效）填入 `true`。

   - 替代代價：
     - 遇到「發動...時，可以不支付 AP 改為 [動作]」時：
     - 禁止將整個效果寫在 `custom`。
     - 必須在 `costs` 陣列中使用 `alternative_cost` 積木。

   - 效果獲得：
     - 遇到「本回合中，此角色獲得 [關鍵字] 或 [能力]」時：
     - 優先檢查 `gain_keyword` 是否能處理（如衝擊、2次攻擊）。
     - 若為複雜文本能力，則使用 `gain_effect` 並定義正確的 `gained_trigger`。

5. 🎯 目標選取器規範 (Target Selector Rules):
   - 當積木中出現 `{選取器}` 時，支援使用以下通用屬性進行精確鎖定：
   - `modifier`: `"exact"` (剛好) | `"up_to"` (最多) | `"at_least"` (至少/或以上)
   - `location`: `"hand"` | `"field"` | `"deck"` | `"outside"` | `"removed_area"` 等。如果是跨區域合計計算（如：場外與移除區），請使用陣列格式，例如 `["outside", "removed_area"]`。
   - `filters`: 可包含多個條件過濾，例如 `{"name": "...", "card_type": "...", "trait": "...", "has_underneath_card": true}` 等。

"""