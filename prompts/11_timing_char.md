# 模組 2-B：角色與場地卡專用時機
TIMING_RULES_CHAR_FIELD = """
【⚠️ 時機判定規則：角色/場地卡 (Character/Field Card)】
當類型為角色或場地時，請根據文本關鍵字使用以下時機：
1. `on_play`: 包含「登場時」。
2. `main_act`: 包含「主起動」。
3. `on_leave`: 包含「退場時」。
4. `on_attack`: 包含「攻擊時」。
5. `on_block`: 包含「阻擋時」。
6. `continuous`: 包含「常駐」、「自己回合中」、「對手回合中」。
7. `on_attack_end` / `on_main_phase_end`: 包含「攻擊結束時」或「主階段結束時」。
8. `on_battle_win`: 包含「進行攻擊並戰鬥勝利時」或「戰鬥勝利時」。(💡 此時機點也可作為 gain_effect 的 gained_trigger 參數)
"""