import json
import os

# ================= 配置區 =================
BASE_DIR = r"C:\Users\wei\Documents\UA_APP0.1\Log_jason"

# ⚠️ 填入你「最原始、只有 167 張卡」的那個 JSON 檔名 (用來對照正確卡號)
RAW_INPUT_FILE = os.path.join(BASE_DIR, "TKG_final_structured.json") 

# 4 個包含翻譯資料的檔案
FILES_TO_CLEAN = [
    "TKG_final_Cards_Logic_0.json",
    "TKG_final_Cards_Logic_1.json",
    "TKG_final_Cards_Logic_2.json",
    "TKG_final_Cards_Logic_3.json"
]

# 輸出的最終大一統檔案 (當作安全備份)
MERGED_FILE = os.path.join(BASE_DIR, "TKG_final_Cards_Logic_MERGED.json")
# ==========================================

def has_invalid_tags(obj):
    """遞迴檢查：發現 "type": "custom" 或 "custom_error" 回傳 True"""
    if isinstance(obj, dict):
        if "custom_error" in obj:
            return True
        if obj.get("type") == "custom":
            return True
        for value in obj.values():
            if has_invalid_tags(value):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if has_invalid_tags(item):
                return True
    return False

def clean_and_update_split_files():
    if not os.path.exists(RAW_INPUT_FILE):
        print(f"❌ 找不到原始卡表檔案: {RAW_INPUT_FILE}")
        return

    # 1. 取得標準 ID 名單 (167筆)
    with open(RAW_INPUT_FILE, 'r', encoding='utf-8') as f:
        raw_list = json.load(f)
        if isinstance(raw_list, dict):
            raw_list = [raw_list]
        valid_ids = {card.get("card_id") for card in raw_list if card.get("card_id")}

    final_db = {}
    seen_ids = set() # 用來記錄已經保留的卡片，防止跨檔案重複
    
    total_ghosts = 0
    total_invalid = 0
    total_duplicates = 0
    total_events_deleted = 0  # 🔥 新增：記錄刪除了多少張事件卡

    print("開始逐一清洗並更新分割檔...\n")

    # 2. 分別處理並覆蓋 4 個檔案
    for file_name in FILES_TO_CLEAN:
        file_path = os.path.join(BASE_DIR, file_name)
        if not os.path.exists(file_path):
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            logic_db = json.load(f)

        cleaned_db = {} # 用來存這個檔案清洗後的最終結果
        
        for card_id, card_data in logic_db.items():
            # 條件 A: 必須是標準名單內的卡 (過濾幽靈)
            if card_id not in valid_ids:
                total_ghosts += 1
                continue
        
            # 條件 B: 不能含有 custom 或 custom_error (過濾翻譯失敗)
            logic_tags = card_data.get("logic_tags", {})
            if has_invalid_tags(logic_tags):
                total_invalid += 1
                continue
            
            # 條件 C: 跨檔案去重 (如果這張卡在之前的檔案已經存過了，就跳過)
            if card_id in seen_ids:
                total_duplicates += 1
                continue
                
            # 通過所有考驗，寫入清洗後的字典
            cleaned_db[card_id] = card_data
            final_db[card_id] = card_data
            seen_ids.add(card_id)

        # 🌟 將清洗後的資料，直接覆蓋寫回原本的 _0 ~ _3 檔案！
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_db, f, ensure_ascii=False, indent=2)
            
        print(f"✅ [{file_name}] 已更新！完美保留: {len(cleaned_db)} 筆")

    # 3. 順便輸出最終大一統檔案當作備份
    with open(MERGED_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_db, f, ensure_ascii=False, indent=2)

    print("\n" + "="*50)
    print(f"🎉【終極清理與原檔更新】執行完成！")
    print(f"🛡️ 刪除了 {total_ghosts} 筆「幽靈卡號」")
    print(f"🧹 剔除了 {total_invalid} 筆「翻譯失敗」(含 custom 或報錯)")
    print(f"🔄 清除了 {total_duplicates} 筆「跨檔案重複資料」")
    print(f"💥 移除了 {total_events_deleted} 筆「事件卡」(準備進行全新翻譯)")
    print("-" * 50)
    print(f"✨ 你的 4 個分割檔 (_0 ~ _3) 已經被徹底淨化並寫入原檔！")
    print(f"✨ 同時備份了一份完美總檔至: TKG_final_Cards_Logic_MERGED.json")
    print(f"✅ 目前實際擁有的無瑕疵卡片數: {len(final_db)} / {len(valid_ids)}")
    
    if len(final_db) < len(valid_ids):
        print(f"\n👉 距離 100% 完成只差最後 {len(valid_ids) - len(final_db)} 張了！")
        print(f"   (請在爬蟲程式更新 Prompt 後，執行爬蟲以補完這些被刪除的事件卡)")
    else:
        print(f"\n🏆 恭喜！167 張卡片全數完美翻譯完畢！")
    print("="*50)

if __name__ == "__main__":
    clean_and_update_split_files()