import logging
import time
import json
import os
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

class BonusSystem:
    def __init__(self, user_db, cards_db, rarity_settings):
        self.user_db = user_db
        self.cards_db = cards_db
        self.rarity_settings = rarity_settings
        self.bonus_data = self.load_bonus_data()
        logging.info("🔄 Bonus system initialization")

    def load_bonus_data(self):
        """Loads bonus data"""
        try:
            if os.path.exists("bonus_data.json"):
                with open("bonus_data.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"Error loading bonus_data.json: {e}")
            return {}

    def save_bonus_data(self):
        """Saves bonus data"""
        try:
            with open("bonus_data.json", "w", encoding="utf-8") as f:
                json.dump(self.bonus_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving bonus_data.json: {e}")

    def get_total_cards_count(self, user_id: int):
        """Returns total number of cards received"""
        user_data = self.user_db[user_id]
        total_cards = sum(len(cards) for cards in user_data["cards"].values())
        # Add duplicates for accurate count
        duplicates = sum(user_data.get("duplicates", {}).values())
        return total_cards + duplicates

    def get_card_milestones(self):
        """Returns milestones for bonuses"""
        return [
            {"required": 10, "cards_reward": 5, "shards_reward": 5, "claimed": False},
            {"required": 50, "cards_reward": 10, "shards_reward": 10, "claimed": False},
            {"required": 100, "cards_reward": 15, "shards_reward": 20, "claimed": False},
            {"required": 350, "cards_reward": 20, "shards_reward": 50, "claimed": False},
            {"required": 500, "cards_reward": 50, "shards_reward": 100, "claimed": False},
            {"required": 1000, "cards_reward": 100, "shards_reward": 200, "claimed": False}
        ]

    def get_user_milestones(self, user_id: int):
        """Returns milestones with user progress"""
        total_cards = self.get_total_cards_count(user_id)
        user_bonus_data = self.bonus_data.get(str(user_id), {})
        milestones = self.get_card_milestones()

        user_milestones = []
        for milestone in milestones:
            milestone_id = f"milestone_{milestone['required']}"
            claimed = user_bonus_data.get(milestone_id, False)
            completed = total_cards >= milestone["required"]

            user_milestones.append({
                "required": milestone["required"],
                "cards_reward": milestone["cards_reward"],
                "shards_reward": milestone["shards_reward"],
                "current": total_cards,
                "completed": completed,
                "claimed": claimed
            })

        return user_milestones

    async def show_bonuses_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Shows bonus menu for attempts"""
        query = update.callback_query
        await query.answer()

        user_data = self.user_db[user_id]
        username = user_data.get("username", "Player")
        milestones = self.get_user_milestones(user_id)

        text = f"🎁 {username}, bonuses for card count\n\n"
        text += "💡 Get rewards for total number of cards received:\n\n"

        for milestone in milestones:
            status = "✅" if milestone["claimed"] else "🎁" if milestone["completed"] else "⏳"

            if milestone["claimed"]:
                progress_text = f"✅ {milestone['required']} cards - CLAIMED"
            elif milestone["completed"]:
                progress_text = f"🎁 {milestone['required']} cards - READY TO CLAIM"
            else:
                progress_text = f"⏳ {milestone['current']}/{milestone['required']} cards"

            reward_text = f"🎴 {milestone['cards_reward']} attempts"
            if milestone["shards_reward"] > 0:
                reward_text += f" + 🀄️ {milestone['shards_reward']} shards"

            text += f"{progress_text}\n{reward_text}\n➖➖➖➖➖➖\n"

        # Add current progress information
        total_cards = self.get_total_cards_count(user_id)
        text += f"\n📊 Total cards received: {total_cards}"

        # Show current balances
        text += f"\n🎴 Current attempts: {user_data.get('cards_today', 0)}"
        text += f"\n🀄️ Current shards: {user_data.get('shards', 0)}"

        buttons = [
            [InlineKeyboardButton("🎁 Claim Available Rewards", callback_data="claim_available_bonuses")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="bonuses")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    async def claim_available_bonuses(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Gives all available bonuses"""
        query = update.callback_query
        await query.answer()

        user_data = self.user_db[user_id]
        milestones = self.get_user_milestones(user_id)
        user_id_str = str(user_id)

        if user_id_str not in self.bonus_data:
            self.bonus_data[user_id_str] = {}

        total_cards_reward = 0
        total_shards_reward = 0
        claimed_milestones = 0

        for milestone in milestones:
            if milestone["completed"] and not milestone["claimed"]:
                total_cards_reward += milestone["cards_reward"]
                total_shards_reward += milestone["shards_reward"]
                claimed_milestones += 1

                # Mark milestone as claimed
                milestone_id = f"milestone_{milestone['required']}"
                self.bonus_data[user_id_str][milestone_id] = True

        if claimed_milestones == 0:
            await query.answer("❌ No available rewards to claim!", show_alert=True)
            return

        # ✅ FIXED: Give rewards to CORRECT fields
        # Attempts go to cards_today (this is what user sees as "attempts")
        user_data["cards_today"] = user_data.get("cards_today", 0) + total_cards_reward
        # Shards go to shards
        user_data["shards"] = user_data.get("shards", 0) + total_shards_reward

        self.save_bonus_data()

        text = (
            f"🎉 Rewards claimed!\n\n"
            f"📦 Received for {claimed_milestones} achievements:\n"
            f"• 🎴 {total_cards_reward} additional attempts\n"
            f"• 🀄️ {total_shards_reward} shards\n\n"
            f"✅ Rewards added to your account!\n\n"
            f"📊 Now you have:\n"
            f"• 🎴 {user_data['cards_today']} attempts\n"
            f"• 🀄️ {user_data['shards']} shards"
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Check Again", callback_data="bonuses")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
            ])
        )

    def update_card_count(self, user_id: int):
        """Updates card counter (called when receiving new card)"""
        # This function will be called from bot.py when getting a card
        # Can add additional logic if needed
        pass

    async def give_bonus_card(self, user_id: int, rarity: str = None):
        """Gives bonus card (ignores cooldown)"""
        user_data = self.user_db[user_id]

        if not rarity:
            valid_rarities = [r for r, s in self.rarity_settings.items() if s["chance"] > 0 and r != "Ultimate"]
            weights = [self.rarity_settings[r]["chance"] for r in valid_rarities]
            rarity = random.choices(valid_rarities, weights=weights, k=1)[0]

        card = random.choice(self.cards_db[rarity])

        # ✅ IGNORE COOLDOWN FOR BONUSES
        is_new = card["name"] not in user_data["cards"][rarity]

        if is_new:
            user_data["cards"][rarity].add(card["name"])
        else:
            # Add duplicates but don't show user
            user_data["duplicates"][rarity] = user_data["duplicates"].get(rarity, 0) + 1
            shards_per_duplicate = {"Common": 1, "Rare": 2, "Epic": 3, "Legend": 5, "Mythic": 10}
            user_data["shards"] = user_data.get("shards", 0) + shards_per_duplicate.get(rarity, 1)

        card_sp = card.get("value", 0)
        user_data["total_sp"] += card_sp

        money_range = self.get_money_range(rarity)
        card_money = random.randint(money_range["min"], money_range["max"])
        user_data["money"] += card_money

        return card, is_new

    def get_money_range(self, rarity: str):
        """Returns money range for rarity"""
        money_ranges = {
            "Common": {"min": 50, "max": 125},
            "Rare": {"min": 175, "max": 500},
            "Epic": {"min": 500, "max": 5000},
            "Legend": {"min": 6000, "max": 100000},
            "Mythic": {"min": 200000, "max": 500000},
            "Ultimate": {"min": 0, "max": 0}
        }
        return money_ranges.get(rarity, {"min": 50, "max": 125})

    async def claim_daily_bonus(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Gives daily bonus with card (ignores cooldown)"""
        query = update.callback_query
        await query.answer()

        user_data = self.user_db[user_id]
        bonus_available, _, _ = self.get_bonus_status(user_id)

        if not bonus_available:
            await query.answer("⏳ Bonus not available yet!", show_alert=True)
            return

        # Give bonus
        user_data["total_sp"] += 1000
        user_data["last_bonus_time"] = time.time()

        # ✅ FIXED: Use new function to give card without cooldown
        card, is_new = self.give_bonus_card(user_id)

        # Show result
        text = (
            f"🎉 Daily bonus received!\n\n"
            f"🎁 You received:\n"
            f"• 1,000 SP\n"
            f"• 1 random card\n\n"
            f"📦 Card: {self.rarity_settings[card['rarity']]['emoji']} {card['name']}\n"
            f"⭐ Rarity: {card['rarity']}\n"
            f"💎 Value: {card.get('value', 0):,} SP\n\n"
            f"✅ Bonus saved!\n"
            f"⏰ Next one in 24 hours"
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="bonuses")]
            ])
        )

    async def give_promo_code_reward(self, user_id: int, reward_type: str = "card"):
        """Gives promo code reward (ignores cooldown)"""
        user_data = self.user_db[user_id]

        if reward_type == "card":
            # ✅ IGNORE COOLDOWN: give card without checking
            card, is_new = self.give_bonus_card(user_id)
            return {
                "type": "card",
                "card": card,
                "is_new": is_new,
                "sp": card.get("value", 0),
                "money": random.randint(100, 500)
            }
        elif reward_type == "shards":
            shards = random.randint(10, 50)
            user_data["shards"] = user_data.get("shards", 0) + shards
            return {
                "type": "shards",
                "shards": shards
            }
        elif reward_type == "attempts":
            attempts = random.randint(5, 20)
            user_data["cards_today"] = user_data.get("cards_today", 0) + attempts
            return {
                "type": "attempts",
                "attempts": attempts
            }

    def get_bonus_status(self, user_id: int):
        """Daily bonus status"""
        user_data = self.user_db[user_id]
        current_time = time.time()
        last_bonus_time = user_data.get("last_bonus_time", 0)
        bonus_cooldown = 24 * 60 * 60  # 24 hours

        time_since_last_bonus = current_time - last_bonus_time
        bonus_available = time_since_last_bonus >= bonus_cooldown

        if bonus_available:
            bonus_status = "✅ Available"
            time_remaining = "Now!"
        else:
            hours_remaining = int((bonus_cooldown - time_since_last_bonus) // 3600)
            minutes_remaining = int(((bonus_cooldown - time_since_last_bonus) % 3600) // 60)
            bonus_status = f"⏳ In {hours_remaining}h {minutes_remaining}m"
            time_remaining = f"{hours_remaining}h {minutes_remaining}m"

        return bonus_available, bonus_status, time_remaining
