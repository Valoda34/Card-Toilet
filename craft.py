import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from collections import defaultdict

# Additional logging setup for craft system
craft_logger = logging.getLogger('craft_system')
craft_logger.setLevel(logging.DEBUG)

class CraftSystem:
    def __init__(self, user_db, cards_db):
        self.user_db = user_db
        self.cards_db = cards_db
        craft_logger.info("🎯 CraftSystem.__init__ called")
        craft_logger.info(f"📊 user_db type: {type(user_db)}, cards_db type: {type(cards_db)}")
        craft_logger.info("✅ Craft system initialized")

    async def show_craft_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Shows craft menu"""
        craft_logger.info(f"🎯🎯🎯 show_craft_menu CALLED for user_id: {user_id}")
        print(f"🚨🚨🚨 SHOW_CRAFT_MENU CALLED FOR USER: {user_id}")

        try:
            craft_logger.info("🔄 Getting callback_query...")
            query = update.callback_query
            craft_logger.info(f"📞 callback_query received: {type(query)}")
            craft_logger.info("🔄 Calling query.answer()...")
            await query.answer()
            craft_logger.info("✅ query.answer() executed")

            # Get user data
            craft_logger.info(f"🔍 Getting user_data for user_id: {user_id}")
            user_data = self.user_db.get(user_id)
            craft_logger.info(f"📊 user_data: {user_data is not None}")

            if not user_data:
                craft_logger.error(f"❌ User data not found for {user_id}")
                craft_logger.info("🔄 Trying to create error message...")
                await query.edit_message_text("❌ Error: user data not found")
                craft_logger.info("✅ Error message sent")
                return

            # Initialize duplicates if not exists
            if "duplicates" not in user_data:
                craft_logger.info("🆕 Initializing duplicates for user")
                user_data["duplicates"] = {
                    "Common": 0, "Rare": 0, "Epic": 0, "Legend": 0, "Mythic": 0
                }

            # Initialize shards if not exists
            if "shards" not in user_data:
                craft_logger.info("🆕 Initializing shards for user")
                user_data["shards"] = 0

            # Initialize cards_today if not exists
            if "cards_today" not in user_data:
                craft_logger.info("🆕 Initializing cards_today for user")
                user_data["cards_today"] = 0

            username = user_data.get("username", "Player")
            duplicates = user_data.get("duplicates", {})
            shards = user_data.get("shards", 0)
            cards_today = user_data.get("cards_today", 0)

            craft_logger.info(f"📊 User data: username={username}, duplicates={duplicates}, shards={shards}, cards_today={cards_today}")

            # Format text
            craft_logger.info("🔄 Formatting menu text...")
            text = f"🍙 {username}, you can craft additional attempts from duplicates and shards.\n\n"
            text += "🌀 Your duplicates and shards\n"

            # Rarity list for display
            rarities = [
                ("Common", "⚡️", "Common"),
                ("Rare", "✨", "Rare"),
                ("Epic", "🐉", "Epic"),
                ("Legend", "🎲", "Legendary"),
                ("Mythic", "💎", "Mythic")
            ]

            # Add rarities in ASCII format
            for i, (rarity, emoji, name) in enumerate(rarities):
                count = duplicates.get(rarity, 0)
                if i == 0:
                    text += f"┏{emoji} {name} - {count}\n"
                elif i == len(rarities) - 1:
                    text += f"┣{emoji} {name} - {count}\n"
                    text += f"┗🀄️ Shards - {shards}\n"
                else:
                    text += f"┣{emoji} {name} - {count}\n"

            text += f"\n🎴 Available attempts: {cards_today}\n\n"
            text += "🍡 Craft costs\n"
            text += "╔10 ⚡️ cards ➠ 1 additional attempt\n"
            text += "╠10 ✨ cards ➠ 2 additional attempts\n"
            text += "╠10 🐉 cards ➠ 4 additional attempts\n"
            text += "╠10 🎲 cards ➠ 8 additional attempts\n"
            text += "╠10 💎 cards ➠ 16 additional attempts\n"
            text += "╚10 🀄️ shards ➠ 1 additional attempt\n\n"
            text += "💡 Additional attempts can be used immediately via '🎴 Get Card' button!\n"
            text += "🛢️ To craft from all materials at once, type command 'Craft all'"

            craft_logger.info("✅ Menu text formatted")

            # Create buttons
            craft_logger.info("🔄 Creating craft buttons...")
            buttons = []

            # Check which rarities can be crafted
            craftable_rarities = []
            for rarity, emoji, name in rarities:
                count = duplicates.get(rarity, 0)
                craft_logger.info(f"🔍 Checking {rarity}: {count} duplicates")
                if count >= 10:
                    craftable_rarities.append((rarity, emoji, name))
                    craft_logger.info(f"✅ Craft available for {rarity}")

            # Add buttons for available crafts
            for rarity, emoji, name in craftable_rarities:
                callback_data = f"craft_{rarity.lower()}"
                craft_logger.info(f"➕ Adding button: {callback_data}")
                buttons.append([InlineKeyboardButton(f"Craft from {emoji}", callback_data=callback_data)])

            # Button for shards if available
            if shards >= 10:
                craft_logger.info("✅ Adding button for shards")
                buttons.append([InlineKeyboardButton("Craft from 🀄️", callback_data="craft_shards")])

            # If no available crafts
            if not buttons:
                craft_logger.info("❌ No available crafts")
                buttons.append([InlineKeyboardButton("❌ Not enough materials", callback_data="none")])

            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")])

            craft_logger.info(f"📋 Created {len(buttons)} button rows")
            craft_logger.info(f"🔘 Total buttons: {sum(len(row) for row in buttons)}")

            # Create keyboard
            craft_logger.info("🔄 Creating InlineKeyboardMarkup...")
            keyboard = InlineKeyboardMarkup(buttons)
            craft_logger.info("✅ Keyboard created")

            craft_logger.info(f"📤 Sending menu with {len(buttons)} buttons")
            craft_logger.info(f"📝 Text length: {len(text)}")

            craft_logger.info("🔄 Calling query.edit_message_text...")
            await query.edit_message_text(
                text,
                reply_markup=keyboard
            )

            craft_logger.info("✅ Craft menu successfully sent")
            print(f"🎉🎉🎉 SHOW_CRAFT_MENU SUCCESSFULLY EXECUTED FOR USER: {user_id}")

        except Exception as e:
            craft_logger.error(f"❌ Critical error in show_craft_menu: {e}", exc_info=True)
            print(f"💥💥💥 ERROR IN SHOW_CRAFT_MENU: {e}")
            try:
                craft_logger.info("🔄 Trying to send alert...")
                await query.answer("❌ Error loading craft menu", show_alert=True)
                craft_logger.info("✅ Alert sent")
            except Exception as alert_error:
                craft_logger.error(f"❌ Error sending alert: {alert_error}")

    async def craft_from_duplicates(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, rarity: str):
        """Craft from duplicates - adds attempts to cards_today"""
        craft_logger.info(f"🎯 craft_from_duplicates called: user_id={user_id}, rarity={rarity}")
        print(f"🔨 CRAFT_FROM_DUPLICATES CALLED: user_id={user_id}, rarity={rarity}")

        try:
            query = update.callback_query
            craft_logger.info("✅ callback_query received")

            await query.answer()
            craft_logger.info("✅ query.answer() executed")

            user_data = self.user_db.get(user_id)
            if not user_data:
                craft_logger.error(f"❌ User data not found for {user_id}")
                await query.answer("❌ Error: user data not found", show_alert=True)
                return

            # Initialize duplicates if not exists
            if "duplicates" not in user_data:
                user_data["duplicates"] = {
                    "Common": 0, "Rare": 0, "Epic": 0, "Legend": 0, "Mythic": 0
                }

            # Initialize cards_today if not exists
            if "cards_today" not in user_data:
                user_data["cards_today"] = 0

            duplicates = user_data.get("duplicates", {})

            # Craft settings
            craft_settings = {
                "common": {"required": 10, "attempts": 1, "emoji": "⚡️", "name": "Common", "key": "Common"},
                "rare": {"required": 10, "attempts": 2, "emoji": "✨", "name": "Rare", "key": "Rare"},
                "epic": {"required": 10, "attempts": 4, "emoji": "🐉", "name": "Epic", "key": "Epic"},
                "legend": {"required": 10, "attempts": 8, "emoji": "🎲", "name": "Legendary", "key": "Legend"},
                "mythic": {"required": 10, "attempts": 16, "emoji": "💎", "name": "Mythic", "key": "Mythic"}
            }

            setting = craft_settings.get(rarity.lower())
            if not setting:
                craft_logger.error(f"❌ Unknown rarity: {rarity}")
                await query.answer("❌ Unknown rarity", show_alert=True)
                return

            # Get duplicates count
            rarity_key = setting["key"]
            current_duplicates = duplicates.get(rarity_key, 0)
            craft_logger.info(f"📊 {rarity_key} duplicates: {current_duplicates}")

            if current_duplicates < setting["required"]:
                error_msg = f"❌ Not enough {setting['name']} duplicates! Need {setting['required']}, you have {current_duplicates}"
                craft_logger.warning(error_msg)
                await query.answer(error_msg, show_alert=True)
                return

            # Execute craft - ADD ATTEMPTS TO cards_today
            user_data["duplicates"][rarity_key] = current_duplicates - setting["required"]
            user_data["cards_today"] = user_data.get("cards_today", 0) + setting["attempts"]
            craft_logger.info(f"✅ Craft completed: used {setting['required']} {setting['emoji']}, received {setting['attempts']} additional attempts")

            text = (
                f"🎉 Successful craft!\n\n"
                f"📦 Used: {setting['required']} {setting['emoji']} {setting['name']} duplicates\n"
                f"🎁 Received: {setting['attempts']} additional attempts\n\n"
                f"🌀 Remaining {setting['name']} duplicates: {user_data['duplicates'][rarity_key]}\n\n"
                f"🎴 Total available attempts: {user_data['cards_today']}\n\n"
                f"💡 Use the '🎴 Get Card' button!"
            )

            buttons = [
                [InlineKeyboardButton("🔄 Craft more", callback_data=f"craft_{rarity.lower()}")],
                [InlineKeyboardButton("📋 To craft menu", callback_data="craft_menu")],
                [InlineKeyboardButton("🎴 Get Card", callback_data="none")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
            ]

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )

            craft_logger.info("✅ Craft message successfully sent")

        except Exception as e:
            craft_logger.error(f"❌ Error in craft_from_duplicates: {e}", exc_info=True)
            try:
                await query.answer("❌ Error during craft", show_alert=True)
            except Exception as alert_error:
                craft_logger.error(f"❌ Error sending alert: {alert_error}")

    async def craft_from_shards(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Craft from shards - adds attempts to cards_today"""
        craft_logger.info(f"🎯 craft_from_shards called: user_id={user_id}")
        print(f"🔨 CRAFT_FROM_SHARDS CALLED: user_id={user_id}")

        try:
            query = update.callback_query
            craft_logger.info("✅ callback_query received")

            await query.answer()
            craft_logger.info("✅ query.answer() executed")

            user_data = self.user_db.get(user_id)
            if not user_data:
                craft_logger.error(f"❌ User data not found for {user_id}")
                await query.answer("❌ Error: user data not found", show_alert=True)
                return

            # Initialize shards if not exists
            if "shards" not in user_data:
                user_data["shards"] = 0

            # Initialize cards_today if not exists
            if "cards_today" not in user_data:
                user_data["cards_today"] = 0

            shards = user_data.get("shards", 0)
            required_shards = 10
            attempts_given = 1

            craft_logger.info(f"📊 Shards: {shards}, required: {required_shards}")

            if shards < required_shards:
                error_msg = f"❌ Not enough shards! Need {required_shards}, you have {shards}"
                craft_logger.warning(error_msg)
                await query.answer(error_msg, show_alert=True)
                return

            # Execute craft - ADD ATTEMPTS TO cards_today
            user_data["shards"] = shards - required_shards
            user_data["cards_today"] = user_data.get("cards_today", 0) + attempts_given
            craft_logger.info(f"✅ Craft from shards completed: used {required_shards}, received {attempts_given} additional attempts")

            text = (
                f"🎉 Successful craft!\n\n"
                f"📦 Used: {required_shards} 🀄️ shards\n"
                f"🎁 Received: {attempts_given} additional attempt\n\n"
                f"🌀 Remaining shards: {user_data['shards']}\n\n"
                f"🎴 Total available attempts: {user_data['cards_today']}\n\n"
                f"💡 Use the '🎴 Get Card' button!"
            )

            buttons = [
                [InlineKeyboardButton("🔄 Craft more", callback_data="craft_shards")],
                [InlineKeyboardButton("📋 To craft menu", callback_data="craft_menu")],
                [InlineKeyboardButton("🎴 Get Card", callback_data="none")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
            ]

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )

            craft_logger.info("✅ Shard craft message successfully sent")

        except Exception as e:
            craft_logger.error(f"❌ Error in craft_from_shards: {e}", exc_info=True)
            try:
                await query.answer("❌ Error during craft", show_alert=True)
            except Exception as alert_error:
                craft_logger.error(f"❌ Error sending alert: {alert_error}")
