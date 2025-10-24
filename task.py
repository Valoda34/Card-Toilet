import logging
import time
import json
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

class TaskSystem:
    def __init__(self, user_db):
        self.user_db = user_db
        self.quests_data = self.load_quests_data()
        logging.info("🔄 Task system initialization")

    def load_quests_data(self):
        """Loads quests data"""
        try:
            if os.path.exists("quests_data.json"):
                with open("quests_data.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"Error loading quests_data.json: {e}")
            return {}

    def save_quests_data(self):
        """Saves quests data"""
        try:
            with open("quests_data.json", "w", encoding="utf-8") as f:
                json.dump(self.quests_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving quests_data.json: {e}")

    def get_daily_quests(self, user_id: int):
        """Returns list of daily quests"""
        user_data = self.user_db[user_id]
        user_quests = self.quests_data.get(str(user_id), {})

        daily_quests = [
            {
                "id": "get_cards",
                "type": "daily",
                "name": "🎴 Get 3 cards",
                "progress": f"{min(user_data.get('cards_today', 0), 3)}/3",
                "required": 3,
                "current": min(user_data.get('cards_today', 0), 3),
                "reward_sp": 500,
                "reward_money": 100,
                "completed": user_data.get('cards_today', 0) >= 3,
                "claimed": user_quests.get("daily_get_cards", False)
            },
            {
                "id": "win_battle",
                "type": "daily",
                "name": "⚔️ Win a battle",
                "progress": f"{user_data.get('battles_won', 0)}/1",
                "required": 1,
                "current": user_data.get('battles_won', 0),
                "reward_sp": 1000,
                "reward_money": 200,
                "completed": user_data.get('battles_won', 0) >= 1,
                "claimed": user_quests.get("daily_win_battle", False)
            },
            {
                "id": "invite_friend",
                "type": "daily",
                "name": "👥 Invite a friend",
                "progress": f"{len(user_quests.get('referrals_today', []))}/1",
                "required": 1,
                "current": len(user_quests.get('referrals_today', [])),
                "reward_sp": 2000,
                "reward_money": 500,
                "completed": len(user_quests.get('referrals_today', [])) >= 1,
                "claimed": user_quests.get("daily_invite_friend", False)
            },
            {
                "id": "collect_epic",
                "type": "daily",
                "name": "🐉 Collect Epic card",
                "progress": f"{len(user_data['cards'].get('Epic', []))}/1",
                "required": 1,
                "current": len(user_data['cards'].get('Epic', [])),
                "reward_sp": 1500,
                "reward_money": 300,
                "completed": len(user_data['cards'].get('Epic', [])) >= 1,
                "claimed": user_quests.get("daily_collect_epic", False)
            }
        ]

        return daily_quests

    def get_weekly_quests(self, user_id: int):
        """Returns list of weekly quests"""
        user_data = self.user_db[user_id]
        user_quests = self.quests_data.get(str(user_id), {})

        weekly_quests = [
            {
                "id": "get_50_cards",
                "type": "weekly",
                "name": "🎴 Get 50 cards",
                "progress": f"{user_quests.get('weekly_cards', 0)}/50",
                "required": 50,
                "current": user_quests.get('weekly_cards', 0),
                "reward_sp": 5000,
                "reward_money": 1000,
                "completed": user_quests.get('weekly_cards', 0) >= 50,
                "claimed": user_quests.get("weekly_get_50_cards", False)
            },
            {
                "id": "win_10_battles",
                "type": "weekly",
                "name": "⚔️ Win 10 battles",
                "progress": f"{user_data.get('battles_won', 0)}/10",
                "required": 10,
                "current": user_data.get('battles_won', 0),
                "reward_sp": 8000,
                "reward_money": 1500,
                "completed": user_data.get('battles_won', 0) >= 10,
                "claimed": user_quests.get("weekly_win_10_battles", False)
            },
            {
                "id": "collect_legend",
                "type": "weekly",
                "name": "🎲 Collect Legend card",
                "progress": f"{len(user_data['cards'].get('Legend', []))}/1",
                "required": 1,
                "current": len(user_data['cards'].get('Legend', [])),
                "reward_sp": 10000,
                "reward_money": 2000,
                "completed": len(user_data['cards'].get('Legend', [])) >= 1,
                "claimed": user_quests.get("weekly_collect_legend", False)
            },
            {
                "id": "craft_attempts",
                "type": "weekly",
                "name": "🛢️ Craft 5 attempts",
                "progress": f"{user_quests.get('weekly_craft_attempts', 0)}/5",
                "required": 5,
                "current": user_quests.get('weekly_craft_attempts', 0),
                "reward_sp": 3000,
                "reward_money": 500,
                "completed": user_quests.get('weekly_craft_attempts', 0) >= 5,
                "claimed": user_quests.get("weekly_craft_attempts", False)
            }
        ]

        return weekly_quests

    def get_achievements(self, user_id: int):
        """Returns list of achievements"""
        user_data = self.user_db[user_id]
        user_quests = self.quests_data.get(str(user_id), {})

        achievements = [
            {
                "id": "first_card",
                "type": "achievement",
                "name": "🌟 First card",
                "description": "Get your first card",
                "progress": f"{min(len(user_data['cards'].get('Common', [])), 1)}/1",
                "required": 1,
                "current": min(len(user_data['cards'].get('Common', [])), 1),
                "reward_sp": 1000,
                "reward_money": 200,
                "completed": len(user_data['cards'].get('Common', [])) >= 1,
                "claimed": user_quests.get("achievement_first_card", False)
            },
            {
                "id": "card_collector",
                "type": "achievement",
                "name": "📚 Collector",
                "description": "Collect 10 different cards",
                "progress": f"{sum(len(cards) for cards in user_data['cards'].values())}/10",
                "required": 10,
                "current": sum(len(cards) for cards in user_data['cards'].values()),
                "reward_sp": 5000,
                "reward_money": 1000,
                "completed": sum(len(cards) for cards in user_data['cards'].values()) >= 10,
                "claimed": user_quests.get("achievement_card_collector", False)
            },
            {
                "id": "arena_champion",
                "type": "achievement",
                "name": "🏆 Arena Champion",
                "description": "Win 25 arena battles",
                "progress": f"{user_data.get('battles_won', 0)}/25",
                "required": 25,
                "current": user_data.get('battles_won', 0),
                "reward_sp": 15000,
                "reward_money": 3000,
                "completed": user_data.get('battles_won', 0) >= 25,
                "claimed": user_quests.get("achievement_arena_champion", False)
            },
            {
                "id": "rich_player",
                "type": "achievement",
                "name": "💰 Rich Player",
                "description": "Save 100,000 money",
                "progress": f"{user_data.get('money', 0)}/100000",
                "required": 100000,
                "current": user_data.get('money', 0),
                "reward_sp": 20000,
                "reward_money": 5000,
                "completed": user_data.get('money', 0) >= 100000,
                "claimed": user_quests.get("achievement_rich_player", False)
            }
        ]

        return achievements

    def update_quest_progress(self, user_id: int, quest_type: str, amount: int = 1):
        """Updates quest progress"""
        user_id_str = str(user_id)
        if user_id_str not in self.quests_data:
            self.quests_data[user_id_str] = {}

        if quest_type == "daily_cards":
            self.quests_data[user_id_str]["daily_cards"] = self.quests_data[user_id_str].get("daily_cards", 0) + amount
        elif quest_type == "weekly_cards":
            self.quests_data[user_id_str]["weekly_cards"] = self.quests_data[user_id_str].get("weekly_cards", 0) + amount
        elif quest_type == "craft_attempts":
            self.quests_data[user_id_str]["weekly_craft_attempts"] = self.quests_data[user_id_str].get("weekly_craft_attempts", 0) + amount

        self.save_quests_data()

    async def show_quests_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Shows main quests menu"""
        query = update.callback_query
        await query.answer()

        user_data = self.user_db[user_id]
        username = user_data.get("username", "Player")

        daily_quests = self.get_daily_quests(user_id)
        completed_daily = sum(1 for q in daily_quests if q["completed"])

        text = (
            f"📋 {username}, quest system\n\n"
            f"📊 Today's progress:\n"
            f"• 🎯 Daily: {completed_daily}/{len(daily_quests)}\n"
            f"• ⏳ Weekly: in progress\n"
            f"• 🏆 Achievements: available\n\n"
            f"💎 Choose quest type:"
        )

        buttons = [
            [InlineKeyboardButton("🎯 Daily Quests", callback_data="quests_daily")],
            [InlineKeyboardButton("📅 Weekly Quests", callback_data="quests_weekly")],
            [InlineKeyboardButton("🏆 Achievements", callback_data="quests_achievements")],
            [InlineKeyboardButton("🎁 Claim All Rewards", callback_data="claim_all_quests")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    async def show_daily_quests(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Shows daily quests"""
        query = update.callback_query
        await query.answer()

        user_data = self.user_db[user_id]
        username = user_data.get("username", "Player")
        quests = self.get_daily_quests(user_id)

        completed_count = sum(1 for quest in quests if quest["completed"])
        total_quests = len(quests)

        text = f"🎯 {username}, daily quests\n\n"
        text += f"📊 Progress: {completed_count}/{total_quests} completed\n\n"

        for quest in quests:
            status = "✅" if quest["claimed"] else "🎁" if quest["completed"] else "⏳"
            text += f"{status} {quest['name']} - {quest['progress']}\n"
            text += f"💎 Reward: {quest['reward_sp']} SP + {quest['reward_money']} 💰\n\n"

        text += "🕒 Quests reset daily at 00:00!"

        buttons = [
            [InlineKeyboardButton("🎁 Claim Completed", callback_data="claim_daily_quests")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="quests_daily")],
            [InlineKeyboardButton("📋 To Quests Menu", callback_data="quests")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    async def show_weekly_quests(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Shows weekly quests"""
        query = update.callback_query
        await query.answer()

        user_data = self.user_db[user_id]
        username = user_data.get("username", "Player")
        quests = self.get_weekly_quests(user_id)

        completed_count = sum(1 for quest in quests if quest["completed"])
        total_quests = len(quests)

        text = f"📅 {username}, weekly quests\n\n"
        text += f"📊 Progress: {completed_count}/{total_quests} completed\n\n"

        for quest in quests:
            status = "✅" if quest["claimed"] else "🎁" if quest["completed"] else "⏳"
            text += f"{status} {quest['name']} - {quest['progress']}\n"
            text += f"💎 Reward: {quest['reward_sp']} SP + {quest['reward_money']} 💰\n\n"

        text += "🕒 Quests reset every week!"

        buttons = [
            [InlineKeyboardButton("🎁 Claim Completed", callback_data="claim_weekly_quests")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="quests_weekly")],
            [InlineKeyboardButton("📋 To Quests Menu", callback_data="quests")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    async def show_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Shows achievements"""
        query = update.callback_query
        await query.answer()

        user_data = self.user_db[user_id]
        username = user_data.get("username", "Player")
        achievements = self.get_achievements(user_id)

        completed_count = sum(1 for achievement in achievements if achievement["completed"])
        total_achievements = len(achievements)

        text = f"🏆 {username}, achievements\n\n"
        text += f"📊 Progress: {completed_count}/{total_achievements} obtained\n\n"

        for achievement in achievements:
            status = "✅" if achievement["claimed"] else "🎁" if achievement["completed"] else "⏳"
            text += f"{status} {achievement['name']}\n"
            text += f"📝 {achievement['description']}\n"
            text += f"📊 {achievement['progress']}\n"
            text += f"💎 Reward: {achievement['reward_sp']} SP + {achievement['reward_money']} 💰\n\n"

        buttons = [
            [InlineKeyboardButton("🎁 Claim Completed", callback_data="claim_achievements")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="quests_achievements")],
            [InlineKeyboardButton("📋 To Quests Menu", callback_data="quests")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    async def claim_quest_rewards(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, quest_type: str):
        """Gives quest rewards"""
        query = update.callback_query
        await query.answer()

        user_data = self.user_db[user_id]
        user_id_str = str(user_id)

        if quest_type == "daily":
            quests = self.get_daily_quests(user_id)
        elif quest_type == "weekly":
            quests = self.get_weekly_quests(user_id)
        else:  # achievements
            quests = self.get_achievements(user_id)

        total_reward_sp = 0
        total_reward_money = 0
        total_reward_attempts = 0  # ADDED: for attempts
        total_reward_shards = 0    # ADDED: for shards
        claimed_quests = 0

        for quest in quests:
            if quest["completed"] and not quest["claimed"]:
                total_reward_sp += quest["reward_sp"]
                total_reward_money += quest["reward_money"]

                # ADDED: Give attempts and shards for quests
                if quest_type == "daily":
                    total_reward_attempts += 1  # +1 attempt for each daily quest
                    total_reward_shards += 5    # +5 shards for each daily quest
                elif quest_type == "weekly":
                    total_reward_attempts += 3  # +3 attempts for each weekly quest
                    total_reward_shards += 15   # +15 shards for each weekly quest
                else:  # achievements
                    total_reward_attempts += 5  # +5 attempts for each achievement
                    total_reward_shards += 25   # +25 shards for each achievement

                claimed_quests += 1

                # Mark quest as completed
                if user_id_str not in self.quests_data:
                    self.quests_data[user_id_str] = {}
                self.quests_data[user_id_str][f"{quest_type}_{quest['id']}"] = True

        if claimed_quests == 0:
            await query.answer("❌ No completed quests to claim rewards!", show_alert=True)
            return

        # Give rewards
        user_data["total_sp"] += total_reward_sp
        user_data["money"] += total_reward_money
        user_data["cards_today"] += total_reward_attempts  # ADDED: give attempts
        user_data["shards"] += total_reward_shards         # ADDED: give shards

        self.save_quests_data()

        quest_type_name = {
            "daily": "daily quests",
            "weekly": "weekly quests",
            "achievements": "achievements"
        }

        text = (
            f"🎉 Rewards claimed!\n\n"
            f"📦 Received for {claimed_quests} {quest_type_name[quest_type]}:\n"
            f"• 💎 {total_reward_sp:,} SP\n"
            f"• 💰 {total_reward_money:,} money\n"
            f"• 🎴 +{total_reward_attempts} attempts\n"      # ADDED
            f"• 🀄️ +{total_reward_shards} shards\n\n"        # ADDED
            f"✅ Rewards added to your account!"
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 To Quests Menu", callback_data="quests")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
            ])
        )

    async def claim_all_rewards(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Gives all available rewards"""
        query = update.callback_query
        await query.answer()

        user_data = self.user_db[user_id]
        user_id_str = str(user_id)

        all_quests = (
            self.get_daily_quests(user_id) +
            self.get_weekly_quests(user_id) +
            self.get_achievements(user_id)
        )

        total_reward_sp = 0
        total_reward_money = 0
        total_reward_attempts = 0  # ADDED
        total_reward_shards = 0    # ADDED
        claimed_quests = 0

        for quest in all_quests:
            if quest["completed"] and not quest["claimed"]:
                total_reward_sp += quest["reward_sp"]
                total_reward_money += quest["reward_money"]

                # ADDED: Give attempts and shards depending on quest type
                if quest["type"] == "daily":
                    total_reward_attempts += 1
                    total_reward_shards += 5
                elif quest["type"] == "weekly":
                    total_reward_attempts += 3
                    total_reward_shards += 15
                else:  # achievements
                    total_reward_attempts += 5
                    total_reward_shards += 25

                claimed_quests += 1

                # Mark quest as completed
                if user_id_str not in self.quests_data:
                    self.quests_data[user_id_str] = {}
                self.quests_data[user_id_str][f"{quest['type']}_{quest['id']}"] = True

        if claimed_quests == 0:
            await query.answer("❌ No completed quests to claim rewards!", show_alert=True)
            return

        # Give rewards
        user_data["total_sp"] += total_reward_sp
        user_data["money"] += total_reward_money
        user_data["cards_today"] += total_reward_attempts  # ADDED
        user_data["shards"] += total_reward_shards         # ADDED

        self.save_quests_data()

        text = (
            f"🎉 All rewards claimed!\n\n"
            f"📦 Received for {claimed_quests} quests:\n"
            f"• 💎 {total_reward_sp:,} SP\n"
            f"• 💰 {total_reward_money:,} money\n"
            f"• 🎴 +{total_reward_attempts} attempts\n"      # ADDED
            f"• 🀄️ +{total_reward_shards} shards\n\n"        # ADDED
            f"✅ Rewards added to your account!"
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 To Quests Menu", callback_data="quests")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
            ])
        )
