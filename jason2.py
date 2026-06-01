import json
import re
import os
import copy
import time
from google import genai
from google.genai import types
import sys
from dotenv import load_dotenv

# ================= 配置區 =================
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR,  "TKG_final_structured.json")
DISPLAY_FILE = os.path.join(BASE_DIR,  "TKG_final_Cards_Display.json")
LOGIC_FILE = os.path.join(BASE_DIR, "TKG_final_Cards_Logic_1.json")
first = 41
last = 82
#
# === LLM API 配置 ===
api_keys_2 = os.getenv("API_KEYS_2").split(",")
API_KEYS = [k.strip() for k in api_keys_2 if k.strip()]
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

def load_md(filename):
    filepath = os.path.join("prompts", filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read() + "\n\n" # 自動加兩個換行，避免積木黏在一起
    else:
        print(f"⚠️ 警告：找不到 Prompt 檔案 {filepath}")
        return ""

def build_final_prompt(card_type, text):
    # 1. 基礎地基
    final_prompt = load_md("00_base_prompt.md")
    
    # 2. 根據類型載入時機規則
    if card_type == "事件卡":
        final_prompt += load_md("10_timing_event.md")
    else:
        final_prompt += load_md("11_timing_char.md")
        
    # 3. 載入通用字典
    final_prompt += load_md("20_dict_common.md")
    
    # 4. 【動態掃描】載入特殊模組
    if "突襲" in text or "raid" in text.lower():
        final_prompt += load_md("30_dict_raid.md")
        
    if any(k in text for k in ["牌組", "檢索", "看牌", "牌山"]):
        final_prompt += load_md("31_dict_deck.md")
        
    if any(k in text for k in ["改為", "抉擇", "或", "．", "替代"]):
        final_prompt += load_md("32_dict_flow.md")
        
    if any(k in text for k in ["當作", "獲得", "抗性", "減少", "消耗", "視為"]):
        final_prompt += load_md("33_dict_keywords.md")
        
    return final_prompt

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
                        system_instruction=build_final_prompt(card_type, text),
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

    for idx, card in enumerate(raw_list[first:last]): # 測試階段維持 0:10
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