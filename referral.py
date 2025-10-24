import logging
import json
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

class ReferralSystem:
    def __init__(self, user_db):
        self.user_db = user_db
        self.referral_data = self.load_referral_data()
        self.bot_username = None
        logging.info("🔄 Referral system initialization")

    def set_bot_username(self, username):
        """Sets bot username"""
        self.bot_username = username
        logging.info(f"✅ Bot username set: {username}")

    def load_referral_data(self):
        """Loads referral data from file"""
        try:
            if os.path.exists("referral_data.json"):
                with open("referral_data.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"Error loading referral_data.json: {e}")
            return {}

    def save_referral_data(self):
        """Saves referral data to file"""
        try:
            with open("referral_data.json", "w", encoding="utf-8") as f:
                json.dump(self.referral_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving referral_data.json: {e}")

    def generate_referral_link(self, user_id: int):
        """Generates referral link"""
        if not self.bot_username:
            logging.warning("❌ bot_username not set when generating link")
            return "⚠️ Link temporarily unavailable"

        link = f"https://t.me/{self.bot_username}?start=ref_{user_id}"
        logging.info(f"✅ Generated referral link for {user_id}: {link}")
        return link

    def get_user_referrals(self, user_id: int):
        """Returns user's referral list"""
        user_id_str = str(user_id)
        if user_id_str not in self.referral_data:
            return []
        return self.referral_data[user_id_str].get("referrals", [])

    def get_user_referrer(self, user_id: int):
        """Returns user's referrer ID"""
        user_id_str = str(user_id)
        if user_id_str not in self.referral_data:
            return None
        return self.referral_data[user_id_str].get("referrer")

    def add_referral(self, referrer_id: int, referral_id: int):
        """Adds referral"""
        try:
            referrer_id_str = str(referrer_id)
            referral_id_str = str(referral_id)

            # Check that user is not inviting themselves
            if referrer_id == referral_id:
                logging.warning(f"❌ User {referrer_id} trying to invite themselves")
                return False, 0, 0, 0

            # Initialize referrer data if not exists
            if referrer_id_str not in self.referral_data:
                self.referral_data[referrer_id_str] = {
                    "referrals": [],
                    "total_earned_sp": 0,
                    "total_earned_money": 0,
                    "total_attempts": 0
                }

            # Check if this user was already invited
            if referral_id_str in self.referral_data[referrer_id_str]["referrals"]:
                logging.warning(f"❌ User {referral_id} already invited by user {referrer_id}")
                return False, 0, 0, 0

            # Add referral
            self.referral_data[referrer_id_str]["referrals"].append(referral_id_str)

            # Give reward to referrer
            referrals_count = len(self.referral_data[referrer_id_str]["referrals"])

            # Reward for 1 invitation
            reward_sp = 10000
            reward_money = 10000
            reward_attempts = 1

            # Additional reward for 10 invitations
            if referrals_count >= 10:
                reward_sp += 100000
                reward_money += 100000
                reward_attempts += 10

            # Give rewards to referrer
            if referrer_id in self.user_db:
                self.user_db[referrer_id]["total_sp"] += reward_sp
                self.user_db[referrer_id]["money"] += reward_money
                self.user_db[referrer_id]["craft_attempts"] = self.user_db[referrer_id].get("craft_attempts", 0) + reward_attempts

                # Update referrer statistics
                self.referral_data[referrer_id_str]["total_earned_sp"] += reward_sp
                self.referral_data[referrer_id_str]["total_earned_money"] += reward_money
                self.referral_data[referrer_id_str]["total_attempts"] += reward_attempts

            # Reward for new user
            if referral_id in self.user_db:
                self.user_db[referral_id]["total_sp"] += 5000
                self.user_db[referral_id]["money"] += 5000

            # Save referral data
            if referral_id_str not in self.referral_data:
                self.referral_data[referral_id_str] = {
                    "referrer": referrer_id_str,
                    "joined_via_ref": True
                }
            else:
                self.referral_data[referral_id_str]["referrer"] = referrer_id_str
                self.referral_data[referral_id_str]["joined_via_ref"] = True

            self.save_referral_data()

            logging.info(f"✅ Successfully added referral: {referral_id} -> {referrer_id}")
            logging.info(f"🎁 Rewards: {reward_sp} SP, {reward_money} money, {reward_attempts} attempts")

            return True, reward_sp, reward_money, reward_attempts

        except Exception as e:
            logging.error(f"❌ Error adding referral: {e}")
            return False, 0, 0, 0

    def get_referral_stats(self, user_id: int):
        """Returns referral statistics"""
        user_id_str = str(user_id)

        referrals = self.get_user_referrals(user_id)
        user_data = self.referral_data.get(user_id_str, {})

        total_earned_sp = user_data.get("total_earned_sp", 0)
        total_earned_money = user_data.get("total_earned_money", 0)
        total_attempts = user_data.get("total_attempts", 0)

        return {
            "total_referrals": len(referrals),
            "total_earned_sp": total_earned_sp,
            "total_earned_money": total_earned_money,
            "total_attempts": total_attempts,
            "referrals": referrals
        }

    async def show_referral_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Shows referral menu"""
        query = update.callback_query
        await query.answer()

        user_data = self.user_db[user_id]
        username = user_data.get("username", "Player")
        stats = self.get_referral_stats(user_id)

        # Generate link
        referral_link = self.generate_referral_link(user_id)

        logging.info(f"📊 Showing referral menu for {user_id}, bot_username: {self.bot_username}")

        text = (
            f"👤 {username}, referral system\n\n"
            f"📊 Statistics:\n"
            f"• Friends invited: {stats['total_referrals']}\n"
            f"• SP earned: {stats['total_earned_sp']:,} 💎\n"
            f"• Money earned: {stats['total_earned_money']:,} 💰\n"
            f"• Attempts received: {stats['total_attempts']} 🎴\n\n"
            f"🎁 **Invitation rewards:**\n"
            f"• For 1 friend: 10,000 SP 💎 + 10,000 💰 + 1 attempt 🎴\n"
            f"• For 10 friends: 100,000 SP 💎 + 100,000 💰 + 10 attempts 🎴\n\n"
            f"👥 Friends also get bonus: 5,000 SP 💎 + 5,000 💰\n\n"
            f"📎 Your referral link:\n"
            f"`{referral_link}`"
        )

        buttons = [
            [InlineKeyboardButton("👥 My Referrals", callback_data="referral_list")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="referral")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
        ]

        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"❌ Error showing referral menu: {e}")
            await query.answer("❌ Error loading menu", show_alert=True)

    async def show_referral_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Shows referral list"""
        query = update.callback_query
        await query.answer()

        stats = self.get_referral_stats(user_id)
        referrals = stats["referrals"]

        if not referrals:
            text = "📝 You don't have any invited friends yet.\n\nShare your link to invite friends!"
        else:
            text = f"👥 Your invited friends ({len(referrals)}):\n\n"

            for i, ref_id in enumerate(referrals, 1):
                ref_user_id = int(ref_id)
                if ref_user_id in self.user_db:
                    ref_username = self.user_db[ref_user_id].get("username", f"Player {ref_id}")
                    if len(ref_username) > 20:
                        ref_username = ref_username[:17] + "..."
                    text += f"{i}. {ref_username}\n"
                else:
                    text += f"{i}. Player {ref_id}\n"

            # Show achievements
            if len(referrals) >= 10:
                text += f"\n🎉 Achievement: 10+ friends! Received bonus rewards! 🎁"

        buttons = [
            [InlineKeyboardButton("📤 Invite Friends", callback_data="referral")],
            [InlineKeyboardButton("🔙 Back", callback_data="referral")]
        ]

        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            logging.error(f"❌ Error showing referral list: {e}")
            await query.answer("❌ Error loading list", show_alert=True)

    async def process_referral_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Processes referral start"""
        try:
            message_text = update.message.text
            if message_text and "start" in message_text and "ref_" in message_text:
                # Extract referrer ID from command
                parts = message_text.split()
                if len(parts) > 1 and "ref_" in parts[1]:
                    referrer_id = int(parts[1].replace("ref_", ""))

                    # Check that user is not inviting themselves
                    if referrer_id != user_id:
                        success, reward_sp, reward_money, reward_attempts = self.add_referral(referrer_id, user_id)

                        if success:
                            # Notify referrer
                            try:
                                if referrer_id in self.user_db:
                                    referrer_username = self.user_db[referrer_id].get("username", "Player")
                                    referrals_count = len(self.get_user_referrals(referrer_id))

                                    reward_text = f"🎁 You received: {reward_sp:,} SP 💎 + {reward_money:,} 💰 + {reward_attempts} attempts 🎴"

                                    if referrals_count >= 10:
                                        reward_text += "\n\n🎉 Reached 10 friends! Received bonus rewards! 🎁"

                                    await context.bot.send_message(
                                        chat_id=referrer_id,
                                        text=(
                                            f"🎉 New referral!\n\n"
                                            f"👤 {self.user_db[user_id].get('username', 'New player')} joined via your link!\n"
                                            f"{reward_text}"
                                        )
                                    )
                            except Exception as e:
                                logging.error(f"❌ Failed to notify referrer: {e}")

                            # Welcome new user
                            await update.message.reply_text(
                                f"🎉 You joined via referral link!\n"
                                f"💎 Received bonus: 5,000 SP + 5,000 💰",
                                reply_markup=self.get_main_keyboard()
                            )

                            logging.info(f"✅ Processed referral start: {user_id} -> {referrer_id}")
        except Exception as e:
            logging.error(f"❌ Error processing referral start: {e}")

    def get_main_keyboard(self):
        """Returns main keyboard"""
        from telegram import ReplyKeyboardMarkup, KeyboardButton
        return ReplyKeyboardMarkup([
            [KeyboardButton("🎴 Get Card")],
            [KeyboardButton("📋 Menu"), KeyboardButton("🗂 My Cards")]
        ], resize_keyboard=True)
