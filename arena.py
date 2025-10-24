import random
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

class ArenaSystem:
    def __init__(self, user_db, cards_db, rarity_settings):
        self.user_db = user_db
        self.cards_db = cards_db
        self.rarity_settings = rarity_settings
        logging.info("🔄 Arena system initialization")

    def get_card_data(self, card_name):
        """Gets card data by name"""
        for rarity, cards in self.cards_db.items():
            for card in cards:
                if card["name"] == card_name:
                    return card
        return None

    def update_arena_team(self, user_data, slot_index, card_name):
        """Updates user's arena team"""
        if "arena_team" not in user_data:
            user_data["arena_team"] = [""] * 5

        while len(user_data["arena_team"]) < 5:
            user_data["arena_team"].append("")

        if 0 <= slot_index < 5:
            user_data["arena_team"][slot_index] = card_name
            return True
        return False

    def get_real_player_team(self, exclude_user_id):
        """Finds a real player for battle"""
        available_players = []

        for user_id, user_data in self.user_db.items():
            if user_id == exclude_user_id:
                continue

            user_team = user_data.get("arena_team", [])
            if len(user_team) == 5 and all(user_team):
                team_cards_data = []
                valid_team = True

                for card_name in user_team:
                    card_data = self.get_card_data(card_name)
                    if card_data:
                        team_cards_data.append({
                            "name": card_name,
                            "attack": card_data.get('attack', 0),
                            "health": card_data.get('health', 0)
                        })
                    else:
                        valid_team = False
                        break

                if valid_team and team_cards_data:
                    available_players.append({
                        "user_id": user_id,
                        "username": user_data.get("username", f"Player {user_id}"),
                        "team": team_cards_data,
                        "cups": user_data.get("arena_cups", 0)
                    })

        if available_players:
            return random.choice(available_players)

        return self.generate_bot_team()

    def generate_bot_team(self):
        """Generates bot team"""
        bot_team = []
        all_cards = []

        for rarity in ["Common", "Rare", "Epic", "Legend", "Mythic", "Ultimate"]:
            if rarity in self.cards_db:
                all_cards.extend(self.cards_db[rarity])

        if len(all_cards) >= 5:
            team_cards = random.sample(all_cards, 5)
        else:
            team_cards = all_cards * 2
            team_cards = team_cards[:5]

        for card in team_cards:
            bot_team.append({
                "name": card["name"],
                "attack": card.get("attack", 0),
                "health": card.get("health", 0)
            })

        return {
            "user_id": 0,
            "username": "Bot Opponent",
            "team": bot_team,
            "cups": random.randint(0, 1000),
            "is_bot": True
        }

    async def show_arena_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """Shows arena menu"""
        query = update.callback_query
        await query.answer()

        user_team = user_data.get("arena_team", [])

        total_attack = 0
        total_health = 0

        team_text = "⚔️ Arena\n\nYour team:\n"
        for i, card_name in enumerate(user_team):
            if card_name:
                card_data = self.get_card_data(card_name)
                if card_data:
                    attack = card_data.get('attack', 0)
                    health = card_data.get('health', 0)
                    team_text += f"{i+1}. {card_name} - ⚔{attack:,} ❤{health:,}\n"
                    total_attack += attack
                    total_health += health
            else:
                team_text += f"{i+1}. ❌ Empty slot\n"

        team_text += f"\n🏆 Cups: {user_data.get('arena_cups', 0)}\n"
        team_text += f"📊 Wins/Losses: {user_data.get('battles_won', 0)}/{user_data.get('battles_lost', 0)}\n"
        team_text += f"⚔️ Total team damage: {total_attack:,}\n"
        team_text += f"❤️ Total team health: {total_health:,}\n"

        buttons = [
            [InlineKeyboardButton("🗂 My Team", callback_data="arena_team")],
            [InlineKeyboardButton("🔍 Find Opponent", callback_data="arena_find")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
        ]

        await query.edit_message_text(
            team_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    async def show_arena_team(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """Shows user's arena team"""
        query = update.callback_query
        await query.answer()

        if "arena_team" not in user_data:
            user_data["arena_team"] = [""] * 5
        elif len(user_data["arena_team"]) < 5:
            user_data["arena_team"].extend([""] * (5 - len(user_data["arena_team"])))

        user_team = user_data["arena_team"]

        total_attack = 0
        total_health = 0

        team_text = "🗂 Your Arena Team:\n\n"
        for i, card_name in enumerate(user_team):
            if card_name:
                card_data = self.get_card_data(card_name)
                if card_data:
                    attack = card_data.get('attack', 0)
                    health = card_data.get('health', 0)
                    team_text += f"{i+1}. {card_name} - ⚔{attack:,} ❤{health:,}\n"
                    total_attack += attack
                    total_health += health
            else:
                team_text += f"{i+1}. ❌ Empty slot\n"

        team_text += f"\n📊 Total statistics:\n"
        team_text += f"⚔️ Total damage: {total_attack:,}\n"
        team_text += f"❤️ Total health: {total_health:,}\n"

        buttons = []
        for i in range(5):
            slot_status = "✅" if user_team[i] else "❌"
            buttons.append([InlineKeyboardButton(
                f"{slot_status} Slot {i+1}",
                callback_data=f"team_slot_{i}"
            )])

        buttons.extend([
            [InlineKeyboardButton("🔍 Find Opponent", callback_data="arena_find")],
            [InlineKeyboardButton("🔙 Back", callback_data="arena")]
        ])

        await query.edit_message_text(
            team_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    async def show_team_slot(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """Shows rarity selection for team slot"""
        query = update.callback_query
        await query.answer()

        data = query.data
        slot_index = int(data.split("_")[2])

        buttons = []
        for rarity in ["Common", "Rare", "Epic", "Legend", "Mythic", "Ultimate"]:
            card_count = len(user_data["cards"][rarity])
            if card_count > 0:
                buttons.append([InlineKeyboardButton(
                    f"{self.rarity_settings[rarity]['emoji']} {rarity} - {card_count} cards",
                    callback_data=f"choose_rarity_{slot_index}_{rarity}"
                )])

        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="arena_team")])

        await query.edit_message_text(
            f"Choose rarity for slot {slot_index + 1}:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    async def show_cards_by_rarity(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """Shows cards of specific rarity for selection"""
        query = update.callback_query
        await query.answer()

        data = query.data
        parts = data.split("_")
        slot_index = int(parts[2])
        rarity = "_".join(parts[3:])

        user_cards = list(user_data["cards"][rarity])

        if not user_cards:
            await query.answer(f"❌ You don't have {rarity} rarity cards", show_alert=True)
            return

        buttons = []
        for card_name in user_cards:
            card_data = self.get_card_data(card_name)
            if card_data:
                button_text = f"{card_name} (⚔{card_data.get('attack', 0):,} ❤{card_data.get('health', 0):,})"
            else:
                button_text = card_name

            buttons.append([InlineKeyboardButton(
                button_text,
                callback_data=f"select_card_{slot_index}_{card_name}"
            )])

        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"team_slot_{slot_index}")])

        await query.edit_message_text(
            f"Choose {rarity} rarity card for slot {slot_index + 1}:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    async def find_arena_enemy(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """Finds real opponent for arena"""
        query = update.callback_query
        await query.answer()

        user_team = user_data.get("arena_team", [])

        if len(user_team) != 5 or not all(user_team):
            await query.edit_message_text(
                "❌ Your team is incomplete! Fill all 5 slots.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to team", callback_data="arena_team")]
                ])
            )
            return

        enemy_data = self.get_real_player_team(update.effective_user.id)

        enemy_total_attack = sum(card['attack'] for card in enemy_data["team"])
        enemy_total_health = sum(card['health'] for card in enemy_data["team"])

        context.user_data["enemy_data"] = enemy_data

        enemy_type = "🤖 Bot" if enemy_data.get("is_bot") else "👤 Player"
        enemy_team_text = f"{enemy_type}: {enemy_data['username']}\n"
        enemy_team_text += f"🏆 Cups: {enemy_data['cups']}\n\n"
        enemy_team_text += "Opponent's team:\n"

        for i, card in enumerate(enemy_data["team"], 1):
            enemy_team_text += f"{i}. {card['name']} - ⚔{card['attack']:,} ❤{card['health']:,}\n"

        enemy_team_text += f"\n📊 Opponent statistics:\n"
        enemy_team_text += f"⚔️ Total damage: {enemy_total_attack:,}\n"
        enemy_team_text += f"❤️ Total health: {enemy_total_health:,}\n"

        await query.edit_message_text(
            f"🎯 Opponent found!\n\n{enemy_team_text}\n"
            "Ready for battle?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ Start Battle", callback_data="battle_attack")],
                [InlineKeyboardButton("🔙 Back", callback_data="arena_team")]
            ])
        )

    # ================== NEW BATTLE METHODS ==================

    async def process_battle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """Processes arena battle"""
        query = update.callback_query
        await query.answer()

        user_team = user_data.get("arena_team", [])
        enemy_data = context.user_data.get("enemy_data", {})

        if not enemy_data:
            enemy_data = self.generate_bot_team()

        user_cards_data = []
        for card_name in user_team:
            card_data = self.get_card_data(card_name)
            if card_data:
                user_cards_data.append({
                    "name": card_name,
                    "attack": card_data.get("attack", 0),
                    "health": card_data.get("health", 0),
                    "max_health": card_data.get("health", 0)
                })

        context.user_data["battle_data"] = {
            "user_cards": user_cards_data,
            "enemy_cards": enemy_data["team"],
            "current_round": 0,
            "user_wins": 0,
            "enemy_wins": 0
        }

        await self.show_round(update, context, user_data)

    async def show_round(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """Shows current battle round"""
        query = update.callback_query
        battle_data = context.user_data["battle_data"]
        current_round = battle_data["current_round"]

        if current_round >= 5 or current_round >= len(battle_data["user_cards"]) or current_round >= len(battle_data["enemy_cards"]):
            await self.show_battle_result(update, context, user_data)
            return

        user_card = battle_data["user_cards"][current_round]
        enemy_card = battle_data["enemy_cards"][current_round]

        user_card["health"] = user_card["max_health"]
        enemy_card["health"] = enemy_card.get("max_health", enemy_card["health"])

        round_text = f"🌀 ROUND {current_round + 1}:\n"
        round_text += f"⚔️ {user_card['name']} vs {enemy_card['name']}\n\n"
        round_text += f"🎯 {user_card['name']}: ⚔{user_card['attack']:,} ❤{user_card['health']:,}\n"
        round_text += f"🎯 {enemy_card['name']}: ⚔{enemy_card['attack']:,} ❤{enemy_card['health']:,}\n\n"
        round_text += "Ready for battle?"

        context.user_data["current_round_data"] = {
            "user_card": user_card.copy(),
            "enemy_card": enemy_card.copy(),
            "round_log": [],
            "round_finished": False
        }

        buttons = [
            [InlineKeyboardButton("⚔️ Start Round", callback_data="start_round")],
            [InlineKeyboardButton("🔙 Cancel Battle", callback_data="arena")]
        ]

        if query:
            await query.edit_message_text(round_text, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await update.message.reply_text(round_text, reply_markup=InlineKeyboardMarkup(buttons))

    async def process_round(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """Processes one round step"""
        query = update.callback_query
        await query.answer()

        battle_data = context.user_data["battle_data"]
        round_data = context.user_data["current_round_data"]
        current_round = battle_data["current_round"]

        user_card = round_data["user_card"]
        enemy_card = round_data["enemy_card"]

        if round_data["round_finished"]:
            battle_data["current_round"] += 1
            await self.show_round(update, context, user_data)
            return

        round_log = round_data["round_log"]

        if not round_log:
            round_log.append(f"🌀 ROUND {current_round + 1}:\n")
            round_log.append(f"⚔️ {user_card['name']} vs {enemy_card['name']}\n\n")

        old_enemy_health = enemy_card['health']
        enemy_card['health'] -= user_card['attack']
        enemy_card['health'] = max(0, enemy_card['health'])

        attack_text = f"🎯 {user_card['name']} attacks! "
        attack_text += f"{enemy_card['name']}: ❤{old_enemy_health:,} → {enemy_card['health']:,}\n"
        round_log.append(attack_text)

        if enemy_card['health'] <= 0:
            round_log.append(f"💀 {enemy_card['name']} defeated!\n\n")
            battle_data["user_wins"] += 1
            round_data["round_finished"] = True
        else:
            old_user_health = user_card['health']
            user_card['health'] -= enemy_card['attack']
            user_card['health'] = max(0, user_card['health'])

            attack_text = f"🎯 {enemy_card['name']} attacks! "
            attack_text += f"{user_card['name']}: ❤{old_user_health:,} → {user_card['health']:,}\n\n"
            round_log.append(attack_text)

            if user_card['health'] <= 0:
                round_log.append(f"💀 {user_card['name']} defeated!\n\n")
                battle_data["enemy_wins"] += 1
                round_data["round_finished"] = True

        round_text = "".join(round_log)

        if not round_data["round_finished"]:
            round_text += f"Current status:\n"
            round_text += f"• {user_card['name']}: ❤{user_card['health']:,}\n"
            round_text += f"• {enemy_card['name']}: ❤{enemy_card['health']:,}\n\n"
            round_text += "Continue battle?"

        buttons = []
        if not round_data["round_finished"]:
            buttons.append([InlineKeyboardButton("⚔️ Continue Battle", callback_data="continue_round")])
        else:
            if current_round < 4:
                buttons.append([InlineKeyboardButton("➡️ Next Round", callback_data="continue_round")])
            else:
                buttons.append([InlineKeyboardButton("🏁 Finish Battle", callback_data="finish_battle")])

        buttons.append([InlineKeyboardButton("🔙 Cancel Battle", callback_data="arena")])

        await query.edit_message_text(round_text, reply_markup=InlineKeyboardMarkup(buttons))

    async def show_battle_result(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """Shows battle result"""
        query = update.callback_query
        battle_data = context.user_data["battle_data"]

        user_wins = battle_data["user_wins"]
        enemy_wins = battle_data["enemy_wins"]

        result_text = "🏁 BATTLE RESULT:\n\n"
        result_text += f"Your wins: {user_wins}\n"
        result_text += f"Opponent wins: {enemy_wins}\n\n"

        if user_wins > enemy_wins:
            result_text += "🎉 VICTORY! Your team won!\n"
            user_data["battles_won"] = user_data.get("battles_won", 0) + 1
            cups_earned = random.randint(1, 20)
            user_data["arena_cups"] = user_data.get("arena_cups", 0) + cups_earned
            result_text += f"🏆 Cups earned: +{cups_earned}\n"
        elif enemy_wins > user_wins:
            result_text += "💀 DEFEAT! Opponent's team won.\n"
            user_data["battles_lost"] = user_data.get("battles_lost", 0) + 1
            cups_lost = random.randint(1, 10)
            user_data["arena_cups"] = max(0, user_data.get("arena_cups", 0) - cups_lost)
            result_text += f"🏆 Cups lost: -{cups_lost}\n"
        else:
            result_text += "🤝 DRAW! Both teams performed well.\n"

        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Battle Again", callback_data="arena_find")],
                [InlineKeyboardButton("🔙 To Arena", callback_data="arena")]
            ])
        )
