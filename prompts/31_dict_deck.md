# 模組 4-B：牌組檢索與看牌
DICT_DECK = """
【🧰 牌組檢索積木 (DICT_DECK)】
1. 檢索與拿取 (look_at_deck):
   - `{"type": "look_at_deck", "look_amount": 數字, "take_amount": 數字, "reveal": true/false, "filters": {過濾器}, "take_action": "add_to_hand"|"play"|"discard", "remainder": "bottom_deck_any_order"|"top_deck_any_order"|"top_or_bottom_deck_any_order"|"bottom_deck_fixed"|"top_deck_fixed"|"outside", "on_success": [動作積木]}`
   - 💡 參數說明：
     - `remainder`: 
         - `"bottom_deck_any_order"`: 剩餘卡片以任意順序放回牌庫底。
         - `"top_deck_any_order"`: 剩餘卡片以任意順序放回牌庫頂。
         - `"top_or_bottom_deck_any_order"`: 剩餘卡片以任意順序，由玩家選擇放置到牌庫上面或下面。
     - `on_success`: 若有「若加入手牌，則捨棄1張」等後續動作，請放在此處。

2. 查看並排序 (look_and_arrange):
   - `{"type": "look_and_arrange", "amount": 數字, "destination": "top_deck_any_order"|"bottom_deck_any_order"|"top_or_bottom_deck_any_order"}`
   - 💡 應用：處理「從自己牌庫上面查看 X 張卡，然後任意放置到牌庫上面或下面」(無拿取卡片動作時專用)。
"""