# 模組 4-B：牌組檢索與看牌
DICT_DECK = """
【🧰 牌組檢索積木 (DICT_DECK)】
- `{"type": "look_at_deck", "look_amount": 數字, "take_amount": 數字, "reveal": true/false, "filters": {過濾器}, "take_action": "add_to_hand"|"play"|"discard", "remainder": "bottom_deck_any_order"|"top_deck_any_order"|"bottom_deck_fixed"|"top_deck_fixed"|"outside", "on_success": [動作積木]}`
  - 💡 參數說明：
    - `remainder`: 
        - `"bottom_deck_any_order"`: 剩餘卡片以任意順序放回牌庫底。
        - `"top_deck_any_order"`: 剩餘卡片以任意順序放回牌庫頂。
    - `on_success`: 若有「若加入手牌，則捨棄1張」等後續動作，請放在此處。
"""