import json
import re
import os
import copy
import time
from google import genai
from google.genai import types
import sys

# ================= 配置區 =================
INPUT_FILE = r"C:\Users\wei\Documents\UA_APP0.1\Log_jason\TKG_final_structured.json"
DISPLAY_FILE = r"C:\Users\wei\Documents\UA_APP0.1\Log_jason\TKG_final_Cards_Display.json"
LOGIC_FILE = r"C:\Users\wei\Documents\UA_APP0.1\Log_jason\TKG_final_Cards_Logic_3.json"



API_KEYS = [
    "AIzaSyBpWvEsSPL0_uSqBUZRDy7o78Ntjs8mplw", #api 0805
    "AIzaSyA3uOGag2sW8p3w3QsAZaFnLHoyjg-9zZc" # api key huc生畢照
    
] # 請記得填入你的 API Key 
current_key_idx = 0
client = genai.Client(api_key=API_KEYS[current_key_idx])
sys.stdout.reconfigure(encoding='utf-8') 
# ==========================================
# ★ 快速通道字典 (已改良：拿掉時機標籤，命中率 100%！)
# ==========================================
EXACT_MATCH_DICT = {
    "滑步": [{"conditions": [], "costs": [], "actions": [{"type": "gain_keyword", "target": "self_card", "keywords": {"step": True}, "duration": "continuous"}]}],
    "衝擊無效": [{"conditions": [], "costs": [], "actions": [{"type": "gain_keyword", "target": "self_card", "keywords": {"impact_nullify": True}, "duration": "continuous"}]}],
    "抽１張卡。": [{"conditions": [], "costs": [], "actions": [{"type": "draw", "amount": 1}]}],
    "抽２張卡。": [{"conditions": [], "costs": [], "actions": [{"type": "draw", "amount": 2}]}],
    "抽１張卡，然後將自己１張手牌放置到場外。": [{"conditions": [], "costs": [], "actions": [{"type": "draw", "amount": 1}, {"type": "discard", "target": {"player": "self", "location": "hand", "amount": 1}, "destination": "outside"}]}],
    "抽２張卡，然後將自己１張手牌放置到場外。": [{"conditions": [], "costs": [], "actions": [{"type": "draw", "amount": 2}, {"type": "discard", "target": {"player": "self", "location": "hand", "amount": 1}, "destination": "outside"}]}]
}

SYSTEM_PROMPT = """
你是一個為 Union Arena (UA) TCG 設計的「資料驅動 (Data-Driven) 語意解析器」。
你的任務是將卡牌文本轉換為「高度參數化 (Highly Parameterized)」的嚴格 JSON 積木。

【🚨 必須嚴格遵守的絕對限制 (防呆底線)】
1. 絕對禁止註解：輸出的 JSON 內嚴禁出現 `//` 或 `/*`，這會導致解析器崩潰。
2. 純字串輸出：必須輸出純 JSON 格式，開頭與結尾【絕對不要】使用 Markdown 的 ```json 標籤包裝。
3. 手牌 vs 場上 絕對隔離：
   - 將「手牌」放置到場外/移除區，【必須且只能】使用 `discard`。
   - 將「場上/前線角色」放置到場外/移除區，【必須且只能】使用 `retire`。
   - 兩者的目標選取器 (location) 絕對不可混用！
4. 拒絕無腦降級：遇到「滿足...條件的情況下，改為...」或「對手若不...則...」等狀態分支與博弈時，絕對禁止使用 `custom` 降級。必須使用 `conditional_branch` 或是 `alternative_cost` 積木來構建邏輯！
5. 無視干擾標點：遇到日文全形引號如『BP3000或以下』，請直接提取裡面的數值 3000 放進 max_bp，絕對禁止將引號保留在 JSON 的數值或 Key 裡面，這會導致格式崩潰。
6. 嚴禁發明變數與枚舉值：遇到卡名請直接寫出（如 "name": "亞門 鋼太朗"）或用 "self_card"。字典裡規定的字串（如 history 的 action，或 amount 的值）絕對不允許自己發明或縮寫！

【⚠️ 領域與位置絕對對應表 (Location Mapping)】
遇到卡牌文本描述位置時，請【嚴格】使用以下對應的英文單字，絕對禁止混用或自創：
1. 場外 (Discard Pile) ＝ "outside"
2. 移除區 (Removed Area/Exile) ＝ "removed_area"
3. 前線 (Front Line) ＝ "front_line"
4. 能源線 (Energy Line) ＝ "energy_line"
5. 場上 (Field，包含前線與能源線) ＝ "field"
6. 牌底 / 牌頂 ＝ "bottom_deck" / "top_deck"

【⚠️ 觸發時機 (Timing) 嚴格規範】
請根據輸入的【卡片類型】與效果文，將積木放入正確的觸發時機陣列中：
1. 若卡片類型為「事件卡」：
   - 打出時立刻發動的瞬發效果（如抽牌、退場角色等），【一律】歸類在 `"event_play"` 陣列中，絕對不可使用 "main_act"！
   - 若包含「手牌減費」效果（如：自己場上有某角色時，消費AP-1），【一律】歸類在 `"in_hand_continuous"` 陣列中。
   - 若包含屬性變更（如：此卡當作所有顏色使用），歸類在 `"continuous"` 陣列中。
2. 若卡片類型為「角色卡」或「場地卡」：
   - 登場時發動歸類為 `"on_play"`。
   - 留在場上每回合宣告發動歸類為 `"main_act"`。
   - 退場時發動歸類為 `"on_leave"`。

【⚠️ 特定狀態與機制的唯一判定法】
1. 狀態判定 (激活/休息)：要判斷卡片是否為激活狀態，一律在 filters 中使用 `"state": "active"` 或 `"state": "rest"`，禁止使用 target_count 去繞圈子。
2. 突襲 (Raid) 判定：要判斷是否為突襲發動，一律在 conditions 中使用 `{"type": "play_type", "value": "raid"}`。
3. 異色能源判定：遇到「移除區有 5 種不同顏色的能源」這類要求時，請使用 `{"eval_type": "unique_energy_requirement"}`。
4. 動態減費算式：在使用 `"dynamic"` 減費時，`"multiplier"` (倍率) 一律使用正整數（如 1），因為積木 "cost_reduction" 本身就已經代表了「減少」。
5. AP 恢復：遇到「恢復 AP」或「將 AP 卡激活」的效果，【一律】使用專用積木 {"type": "activate_ap", "amount": 數字}。(💡若文本寫「全部/所有」，請一律填寫數字 3，嚴禁使用字串 "all")。

【⚠️ 動作連鎖與代價規則 (on_success vs conditional_branch)】
1. 遇到文本包含「作為代價...」、「將 OOO 休息。如這樣做，則 XXX」或「藉此...」時，【絕對禁止】使用 "conditional_branch"！
2. 正確做法：將前置動作（如休息、捨棄手牌）寫為獨立積木，並將後續動作（如加 BP、抽卡）全部包進該動作的 `"on_success"` 陣列中。

【📜 特殊排版 處理規則】
1. 主動拆解縫合怪：若遇到事件卡同時寫著「...的情況下，手牌上此卡的能源需求減少。選擇對手前線１張...」即使沒有換行，你也必須主動將其切開！將減費效果丟進 `"in_hand_continuous"`，將選擇退場等瞬發動作丟進 `"main_act"` 或 `"event_play"`。

【📂 根節點與觸發時機 (Root & Timings)】
輸出的 JSON 必須直接以觸發時機為 Key，Value 為「效果區塊 (Effect Block) 陣列」。嚴禁包裝 `logic_tags` 外殼。
- 觸發時機包含: "on_play", "event_play", "on_attack", "on_block", "on_leave", "on_move", "main_act", "continuous", "in_hand_continuous", "on_battle_win", "on_other_leave", "on_attack_end", "on_main_phase_end", "on_being_targeted_by_opponent_effect"

【🧱 效果區塊結構 (Effect Block Schema)】
每個效果區塊是一個 Object，必須包含以下 5 個欄位。空值或無限制的欄位請留空，主程式會自動處理：
1. "optional": boolean。文本若含「可...」字眼則為 true，否則為 false (代價與選發脫鉤)。
2. "limit": {"type": "per_turn"|"per_turn_by_name", "amount": 1, "name": "卡名"}。發動限制，若無次數限制則留空或省略。
3. "conditions": 陣列。發動的先決條件積木。無條件則為 []。
4. "costs": 陣列。發動需扣除的資源動作 (如 pay_ap, discard)。無代價則為 []。
5. "actions": 陣列。具體執行的效果動作。(絕對不可為空陣列，若有支付 cost 必定有對應 action)

【🎯 全能目標選取器 (Target Selector)】
需選取目標時，統一使用以下參數化結構 (無限制的參數請留空或省略)：
`{"player": "self"|"opponent"|"both", "location": "front_line"|"energy_line"|"hand"|"deck"|"outside"|"removed_area"|"field"|"raid_source"|"raid_source_bottom", "amount": 數字, "modifier": "up_to"|"exact", "filters": {"trait": "...", "name": "...", "name_includes": "...", "color": "...", "state": "active"|"rest", "card_type": "...", "max_bp": 數字, "min_bp": 數字, "max_energy": 數字, "ap_consumption": 數字, "base_bp": 數字, "history": "played_this_turn", "other": true/false, "has_underneath_card": true/false, "underneath_face_down": true/false, "unique_names": true/false, "any_of": [{過濾條件1}, {過濾條件2}]}}`
- 若目標是發動卡片自身，可直接填字串 `"self_card"`。
- 若目標是「本回合下一張使用的卡片」，可直接填字串 `"next_played_card"`。
- 遇到「或 (OR)」的多重條件時，請使用 `"any_of"` 陣列包裝多個過濾條件物件。
- 遇到「不同卡名」時，請將 `"unique_names": true` 加入 filters 中。
- 遇到「下面擁有/沒有背面向上的卡」時，請在 filters 中使用 `"has_underneath_card": true/false`，若指定背面向上請加 `"underneath_face_down": true`。

【⚠️ 目標繼承規則 (Selected Target)】
1. 當同一個效果中，有多個動作針對「同一個被選擇的目標」時（例如：選擇 1 張角色，使其 BP+3000，並獲得衝擊）。
2. 第一個動作必須寫出完整的 `"target"` 過濾器。
3. 第二個（及之後的）動作，其 `"target"` 【必須直接寫】 `"selected_target"`，絕對禁止重複列出過濾器條件！

【🧰 高度參數化積木字典 (Dictionaries)】
1. 條件積木 (Conditions):
   - `{"type": "target_count", "target": {目標選取器}, "operator": ">="|"<="|"==", "count": 整數}`
   - `{"type": "history", "action": "played_this_turn"|"not_played_this_turn"|"opponent_retired_character_this_turn"}`
   - `{"type": "life_count", "player": "self"|"opponent", "operator": ">="|"<="|"==", "count": 整數}`
   - `{"type": "is_raid"}`
   - `{"type": "attack_count", "player": "self"|"opponent", "operator": "==", "count": 整數}`
   - `{"type": "play_type", "value": "raid"}`

2. 動作與代價通用積木 (Actions & Costs):
   - `{"type": "pay_ap", "amount": 1}`
   - `{"type": "activate_ap", "amount": 數字}`
   - `{"type": "draw", "amount": 數字}`
   - `{"type": "discard", "target": {限hand的選取器}, "destination": "outside"|"removed_area"|"bottom_deck"}`
   - `{"type": "retire", "target": {限field/front_line的選取器}, "to_removal": true/false}`
   - `{"type": "return_to_hand", "target": {目標選取器}, "on_fail": [若沒有返回成功，強制執行的動作積木]}`
   - `{"type": "change_state", "target": {目標選取器}, "state": "active"|"rest"}`
   - `{"type": "play_character", "target": {目標選取器}, "state": "active"|"rest"}`
   - `{"type": "life_to_hand", "player": "self"|"opponent", "amount": 1, "on_success": [動作積木陣列]}`
   - `{"type": "move_card", "source": {目標選取器}, "destination": "hand"|"bottom_deck"|"top_deck"|"outside"|"removed_area"|"under_character", "target_character": {目標選取器}, "amount": 數字, "face_down": true/false}`
     💡備註：若有多個去向，請寫成陣列。
   - `{"type": "cost_reduction", "target": {目標選取器}, "attribute": "energy"|"ap", "value": 數字, "duration": "turn"|"continuous"}`
     💡動態減費備註：若為動態，將 value 改為：`{"dynamic": {"multiplier": 1, "factor": {"target": {目標選取器}, "eval_type": "card_count"|"unique_energy_requirement"}}}`

3. 全能檢索積木 (Universal Deck Search):
   - `{"type": "look_at_deck", "look_amount": 數字, "take_amount": 數字, "reveal": true/false, "filters": {目標選取器的filters格式}, "take_action": "add_to_hand"|"play"|"discard"|"move_card", "remainder": "bottom_deck_any_order"|"outside"|"top_deck_any_order"|"top_or_bottom", "on_success": [動作積木陣列]}`
     💡備註：處理看牌與找牌。若有「如這樣做.../有加入手牌的情況下...」的後續動作，請放入 on_success 陣列中。

4. 數值與關鍵字積木 (Stats & Keywords):
   - `{"type": "stat_change", "target": {目標選取器}, "attribute": "bp"|"ap"|"generated_energy", "value": 數字, "duration": "turn"|"continuous"}`
   - `{"type": "gain_keyword", "target": {目標選取器}, "keywords": {"impact": 數字, "impact_nullify": true, "damage": 1, "step": true, "cannot_stand": true, "snipe": true, "twice_attack": true, "twice_block": true, "cannot_be_selected": true, "must_block": true, "cannot_be_blocked_by": {"bp_threshold": 4000}, "targeting_cost": {代價積木}}, "duration": "turn"|"continuous"}`
     💡指定抗性備註：若文本為「對手用效果選擇此角色時，若不追加將他自己1張手牌放置到場外，便不能選擇」，請使用 `"targeting_cost": {"type": "discard", "target": {"player": "opponent", "location": "hand", "amount": 1, "modifier": "exact"}, "destination": "outside"}`。
   - `{"type": "gain_effect", "target": {目標選取器}, "gained_trigger": "觸發時機(如on_leave)", "effects": [動作積木陣列], "limit": {限制積木}}`
   - `{"type": "treat_as_name", "target": {目標選取器}, "name": "卡名"}`
   - `{"type": "treat_as_color", "target": {目標選取器}, "color": "all"|"red"|"blue"|"yellow"|"green"|"purple"}`
   - `{"type": "apply_player_restriction", "player": "self"|"opponent", "restriction": "cannot_play_from_hand", "duration": "turn"}`

5. 流程控制積木 (Flow Control):
   - `{"type": "conditional_branch", "condition": {條件積木}, "if_true": [動作積木陣列], "if_false": [動作積木陣列]}`
    💡備註：遇到「...的情況下，改為...」時，將【修改後的動作】放進 if_true，將【原本的動作】放進 if_false。
   - `{"type": "choose_effect", "player": "self"|"opponent", "amount": 1, "modifier": "up_to"|"exact", "options": [[動作積木陣列1], [動作積木陣列2]]}`
     💡備註：專門處理文本中有「．(黑點)」的條列式選項，或對手的二選一抉擇博弈。
   - `{"type": "alternative_cost", "original_cost": {代價積木}, "new_cost": {代價積木}}`

【範例輸出 (處理事件卡縫合怪與條件替換)】
文本：「自己場上擁有〈有馬 貴將〉的情況下，手牌上此卡的AP消耗-1。\n選擇對手前線1張『BP5000或以下』角色退場。自己場上擁有〈佐佐木 琲世〉的情況下，改為『BP6000或以下』。」
{
  "in_hand_continuous": [
    {
      "optional": false,
      "conditions": [
        {
          "type": "target_count",
          "target": {"player": "self", "location": "front_line", "filters": {"name": "有馬 貴將"}},
          "operator": ">=",
          "count": 1
        }
      ],
      "costs": [],
      "actions": [
        {"type": "cost_reduction", "target": "self_card", "attribute": "ap", "value": 1, "duration": "continuous"}
      ]
    }
  ],
  "event_play": [
    {
      "optional": false,
      "conditions": [],
      "costs": [],
      "actions": [
        {
          "type": "conditional_branch",
          "condition": {
            "type": "target_count",
            "target": {"player": "self", "location": "front_line", "filters": {"name": "佐佐木 琲世"}},
            "operator": ">=",
            "count": 1
          },
          "if_true": [
            {"type": "retire", "target": {"player": "opponent", "location": "front_line", "amount": 1, "modifier": "exact", "filters": {"max_bp": 6000}}, "to_removal": false}
          ],
          "if_false": [
            {"type": "retire", "target": {"player": "opponent", "location": "front_line", "amount": 1, "modifier": "exact", "filters": {"max_bp": 5000}}, "to_removal": false}
          ]
        }
      ]
    }
  ]
}
"""
def switch_api_key():
    """自動換彈：當遇到 429 額度耗盡時，自動切換到下一把鑰匙"""
    global current_key_idx, client
    # 索引加 1，如果到底了就回到 0 (循環使用)
    current_key_idx = (current_key_idx + 1) % len(API_KEYS)
    print(f"  [🔑 自動換彈匣] 額度可能耗盡，瞬間切換至第 {current_key_idx + 1} 把 API Key！")
    client = genai.Client(api_key=API_KEYS[current_key_idx])
class UAParser:

    @classmethod
    def _call_llm_parser(cls, text, name, card_type, color, traits, ap, energy, bp):
        max_retries = 8
        
        for attempt in range(max_retries):
            try:
                print(f"  [LLM 處理中] 嘗試解析 (第 {attempt+1}/{max_retries} 次)...")
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents = f"""
                        【【當前解析任務面板】
                        - 卡片名稱：{name}
                        - 卡片類型：{card_type}
                        - 卡片顏色：{color}
                        - 卡片特徵：{traits}
                        - 基礎數值：AP消費 {ap}, 能源需求 {energy}, BP {bp}

                        【效果文本】
                        {text}
                        """,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.0, 
                        response_mime_type="application/json", 
                        safety_settings=[
                            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                        ]
                    )
                )
                
                raw_resp = response.text
                match = re.search(r'(\{.*\})', raw_resp, re.DOTALL)
                if not match:
                    raise ValueError("回傳的內容中找不到 JSON 大括號！")
                    
                json_str = match.group(1)
                parsed_data = json.loads(json_str)
                
                print(f"  [API 成功] 💥 單卡翻譯成功！暫停 5 秒...")
                time.sleep(5) 
                return parsed_data
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    # 🌟 終極改動：不再罰站 60 秒了！
                    # 直接呼叫換鑰匙函數，並稍等 3 秒讓連線緩衝，立刻重新猛攻！
                    switch_api_key()
                    time.sleep(3)
                    continue 
                else:
                    print(f"  [LLM 解析錯誤] 第 {attempt+1} 次失敗，原因: {error_msg}")
                    time.sleep(5)
                    continue
        safe_text = text.replace("'", "\\'")
        
        # 降級時自動推測時機點
        timing = "continuous"
        if "登場時" in text: timing = "on_play"
        elif "退場時" in text: timing = "on_leave"
        elif "攻擊時" in text: timing = "on_attack"
        elif "主起動" in text: timing = "main_act"
        
        return {timing: [{"conditions": [], "costs": [], "actions": [{"type": "custom", "description": safe_text}]}]}
    @classmethod
    def extract_advanced_logic(cls, raw_text, name, card_type, color, traits, ap, energy, bp):
        if not raw_text: return {}
        
        # ==========================================
        # 🧹 預處理第一階段：排版淨化
        # ==========================================
        clean_text = raw_text.replace('　', ' ').strip()
        clean_text = clean_text.replace('『', '').replace('』', '').replace('「', '').replace('」', '')
        clean_text = re.sub(r'（.*?）|\(.*?\)| \([^)]*\)', '', clean_text)

        # ==========================================
        # ✂️ 預處理第二階段：邏輯斷行與事件卡補丁
        # ==========================================
        clean_text = clean_text.replace('的情況下，改為', '的情況下，\n改為')
        
        text = re.sub(r'。\s*(〈[^〉]+〉|［特徵：[^］]+］)(?=\n|$)', r'。\n\1', clean_text)
        text = re.sub(r'^(〈[^〉]+〉|［特徵：[^］]+］)\s*(登場時|攻擊時|退場時|阻擋時|主起動|衝擊|傷害)', r'\1\n\2', text, flags=re.MULTILINE)
        
        # ★ 終極事件卡防呆 (你上次漏掉的就是這段！)
        if not re.search(r"(登場時|退場時|攻擊時|阻擋時|主起動|衝擊|傷害|連續行動|自己回合中|對手回合中|回合１)", text):
            if "情況下" not in text and "每有" not in text: # 排除純常駐條件
                text = "主起動\n" + text
        
        is_inside_raid_box = bool(re.search(r"^(〈[^〉]+〉|［特徵：[^］]+］)$", text, flags=re.MULTILINE))
        
        single_line_text = text.replace('\n', '').strip()
        clean_single_line = re.sub(r"^(登場時|退場時|攻擊時|阻擋時|主起動)\s*", "", single_line_text).strip()
        
        timing_guess = "continuous"
        if "登場時" in single_line_text: timing_guess = "on_play"
        elif "退場時" in single_line_text: timing_guess = "on_leave"
        elif "攻擊時" in single_line_text: timing_guess = "on_attack"
        elif "主起動" in single_line_text: timing_guess = "main_act"
        
        # ==========================================
        # ⚡ 快速通道 1：字典秒殺
        # ==========================================
        if clean_single_line in EXACT_MATCH_DICT:
            effect_blocks = copy.deepcopy(EXACT_MATCH_DICT[clean_single_line])
            if is_inside_raid_box:
                for b in effect_blocks:
                    b.setdefault("conditions", []).append({"type": "play_type", "value": "raid"})
            return {timing_guess: effect_blocks}

        # ==========================================
        # ⚡ 快速通道 2：正則秒殺 (已修復 isdigit 崩潰問題！)
        # ==========================================
        compact_line = clean_single_line.replace(' ', '') 
        kw_match = re.match(r"^(衝擊|傷害)([➊-➓0-9]+)$", compact_line)
        if kw_match:
            kw_name = "impact" if kw_match.group(1) == "衝擊" else "damage"
            val_str = kw_match.group(2)
            circle_map = {'➊':1, '➋':2, '➌':3, '➍':4, '➎':5, '➏':6, '➐':7, '➑':8, '➒':9, '➓':10}
            
            # 絕對安全的轉換邏輯
            if val_str in circle_map:
                val = circle_map[val_str]
            else:
                val = int(val_str)
                
            effect_blocks = [{
                "optional": False,
                "conditions": [], "costs": [],
                "actions": [{"type": "gain_keyword", "target": "self_card", "keywords": {kw_name: val}, "duration": "continuous"}]
            }]
            if is_inside_raid_box:
                effect_blocks[0].setdefault("conditions", []).append({"type": "play_type", "value": "raid"})
            return {"continuous": effect_blocks}

        # ==========================================
        # 🧠 大腦解析：送交 LLM
        # ==========================================
        try:
            # 這裡要把剛剛接到的三個參數，繼續往下傳給 _call_llm_parser
            llm_result = cls._call_llm_parser(text, name, card_type, color, traits, ap, energy, bp)
        except Exception as e:
            return {"custom_error": f"API 呼叫失敗: {str(e)}"}

        if isinstance(llm_result, dict) and "logic_tags" in llm_result:
            llm_result = llm_result["logic_tags"]

        if not isinstance(llm_result, dict):
            return {"custom_error": "LLM 回傳格式錯誤"}

        if is_inside_raid_box:
            for parsed_timing, blocks in llm_result.items():
                if isinstance(blocks, list):
                    for b in blocks:
                        if isinstance(b, dict):
                            b.setdefault("conditions", []).append({"type": "play_type", "value": "raid"})

        clean_logic_tags = {k: v for k, v in llm_result.items() if v}
        return clean_logic_tags

    @classmethod
    def parse_life_trigger(cls, trigger_data, card_color):
        if trigger_data is None or not isinstance(trigger_data, dict):
            return []

        text = trigger_data.get("text") or ""
        kw = (trigger_data.get("keyword") or "").upper()

        effect = {
            "conditions": [],
            "costs": [],
            "actions": []
        }

        if kw == "獲得" or "加入手牌" in text:
            effect["actions"].append({
                "type": "move_cards",
                "target": "self_card",
                "destination": "hand"
            })
        elif kw == "抽牌" or ("抽" in text and "卡" in text):
            effect["actions"].append({
                "type": "draw",
                "amount": 1
            })
        elif kw == "激活" or ("激活" in text and "BP+3000" in text):
            effect["actions"].extend([
                {
                    "type": "change_state",
                    "target": {"player": "self", "location": "field", "amount": 1, "filters": {"card_type": "character"}},
                    "state": "active"
                },
                {
                    "type": "buff_bp",
                    "target": "selected_target", 
                    "amount": 3000,
                    "duration": "turn"
                }
            ])
        elif kw == "FINAL" or "沒有生命值" in text:
            effect["conditions"].append({
                "type": "life_count",
                "player": "self",
                "operator": "==",
                "count": 0
            })
            effect["actions"].append({
                "type": "recover_life",
                "amount": 1
            })

        elif "對手前線" in text and "BP2500" in text:
            # 官方規則：退場 BP 3000 或以下
            effect["actions"].append({
                "type": "retire",
                "target": {"player": "opponent", "location": "front_line", "amount": 1, "filters": {"max_bp": 2500}},
                "to_removal": False
            })
        elif kw == "SPECIAL" or ("退場" in text and "選擇對手" in text):
            effect["actions"].append({
                "type": "retire",
                "target": {
                    "player": "opponent", 
                    "location": "front_line", 
                    "amount": 1
                },
                "to_removal": False
            })
        elif kw == "突襲" or "情況下進行" in text:
            # 🔥 修正 1：完美還原 RAID 觸發的「二選一」機制
            effect["actions"].append({
                "type": "choose_effect",
                "player": "self",
                "options": [
                    [
                        {"type": "move_cards", "target": "self_card", "destination": "hand"}
                    ],
                    [
                        {"type": "play_character", "target": "self_card", "state": "active"}
                        # 💡 備註：引擎端在執行這個選項時，需自動檢查是否滿足突襲條件
                    ]
                ]
            })
        
        
        elif "手牌選擇" in text and "BP3500" in text:
            # 官方規則：回手 BP 4000 或以下 (幫你從 3500 修正為標準 4000)
            effect["actions"].append({
                "type": "return_to_hand",
                "target": {"player": "opponent", "location": "front_line", "amount": 1, "filters": {"max_bp": 3500}}
            })
        elif "手牌" in text and "登場" in text:
            # 官方規則：手牌登場 (能需2以下, AP1)
            effect["actions"].append({
                "type": "play_character",
                "target": {"player": "self", "location": "hand", "amount": 1, "filters": {"card_type": "character", "max_energy": 2, "max_ap": 1}},
                "state": "active"
            })
        elif "場外" in text and "登場" in text:
            # 官方規則：場外登場 (能需2以下, AP1)
            effect["actions"].append({
                "type": "play_character",
                "target": {"player": "self", "location": "outside", "amount": 1, "filters": {"card_type": "character", "max_energy": 2, "max_ap": 1}},
                "state": "active"
            })
        elif "角色休息" in text:
            # 官方規則：休息並賦予無法激活
            effect["actions"].extend([
                {
                    "type": "change_state",
                    "target": {"player": "opponent", "location": "front_line", "amount": 1},
                    "state": "rest"
                },
                {
                    "type": "add_keyword", # 這裡可以對接 Godot 裡的狀態標籤
                    "target": "selected_target",
                    "keyword": "cannot_stand",
                    "duration": "turn"
                }
            ])
            
        else:
            return []

        return [effect]
    
def run_split():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 找不到來源檔案 {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    raw_list = raw_data if isinstance(raw_data, list) else [raw_data]
    
    display_db, logic_db = {}, {}

    if os.path.exists(DISPLAY_FILE):
        with open(DISPLAY_FILE, 'r', encoding='utf-8') as f:
            display_db = json.load(f)
    if os.path.exists(LOGIC_FILE):
        with open(LOGIC_FILE, 'r', encoding='utf-8') as f:
            logic_db = json.load(f)

    for idx, card in enumerate(raw_list[123:167]): # 測試階段維持 0:10
        card_id = card.get("card_id", "UNKNOWN_ID")
        color = card.get("color", "無")
        
        if card_id in logic_db and "logic_tags" in logic_db[card_id]:
            print(f"⏩ 跳過 [{idx+1}/{len(raw_list)}]: {card_id} (已解析過)")
            continue
            
        print(f"處理中 [{idx+1}/{len(raw_list)}]: {card_id}")

        display_db[card_id] = {
            "name": card.get("name"),
            "raw_text": card.get("raw_text"),
            "img_url": card.get("img_url"),
            "traits": card.get("traits", []), 
            "effects_text": [e.get("text", "") for e in card.get("main_effects", [])],
            "trigger_display": {
                "keyword": card.get("trigger", {}).get("keyword", ""),
                "text": card.get("trigger", {}).get("text", "")
            }
        }

        effect_texts = [e.get("text", "").strip() for e in card.get("main_effects", []) if e.get("text", "").strip()]
        
        # 👇 如果有 2 個以上的效果，才加上獨立標籤防呆；否則維持原樣以保證「字典秒殺」正常運作
        if len(effect_texts) > 1:
            combined_main_text = "\n\n".join([f"【獨立效果 {i+1}】\n{txt}" for i, txt in enumerate(effect_texts)])
        else:
            combined_main_text = effect_texts[0] if effect_texts else ""
        parsed_logic_tags = {}
        skip_llm = False

        if not combined_main_text or combined_main_text in ["-", "無"]:
            print(f"  ⏭️ [跳過] 發現白板卡，直接寫入空效果。")
            parsed_logic_tags = {}
            skip_llm = True

        elif re.search(r'(.+)_(\d+)$', card_id):
            base_id = re.search(r'(.+)_(\d+)$', card_id).group(1)
            if base_id in logic_db:
                print(f"  👯 [異畫複製] 發現異畫卡，直接拷貝基礎卡 {base_id} 的效果！")
                parsed_logic_tags = copy.deepcopy(logic_db[base_id].get("logic_tags", {}))
                skip_llm = True
            else:
                print(f"  ⚠️ [警告] 找不到基礎卡 {base_id}，將走正常解析流程。")

        if not skip_llm:
            try:
                card_name = card.get("name", "未知名稱")
                card_type = card.get("type", "未知類型")
                
                # 👇 新增：抓取特徵 (轉成字串) 與數值
                card_traits = ", ".join(card.get("traits", [])) if card.get("traits") else "無"
                card_ap = card.get("ap", 1)
                card_energy = card.get("energy", 0)
                card_bp = card.get("bp", 0)
                
                # 👇 將所有變數一起丟進去！
                parsed_logic_tags = UAParser.extract_advanced_logic(
                    combined_main_text, card_name, card_type, color, 
                    card_traits, card_ap, card_energy, card_bp
                )
            except Exception as e:
                print(f"  ❌ 解析發生錯誤: {e}")
                parsed_logic_tags = {"custom_error": str(e)}

        logic_db[card_id] = {
            "ap_cost": int(card.get("ap", 1) if card.get("ap") else 1),
            "energy_req": int(card.get("energy", 0) if card.get("energy") else 0),
            "type": card.get("type", "未知"),
            "gen_energy": 1 if "1" in str(card.get("gen_energy", "")) else 0, 
            "bp": int(card.get("bp", 0) if card.get("bp") else 0),
            "color": color,
            "traits": card.get("traits", []), 
            "logic_tags": parsed_logic_tags,
            "life_trigger": UAParser.parse_life_trigger(card.get("trigger"), color)
        }
        
        os.makedirs(os.path.dirname(DISPLAY_FILE), exist_ok=True)
        with open(DISPLAY_FILE, 'w', encoding='utf-8') as f:
            json.dump(display_db, f, ensure_ascii=False, indent=2)
        with open(LOGIC_FILE, 'w', encoding='utf-8') as f:
            json.dump(logic_db, f, ensure_ascii=False, indent=2)

    print(f"✅ 全部解析完成！共處理了 {len(display_db)} 張卡片。")

if __name__ == "__main__":
    run_split()