import os
import random
import logging
import json
import atexit
import aiohttp
import time
import asyncio
import importlib
import re
from collections import defaultdict
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputMediaPhoto,
    InputMediaAnimation,
    CallbackQuery
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ================== CONFIGURATION ==================
TOKEN = "8170272465:AAFmTpane2uj3C0sJ0gB7r3y4MCOy9DBz0g"

# Arena settings
ARENA_COOLDOWN = 1 * 60 * 60  # 1 hour in seconds
ARENA_BATTLES_PER_DAY = 10    # Maximum battles per day

RARITY_SETTINGS = {
    "Common": {"chance": 50, "emoji": "⚡️", "rarity_emoji": "⚪", "color": "#FFFFFF"},
    "Rare": {"chance": 25, "emoji": "✨", "rarity_emoji": "🔵", "color": "#0000FF"},
    "Epic": {"chance": 15, "emoji": "🐉", "rarity_emoji": "🟣", "color": "#800080"},
    "Legend": {"chance": 5, "emoji": "🎲", "rarity_emoji": "🟡", "color": "#FFFF00"},
    "Mythic": {"chance": 1, "emoji": "💎", "rarity_emoji": "🔴", "color": "#FF0000"},
    "Ultimate": {"chance": 0, "emoji": "👑", "rarity_emoji": "🅱️", "color": "#FFD700"}
}

# Money settings for rarities
MONEY_RANGES = {
    "Common": {"min": 50, "max": 125},
    "Rare": {"min": 175, "max": 500},
    "Epic": {"min": 500, "max": 5000},
    "Legend": {"min": 6000, "max": 100000},
    "Mythic": {"min": 200000, "max": 500000},
    "Ultimate": {"min": 0, "max": 0}
}

# Cooldown in seconds (2 hours) and cards before cooldown
COOLDOWN_TIME = 2 * 60 * 60  # 2 hours
CARDS_BEFORE_COOLDOWN = 3     # 3 cards before cooldown activation

# ================== DATA ==================
def load_data():
    global CARDS_DB, COMBINE_DATA

    if not os.path.exists("cards.json"):
        with open("cards.json", "w", encoding="utf-8") as f:
            json.dump({rarity: [] for rarity in RARITY_SETTINGS}, f, ensure_ascii=False)

    try:
        with open("cards.json", "r", encoding="utf-8") as f:
            CARDS_DB = json.load(f)
    except Exception as e:
        CARDS_DB = defaultdict(list)
        logging.error(f"Error loading cards.json: {str(e)}")

    if not os.path.exists("in_menu.json"):
        with open("in_menu.json", "w", encoding="utf-8") as f:
            json.dump({"combine_cards": []}, f, ensure_ascii=False)

    try:
        with open("in_menu.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            COMBINE_DATA = data.get("combine_cards", [])
    except Exception as e:
        COMBINE_DATA = []
        logging.error(f"Error loading in_menu.json: {str(e)}")

    CARDS_DB.setdefault("Ultimate", [])
    existing_names = {c["name"].lower() for c in CARDS_DB["Ultimate"]}

    for recipe in COMBINE_DATA:
        if isinstance(recipe, dict) and "name" in recipe:
            if recipe["name"].lower() not in existing_names:
                CARDS_DB["Ultimate"].append({
                    "name": recipe["name"],
                    "attack": recipe.get("attack", 0),
                    "health": recipe.get("health", 0),
                    "value": recipe.get("value", 0),
                    "photo": recipe.get("preview", ""),
                    "animation": recipe.get("result_animation", ""),
                    "desc": recipe.get("desc", "")
                })

    # ДЕБАГ: Проверяем загрузку Ultimate карт
    logging.info(f"🃏 Loaded Ultimate cards: {len(CARDS_DB.get('Ultimate', []))}")
    for card in CARDS_DB.get('Ultimate', []):
        logging.info(f"   📝 {card['name']} - Animation: {card.get('animation', 'NO')}")
    
    logging.info(f"🔮 Loaded combine recipes: {len(COMBINE_DATA)}")
    for recipe in COMBINE_DATA:
        if isinstance(recipe, dict):
            logging.info(f"   🧬 {recipe.get('name', 'UNNAMED')} - Preview: {recipe.get('preview', 'NO')}")

load_data()

# ================== DATABASE ==================
user_db = defaultdict(lambda: {
    "cards": defaultdict(set),
    "total_sp": 0,
    "money": 0,
    "username": "",
    "last_card_time": 0,
    "cards_today": 0,
    "arena_team": [],
    "arena_cups": 0,
    "battles_won": 0,
    "battles_lost": 0,
    "last_bonus_time": 0,
    "completed_quests": [],
    "duplicates": {
        "Common": 0, "Rare": 0, "Epic": 0, "Legend": 0, "Mythic": 0
    },
    "shards": 0,
    "craft_attempts": 0,
    # NEW FIELDS FOR ARENA AND PROMO CODES
    "last_arena_battle": 0,
    "arena_battles_today": 0,
    "last_arena_reset": time.time(),
    "used_promo_codes": set()
})

def save_user_data():
    try:
        data = {
            str(user_id): {
                "cards": {rarity: list(cards) for rarity, cards in user_data["cards"].items()},
                "total_sp": user_data["total_sp"],
                "money": user_data["money"],
                "username": user_data["username"],
                "last_card_time": user_data["last_card_time"],
                "cards_today": user_data["cards_today"],
                "arena_team": user_data.get("arena_team", []),
                "arena_cups": user_data.get("arena_cups", 0),
                "battles_won": user_data.get("battles_won", 0),
                "battles_lost": user_data.get("battles_lost", 0),
                "last_bonus_time": user_data.get("last_bonus_time", 0),
                "completed_quests": user_data.get("completed_quests", []),
                "duplicates": user_data.get("duplicates", {
                    "Common": 0, "Rare": 0, "Epic": 0, "Legend": 0, "Mythic": 0
                }),
                "shards": user_data.get("shards", 0),
                "craft_attempts": user_data.get("craft_attempts", 0),
                # New fields
                "last_arena_battle": user_data.get("last_arena_battle", 0),
                "arena_battles_today": user_data.get("arena_battles_today", 0),
                "last_arena_reset": user_data.get("last_arena_reset", time.time()),
                "used_promo_codes": list(user_data.get("used_promo_codes", set()))
            }
            for user_id, user_data in user_db.items()
        }
        with open("users_data.json", "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving data: {str(e)}")

def load_user_data():
    try:
        if os.path.exists("users_data.json"):
            with open("users_data.json", "r") as f:
                data = json.load(f)
                for user_id_str, user_data in data.items():
                    user_id = int(user_id_str)
                    
                    # Check and initialize new fields
                    if "last_arena_battle" not in user_data:
                        user_data["last_arena_battle"] = 0
                    if "arena_battles_today" not in user_data:
                        user_data["arena_battles_today"] = 0
                    if "last_arena_reset" not in user_data:
                        user_data["last_arena_reset"] = time.time()
                    if "used_promo_codes" not in user_data:
                        user_data["used_promo_codes"] = []
                    
                    user_db[user_id] = {
                        "cards": defaultdict(set, {k: set(v) for k, v in user_data.get("cards", {}).items()}),
                        "total_sp": user_data.get("total_sp", 0),
                        "money": user_data.get("money", 0),
                        "username": user_data.get("username", ""),
                        "last_card_time": user_data.get("last_card_time", 0),
                        "cards_today": user_data.get("cards_today", 0),
                        "arena_team": user_data.get("arena_team", []),
                        "arena_cups": user_data.get("arena_cups", 0),
                        "battles_won": user_data.get("battles_won", 0),
                        "battles_lost": user_data.get("battles_lost", 0),
                        "last_bonus_time": user_data.get("last_bonus_time", 0),
                        "completed_quests": user_data.get("completed_quests", []),
                        "duplicates": user_data.get("duplicates", {
                            "Common": 0, "Rare": 0, "Epic": 0, "Legend": 0, "Mythic": 0
                        }),
                        "shards": user_data.get("shards", 0),
                        "craft_attempts": user_data.get("craft_attempts", 0),
                        # New fields
                        "last_arena_battle": user_data.get("last_arena_battle", 0),
                        "arena_battles_today": user_data.get("arena_battles_today", 0),
                        "last_arena_reset": user_data.get("last_arena_reset", time.time()),
                        "used_promo_codes": set(user_data.get("used_promo_codes", []))
                    }
    except Exception as e:
        logging.error(f"Error loading user data: {str(e)}")

load_user_data()
atexit.register(save_user_data)

# ================== ONEDRIVE SUPPORT ==================
class OneDriveHelper:
    @staticmethod
    def is_onedrive_link(url: str) -> bool:
        """Проверяет, является ли ссылка OneDrive"""
        onedrive_patterns = [
            '1drv.ms',
            'onedrive.live.com',
            'sharepoint.com'
        ]
        
        # Исключаем другие популярные хостинги
        exclude_patterns = [
            'postimg.cc',
            'i.postimg.cc',
            'imgur.com',
            'i.imgur.com',
            'telegra.ph',
            'cdn.telegram.org'
        ]
        
        url_lower = url.lower()
        
        # Если URL содержит исключаемые паттерны - это не OneDrive!
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False
            
        return any(pattern in url_lower for pattern in onedrive_patterns)
    
    @staticmethod
    def convert_onedrive_link(shared_url: str) -> str:
        """Конвертирует OneDrive shared ссылку в прямую ссылку для скачивания"""
        try:
            # Если это уже прямая ссылка
            if 'download.aspx' in shared_url or 'download?' in shared_url:
                return shared_url
            
            # Обработка стандартных OneDrive shared ссылок
            if '1drv.ms' in shared_url:
                # Конвертируем 1drv.ms в прямую ссылку
                share_id = shared_url.split('!')[-1] if '!' in shared_url else shared_url.split('/')[-1]
                return f"https://api.onedrive.com/v1.0/shares/{share_id}/root/content"
            
            # Для других форматов OneDrive
            elif 'onedrive.live.com' in shared_url:
                if 'redir?' in shared_url:
                    # Извлекаем ID ресурса
                    match = re.search(r'resid=([^&]+)', shared_url)
                    if match:
                        resid = match.group(1)
                        return f"https://api.onedrive.com/v1.0/drives/{resid}/root/content"
                
            return shared_url
            
        except Exception as e:
            logging.error(f"OneDrive link conversion error: {e}")
            return shared_url

# ================== PROMO CODE SYSTEM ==================
class PromoCodeSystem:
    def __init__(self, user_db):
        self.user_db = user_db
        self.promo_codes_file = "promo_codes.json"
        self.load_promo_codes()
    
    def load_promo_codes(self):
        """Loads promo codes from file"""
        if not os.path.exists(self.promo_codes_file):
            self.promo_codes = {}
            self.save_promo_codes()
            return
        
        try:
            with open(self.promo_codes_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.promo_codes = data
        except Exception as e:
            logging.error(f"Error loading promo codes: {e}")
            self.promo_codes = {}
    
    def save_promo_codes(self):
        """Saves promo codes to file"""
        try:
            with open(self.promo_codes_file, "w", encoding="utf-8") as f:
                json.dump(self.promo_codes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving promo codes: {e}")
    
    def create_promo_code(self, code: str, rewards: dict, 
                         max_uses: int = None, 
                         expires_in_hours: int = None,
                         is_active: bool = True):
        """Creates a new promo code"""
        expires_at = None
        if expires_in_hours:
            expires_at = time.time() + (expires_in_hours * 3600)
        
        self.promo_codes[code.upper()] = {
            "rewards": rewards,
            "max_uses": max_uses,
            "uses_count": 0,
            "expires_at": expires_at,
            "is_active": is_active,
            "created_at": time.time()
        }
        self.save_promo_codes()
        logging.info(f"✅ Promo code created: {code}")
    
    def deactivate_promo_code(self, code: str):
        """Deactivates promo code"""
        if code.upper() in self.promo_codes:
            self.promo_codes[code.upper()]["is_active"] = False
            self.save_promo_codes()
            return True
        return False
    
    def activate_promo_code(self, code: str):
        """Activates promo code"""
        if code.upper() in self.promo_codes:
            self.promo_codes[code.upper()]["is_active"] = True
            self.save_promo_codes()
            return True
        return False
    
    def delete_promo_code(self, code: str):
        """Deletes promo code"""
        if code.upper() in self.promo_codes:
            del self.promo_codes[code.upper()]
            self.save_promo_codes()
            return True
        return False
    
    def edit_promo_code(self, code: str, param: str, value):
        """Edits promo code parameters"""
        if code.upper() not in self.promo_codes:
            return False
        
        promo = self.promo_codes[code.upper()]
        
        if param == "max_uses":
            promo["max_uses"] = int(value) if value.lower() != "none" else None
        elif param == "expires_hours":
            if value.lower() == "none":
                promo["expires_at"] = None
            else:
                promo["expires_at"] = time.time() + (int(value) * 3600)
        elif param == "is_active":
            promo["is_active"] = value.lower() == "true"
        else:
            return False
        
        self.save_promo_codes()
        return True
    
    def check_promo_code(self, code: str, user_id: int):
        """Checks promo code for user"""
        code = code.upper()
        
        if code not in self.promo_codes:
            return {"success": False, "message": "❌ Promo code not found"}
        
        promo = self.promo_codes[code]
        
        # Check activity
        if not promo.get("is_active", True):
            return {"success": False, "message": "❌ Promo code is not active"}
        
        # Check expiration
        if promo.get("expires_at") and time.time() > promo["expires_at"]:
            return {"success": False, "message": "❌ Promo code has expired"}
        
        # Check usage limit
        if promo.get("max_uses") and promo.get("uses_count", 0) >= promo["max_uses"]:
            return {"success": False, "message": "❌ Promo code usage limit reached"}
        
        # Check reuse
        if user_id in self.user_db and code in self.user_db[user_id].get("used_promo_codes", set()):
            return {"success": False, "message": "❌ You have already used this promo code"}
        
        return {"success": True, "promo": promo}
    
    def apply_promo_code(self, code: str, user_id: int):
        """Applies promo code for user"""
        check_result = self.check_promo_code(code, user_id)
        if not check_result["success"]:
            return check_result
        
        promo = check_result["promo"]
        user_data = self.user_db[user_id]
        rewards = promo["rewards"]
        
        # Give rewards
        reward_text = "🎁 Rewards received:\n"
        
        if "money" in rewards:
            user_data["money"] += rewards["money"]
            reward_text += f"💰 Money: +{rewards['money']:,}\n"
        
        if "sp" in rewards:
            user_data["total_sp"] += rewards["sp"]
            reward_text += f"💎 SP: +{rewards['sp']:,}\n"
        
        if "cards_today" in rewards:
            user_data["cards_today"] += rewards["cards_today"]
            reward_text += f"🎴 Attempts: +{rewards['cards_today']}\n"
        
        if "arena_battles" in rewards:
            user_data["arena_battles_today"] = max(0, user_data.get("arena_battles_today", 0) - rewards["arena_battles"])
            reward_text += f"⚔️ Arena battles: +{rewards['arena_battles']}\n"
        
        if "shards" in rewards:
            user_data["shards"] += rewards["shards"]
            reward_text += f"🀄️ Shards: +{rewards['shards']}\n"
        
        # Add cards if specified
        if "cards" in rewards:
            for rarity, card_names in rewards["cards"].items():
                for card_name in card_names:
                    if card_name not in user_data["cards"][rarity]:
                        user_data["cards"][rarity].add(card_name)
                        reward_text += f"🃏 New card: {card_name} ({rarity})\n"
        
        # Update promo code statistics
        self.promo_codes[code.upper()]["uses_count"] += 1
        user_data["used_promo_codes"].add(code.upper())
        
        self.save_promo_codes()
        
        return {
            "success": True, 
            "message": f"✅ Promo code activated!\n\n{reward_text}"
        }
    
    def get_promo_stats(self):
        """Returns promo code statistics"""
        active_codes = {code: data for code, data in self.promo_codes.items() 
                       if data.get("is_active", True)}
        
        return {
            "total_codes": len(self.promo_codes),
            "active_codes": len(active_codes),
            "details": active_codes
        }
    
    def get_promo_info(self, code: str):
        """Returns detailed info about specific promo code"""
        code = code.upper()
        if code not in self.promo_codes:
            return None
        
        return self.promo_codes[code]

# Initialize promo code system
promo_system = PromoCodeSystem(user_db)
logging.info("✅ Promo code system initialized")

# ================== ARENA FUNCTIONS ==================
def check_arena_availability(user_data):
    """Checks arena availability for user"""
    current_time = time.time()
    
    # Reset daily counter if a day has passed
    if current_time - user_data["last_arena_reset"] >= 24 * 60 * 60:
        user_data["arena_battles_today"] = 0
        user_data["last_arena_reset"] = current_time
    
    # Check cooldown
    time_since_last_battle = current_time - user_data["last_arena_battle"]
    cooldown_remaining = ARENA_COOLDOWN - time_since_last_battle
    
    # Check daily limit
    battles_remaining = ARENA_BATTLES_PER_DAY - user_data["arena_battles_today"]
    
    is_available = cooldown_remaining <= 0 and battles_remaining > 0
    
    return {
        "available": is_available,
        "cooldown_remaining": max(0, cooldown_remaining),
        "battles_remaining": max(0, battles_remaining),
        "battles_used": user_data["arena_battles_today"]
    }

def is_arena_team_complete(user_data):
    """Проверяет, полностью ли собрана команда для арены"""
    team = user_data.get("arena_team", [])
    if not team:
        return False
    
    # Проверяем что все 5 слотов заполнены (не пустые строки)
    return len(team) == 5 and all(slot.strip() for slot in team)

def get_arena_team_info(user_data):
    """Возвращает информацию о команде арены"""
    team = user_data.get("arena_team", [""] * 5)
    team_info = []
    
    for i, card_name in enumerate(team, 1):
        if card_name and card_name.strip():
            # Находим карту в базе
            card_data = None
            for rarity, cards in CARDS_DB.items():
                for card in cards:
                    if card["name"] == card_name:
                        card_data = card
                        break
                if card_data:
                    break
            
            if card_data:
                team_info.append(f"{i}. {card_name} (⚔{card_data.get('attack', 0)} ❤{card_data.get('health', 0)})")
            else:
                team_info.append(f"{i}. {card_name} (❓)")
        else:
            team_info.append(f"{i}. ⏸ Empty")
    
    return "\n".join(team_info)

# ================== CRAFT SYSTEM REINITIALIZATION ==================
logging.info("=== CRAFT SYSTEM REINITIALIZATION ===")

craft_system = None
try:
    # Force reimport and recreate craft_system
    import craft
    importlib.reload(craft)
    
    from craft import CraftSystem
    craft_system = CraftSystem(user_db, CARDS_DB)
    logging.info("✅ CraftSystem force reinitialized")
    
    # Check if methods are available
    if hasattr(craft_system, 'show_craft_menu'):
        logging.info("✅ Method show_craft_menu available")
    else:
        logging.error("❌ Method show_craft_menu NOT available")
        
except Exception as e:
    logging.error(f"❌ Craft reinitialization error: {e}", exc_info=True)
    craft_system = None

# ================== OTHER SYSTEMS IMPORT ==================
try:
    from rating import RatingSystem
    rating_system = RatingSystem(user_db, CARDS_DB)
    logging.info("✅ Rating system initialized")
except Exception as e:
    logging.error(f"❌ Rating initialization error: {e}")
    rating_system = None

try:
    from referral import ReferralSystem
    referral_system = ReferralSystem(user_db)
    logging.info("✅ Referral system initialized")
except Exception as e:
    logging.error(f"❌ Referral initialization error: {e}")
    referral_system = None

try:
    from arena import ArenaSystem
    arena_system = ArenaSystem(user_db, CARDS_DB, RARITY_SETTINGS)
    logging.info("✅ Arena module loaded successfully")
except Exception as e:
    logging.error(f"❌ Arena module loading error: {e}")
    arena_system = None

try:
    from task import TaskSystem
    task_system = TaskSystem(user_db)
    logging.info("✅ Task system initialized")
except Exception as e:
    logging.error(f"❌ Task initialization error: {e}")
    task_system = None

try:
    from bonuses import BonusSystem
    bonus_system = BonusSystem(user_db, CARDS_DB, RARITY_SETTINGS)
    logging.info("✅ Bonus system initialized")
except Exception as e:
    logging.error(f"❌ Bonus initialization error: {e}")
    bonus_system = None

# ================== SYSTEM CHECKS ==================
logging.info("=== SYSTEM CHECKS ===")
logging.info(f"✅ Referrals: {referral_system is not None}")
logging.info(f"✅ Arena: {arena_system is not None}") 
logging.info(f"✅ Craft: {craft_system is not None}")
logging.info(f"✅ Tasks: {task_system is not None}")
logging.info(f"✅ Bonuses: {bonus_system is not None}")
logging.info(f"✅ Promo codes: {promo_system is not None}")

# ================== KEYBOARDS ==================
def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎴 Get Card")],
        [KeyboardButton("📋 Menu"), KeyboardButton("🗂 My Cards")]
    ], resize_keyboard=True)

def get_profile_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗡 Arena", callback_data="arena"),
         InlineKeyboardButton("🔗 Referrals", callback_data="referral")],
        [InlineKeyboardButton("🏆 Rating", callback_data="rating"),
         InlineKeyboardButton("🃏 Create Card", callback_data="combine")],
        [InlineKeyboardButton("⚙️ Craft", callback_data="craft_menu"),
         InlineKeyboardButton("📋 Quests", callback_data="quests")],
        [InlineKeyboardButton("🎁 Bonuses", callback_data="bonuses"),
         InlineKeyboardButton("🎫 Promo Code", callback_data="promo_menu")],
        [InlineKeyboardButton("🌌 Change Universe", callback_data="change_universe")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ])

def get_collection_keyboard(user_id):
    user_data = user_db[user_id]
    duplicates = user_data.get("duplicates", {})
    shards = user_data.get("shards", 0)
    
    buttons = []
    for rarity, settings in RARITY_SETTINGS.items():
        user_card_count = len(user_db[user_id]["cards"][rarity])
        total_cards = len(CARDS_DB.get(rarity, []))
        dup_count = duplicates.get(rarity, 0)
        
        if user_card_count > 0:
            button_text = f"{settings['emoji']} {rarity} - {user_card_count}/{total_cards} (🎴{dup_count})"
            buttons.append([InlineKeyboardButton(button_text, callback_data=f"collection_{rarity}")])
    
    if not buttons:
        buttons.append([InlineKeyboardButton("❌ You don't have any cards yet", callback_data="none")])
    
    return InlineKeyboardMarkup(buttons)

# ================== IMPROVED MEDIA SENDING ==================
async def send_media(context: ContextTypes.DEFAULT_TYPE, chat_id: int, media_url: str, caption: str, reply_markup=None):
    """Умная отправка медиа с улучшенным определением типа"""
    if not media_url:
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup)
        return

    try:
        media_url_lower = media_url.lower()
        
        # УЛУЧШЕННОЕ ОПРЕДЕЛЕНИЕ ТИПА МЕДИА
        if media_url_lower.endswith('.mp4') or 'video' in media_url_lower:
            await context.bot.send_video(
                chat_id=chat_id,
                video=media_url,
                caption=caption,
                reply_markup=reply_markup,
                read_timeout=60,
                write_timeout=60,
                connect_timeout=60,
                supports_streaming=True
            )
        
        elif media_url_lower.endswith(('.gif', '.webm')) or 'gif' in media_url_lower:
            # ВАЖНО: GIF отправляем как анимацию, а не как документ!
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=media_url,
                caption=caption,
                reply_markup=reply_markup,
                read_timeout=60,
                write_timeout=60,
                connect_timeout=60
            )
        
        # Для OneDrive ВСЕГДА используем send_document (кроме GIF)
        elif OneDriveHelper.is_onedrive_link(media_url) and not media_url_lower.endswith('.gif'):
            await context.bot.send_document(
                chat_id=chat_id,
                document=media_url,
                caption=caption,
                reply_markup=reply_markup,
                read_timeout=90,
                write_timeout=90,
                connect_timeout=90
            )
        
        else:
            # Для всех остальных случаев (изображения) - send_photo
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=media_url,
                caption=caption,
                reply_markup=reply_markup,
                read_timeout=60,
                write_timeout=60,
                connect_timeout=60
            )

    except Exception as e:
        logging.error(f"Media send failed for {media_url}: {e}")
        
        # 🔄 УЛУЧШЕННЫЙ ФОЛБЭК
        try:
            # Если это GIF, пробуем как анимацию
            if media_url.lower().endswith('.gif'):
                await context.bot.send_animation(
                    chat_id=chat_id,
                    animation=media_url,
                    caption=f"{caption}\n\n⚠️ Sent as animation",
                    reply_markup=reply_markup
                )
            else:
                # Для остальных - как документ
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=media_url,
                    caption=f"{caption}\n\n📎 Sent as document",
                    reply_markup=reply_markup,
                    read_timeout=90,
                    write_timeout=90
                )
        except Exception as e2:
            logging.error(f"Fallback send also failed: {e2}")
            
            # 📝 ФИНАЛЬНЫЙ ФОЛБЭК - только текст
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{caption}\n\n⚠️ Media unavailable: {str(e)[:100]}",
                reply_markup=reply_markup
            )

# ================== ONEDRIVE TESTING COMMAND ==================
async def test_onedrive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестирование OneDrive ссылок"""
    user_id = update.effective_user.id
    
    # Примеры тестовых ссылок (замени на свои реальные)
    test_links = [
        "https://i.postimg.cc/Y0dwptB3/New-Project-12-Copy-2-Copy-E100-A8-F.png",
        "https://1drv.ms/v/s!YOUR_TEST_LINK_HERE",  # Замени на реальную ссылку
    ]
    
    text = "🔗 Тестирование ссылок\n\n"
    
    for i, link in enumerate(test_links, 1):
        try:
            # Проверяем конвертацию
            is_onedrive = OneDriveHelper.is_onedrive_link(link)
            converted = OneDriveHelper.convert_onedrive_link(link)
            
            text += f"🔹 Ссылка #{i}:\n"
            text += f"   📎 Оригинал: {link[:50]}...\n"
            text += f"   🔄 OneDrive: {'✅' if is_onedrive else '❌'}\n"
            text += f"   🎯 Конвертировано: {converted != link}\n"
            
            # Пробуем отправить
            if is_onedrive:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=link,
                    caption=f"Test OneDrive #{i}"
                )
            else:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=link,
                    caption=f"Test Image #{i}"
                )
            text += f"   📤 Отправка: ✅ Успешно\n\n"
            
        except Exception as e:
            text += f"   📤 Отправка: ❌ Ошибка: {str(e)[:100]}...\n\n"
    
    await update.message.reply_text(text)

# ================== DEBUG CARD COMMAND ==================
async def debug_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка информации о карте"""
    if not context.args:
        await update.message.reply_text("Укажите название карты: /debug_card 'Large Police Toilet'")
        return
    
    card_name = " ".join(context.args)
    
    # Ищем карту во всех редкостях
    found = False
    for rarity, cards in CARDS_DB.items():
        for card in cards:
            if card["name"].lower() == card_name.lower():
                found = True
                text = (
                    f"🔍 Найдена карта:\n"
                    f"📝 Название: {card['name']}\n"
                    f"🎯 Редкость: {rarity}\n"
                    f"🖼️ Фото: {card.get('photo', 'Нет')}\n"
                    f"🎞️ Анимация: {card.get('animation', 'Нет')}\n"
                    f"⚔️ Атака: {card.get('attack', 0)}\n"
                    f"❤️ Здоровье: {card.get('health', 0)}\n"
                    f"💎 Ценность: {card.get('value', 0)}"
                )
                
                # Пробуем отправить медиа
                media_url = card.get("animation") or card.get("photo")
                if media_url:
                    try:
                        await send_media(
                            context=context,
                            chat_id=update.effective_chat.id,
                            media_url=media_url,
                            caption=text
                        )
                    except Exception as e:
                        await update.message.reply_text(f"{text}\n\n❌ Ошибка отправки: {e}")
                else:
                    await update.message.reply_text(f"{text}\n\n❌ Нет медиа ссылки")
                return
                
    if not found:
        await update.message.reply_text(f"❌ Карта '{card_name}' не найдена в базе")

# ================== DEBUG ULTIMATE CARD COMMAND ==================
async def debug_ultimate_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка данных ультимейт карты"""
    if not context.args:
        await update.message.reply_text("Укажите название карты: /debug_ultimate 'Best Duo'")
        return
    
    card_name = " ".join(context.args)
    
    # Ищем в COMBINE_DATA
    combine_card = next((c for c in COMBINE_DATA if c["name"].lower() == card_name.lower()), None)
    
    # Ищем в CARDS_DB
    ultimate_card = next((c for c in CARDS_DB["Ultimate"] if c["name"].lower() == card_name.lower()), None)
    
    text = f"🔍 Debug card: {card_name}\n\n"
    
    if combine_card:
        text += f"✅ Found in COMBINE_DATA:\n"
        text += f"   📝 Name: {combine_card['name']}\n"
        text += f"   🖼️ Preview: {combine_card.get('preview', 'NO')}\n"
        text += f"   🎞️ Result Animation: {combine_card.get('result_animation', 'NO')}\n"
        text += f"   ⚔️ Attack: {combine_card.get('attack', 0)}\n"
        text += f"   ❤️ Health: {combine_card.get('health', 0)}\n"
    else:
        text += f"❌ NOT FOUND in COMBINE_DATA\n"
    
    text += "\n"
    
    if ultimate_card:
        text += f"✅ Found in CARDS_DB['Ultimate']:\n"
        text += f"   📝 Name: {ultimate_card['name']}\n"
        text += f"   🖼️ Photo: {ultimate_card.get('photo', 'NO')}\n"
        text += f"   🎞️ Animation: {ultimate_card.get('animation', 'NO')}\n"
        text += f"   ⚔️ Attack: {ultimate_card.get('attack', 0)}\n"
        text += f"   ❤️ Health: {ultimate_card.get('health', 0)}\n"
        text += f"   💎 Value: {ultimate_card.get('value', 0)}\n"
    else:
        text += f"❌ NOT FOUND in CARDS_DB['Ultimate']\n"
    
    # Показываем все ультимейт карты для сравнения
    text += f"\n📋 All Ultimate cards:\n"
    for card in CARDS_DB.get('Ultimate', []):
        text += f"   • {card['name']} (Animation: {card.get('animation', 'NO')})\n"
    
    await update.message.reply_text(text)

# ================== FIX PROBLEMATIC CARDS COMMAND ==================
async def fix_problematic_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка и исправление проблемных карт"""
    user_id = update.effective_user.id
    
    problem_cards = []
    for rarity, cards in CARDS_DB.items():
        for card in cards:
            media_url = card.get("animation") or card.get("photo")
            if media_url and ('catbox.moe' in media_url.lower() and media_url.lower().endswith('.gif')):
                problem_cards.append({
                    'name': card['name'],
                    'rarity': rarity,
                    'url': media_url,
                    'type': 'GIF from catbox.moe'
                })
    
    if problem_cards:
        text = "🔧 Проблемные карты (GIF из catbox.moe):\n\n"
        for card in problem_cards:
            text += f"• {card['name']} ({card['rarity']})\n"
            text += f"  📎 {card['url']}\n\n"
        
        text += "💡 Эти карты будут отправляться как анимации"
    else:
        text = "✅ Проблемных карт не найдено"
    
    await update.message.reply_text(text)

# ================== IMPROVED CARD DETAILS FUNCTIONS ==================
async def show_card_details(query: CallbackQuery, user_id: int, rarity: str, index: int = 0):
    try:
        user_cards = list(user_db[user_id]["cards"][rarity])
        
        if not user_cards:
            await query.answer("You don't have cards of this rarity", show_alert=True)
            return

        # Обеспечиваем корректный индекс
        index = max(0, min(index, len(user_cards) - 1))
        card_name = user_cards[index]
        
        # Находим карту в базе
        card = None
        for card_data in CARDS_DB.get(rarity, []):
            if card_data["name"] == card_name:
                card = card_data
                break

        if not card:
            await query.answer("❌ Card not found in database", show_alert=True)
            return

        # Создаем описание карты
        user_data = user_db[user_id]
        duplicates = user_data.get("duplicates", {})
        dup_count = duplicates.get(rarity, 0)
        
        caption = (
            f"{RARITY_SETTINGS[rarity]['emoji']} {card['name']}\n\n"
            f"{RARITY_SETTINGS[rarity]['rarity_emoji']} Rarity: {rarity}\n"
            f"⚔️ Attack: {card.get('attack', 0):,}\n"
            f"❤️ Health: {card.get('health', 0):,}\n"
            f"💎 Value: {card.get('value', 0):,} SP\n"
            f"🎴 Duplicates of this rarity: {dup_count}\n"
            f"📊 Card {index + 1} of {len(user_cards)}"
        )

        # Создаем кнопки навигации
        buttons = []
        
        if len(user_cards) > 1:
            nav_buttons = []
            
            if index > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"nav_{rarity}_{index-1}"))
            else:
                nav_buttons.append(InlineKeyboardButton("◀️", callback_data="none"))
            
            nav_buttons.append(InlineKeyboardButton(f"{index+1}/{len(user_cards)}", callback_data="none"))
            
            if index < len(user_cards) - 1:
                nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"nav_{rarity}_{index+1}"))
            else:
                nav_buttons.append(InlineKeyboardButton("▶️", callback_data="none"))
            
            buttons.append(nav_buttons)

        buttons.append([InlineKeyboardButton("🔙 Back to Rarities", callback_data="back_collection")])

        keyboard = InlineKeyboardMarkup(buttons)
        media_url = card.get("animation") or card.get("photo")
        
        # ПРОСТОЙ И НАДЕЖНЫЙ СПОСОБ ОТПРАВКИ
        try:
            if media_url:
                # Определяем тип медиа по расширению
                if media_url.lower().endswith(('.gif', '.webm')):
                    # Для GIF используем анимацию
                    await query.edit_message_media(
                        media=InputMediaAnimation(media=media_url, caption=caption),
                        reply_markup=keyboard
                    )
                else:
                    # Для всего остального - фото
                    await query.edit_message_media(
                        media=InputMediaPhoto(media=media_url, caption=caption),
                        reply_markup=keyboard
                    )
            else:
                # Если нет медиа, просто редактируем текст
                await query.edit_message_text(
                    caption + "\n\n🖼️ No image available", 
                    reply_markup=keyboard
                )
                
        except Exception as media_error:
            logging.error(f"Media error for card {card_name}: {media_error}")
            # Если ошибка с медиа, показываем только текст
            await query.edit_message_text(
                caption + "\n\n⚠️ Image temporarily unavailable",
                reply_markup=keyboard
            )

    except Exception as e:
        logging.error(f"Error in show_card_details for {rarity} card {index}: {str(e)}")
        await query.answer("❌ Error loading card", show_alert=True)

async def safe_show_card_details(query: CallbackQuery, user_id: int, rarity: str, index: int = 0):
    try:
        if rarity not in RARITY_SETTINGS:
            await query.answer("❌ Unknown rarity", show_alert=True)
            return
            
        user_cards = list(user_db[user_id]["cards"][rarity])
        if not user_cards:
            await query.answer("❌ You don't have cards of this rarity", show_alert=True)
            return
            
        # Обеспечиваем корректный индекс
        index = max(0, min(index, len(user_cards) - 1))
        await show_card_details(query, user_id, rarity, index)
        
    except Exception as e:
        logging.error(f"Error in safe_show_card_details: {e}")
        await query.answer("❌ Error occurred while loading card", show_alert=True)

# ================== MAIN FUNCTIONS ==================
async def delayed_bot_username_setup(context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(2)
    if referral_system and referral_system.bot_username is None:
        try:
            bot_info = await context.bot.get_me()
            referral_system.set_bot_username(bot_info.username)
            logging.info(f"✅ Delayed bot username setup: {bot_info.username}")
        except Exception as e:
            logging.error(f"❌ Delayed bot username error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Initialize user if not exists
    if user_id not in user_db:
        user_db[user_id] = {
            "cards": defaultdict(set),
            "total_sp": 0,
            "money": 0,
            "username": user.full_name,
            "last_card_time": 0,
            "cards_today": CARDS_BEFORE_COOLDOWN,
            "arena_team": [],
            "arena_cups": 0,
            "battles_won": 0,
            "battles_lost": 0,
            "last_bonus_time": 0,
            "completed_quests": [],
            "duplicates": {"Common": 0, "Rare": 0, "Epic": 0, "Legend": 0, "Mythic": 0},
            "shards": 0,
            "craft_attempts": 0,
            # New fields
            "last_arena_battle": 0,
            "arena_battles_today": 0,
            "last_arena_reset": time.time(),
            "used_promo_codes": set()
        }
    else:
        user_db[user_id]["username"] = user.full_name
    
    if referral_system:
        if referral_system.bot_username is None:
            try:
                bot_info = await context.bot.get_me()
                referral_system.set_bot_username(bot_info.username)
                logging.info(f"✅ Bot username for referrals: {bot_info.username}")
            except Exception as e:
                logging.error(f"❌ Bot username error: {e}")
                asyncio.create_task(delayed_bot_username_setup(context))
    
    if referral_system:
        await referral_system.process_referral_start(update, context, user.id)
    
    await update.message.reply_text(
        f"👋 Welcome, {user.full_name}!\n\n"
        f"🎴 Get Card - get a random card\n"
        f"💡 You have {user_db[user_id]['cards_today']} attempts to get cards",
        reply_markup=get_main_keyboard()
    )

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = user_db[user.id]
    total_cards = sum(len(cards) for cards in user_data["cards"].values())
    total_all_cards = sum(len(cards) for cards in CARDS_DB.values())

    current_time = time.time()
    time_since_last_card = current_time - user_data["last_card_time"]
    
    # Always show how many attempts are available
    available_cards = user_data["cards_today"]
    
    cooldown_status = ""
    if user_data["cards_today"] <= 0:
        if time_since_last_card < COOLDOWN_TIME:
            remaining_time = COOLDOWN_TIME - time_since_last_card
            hours = int(remaining_time // 3600)
            minutes = int((remaining_time % 3600) // 60)
            cooldown_status = f"\n⏰ Cooldown: {hours}h {minutes}m"
        else:
            # If cooldown passed, reset counter
            user_data["cards_today"] = CARDS_BEFORE_COOLDOWN
            available_cards = CARDS_BEFORE_COOLDOWN

    text = (
        f"👤 {user_data['username']}:\n"
        f"🗺️ Universe: Skibidi Toilet\n"
        f"🃏 Total Cards: {total_cards} of {total_all_cards}\n"
        f"🎖️ Season Points: {user_data['total_sp']:,} S.P\n"
        f"💰 Money: {user_data['money']:,}\n"
        f"🎴 Available attempts: {available_cards}"
        f"{cooldown_status}"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=get_profile_keyboard())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=get_profile_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "🎴 Get Card":
        await send_random_card(update, context, user_id)
    elif text == "📋 Menu":
        await show_profile(update, context)
    elif text == "🗂 My Cards":
        await show_collection(update, user_id)
    elif text.lower() == "craft all":
        await craft_all_materials(update, context, user_id)
    elif text.lower() == "test onedrive":
        await test_onedrive(update, context)
    elif text.lower().startswith("/debug_card"):
        await debug_card(update, context)
    elif text.lower().startswith("/debug_ultimate"):
        await debug_ultimate_card(update, context)
    elif text.lower().startswith("/fix_cards"):
        await fix_problematic_cards(update, context)
    else:
        await update.message.reply_text("Use menu buttons for navigation", reply_markup=get_main_keyboard())

async def send_random_card(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        user_data = user_db[user_id]
        current_time = time.time()
        
        # Check if there are available attempts
        if user_data["cards_today"] <= 0:
            time_since_last_card = current_time - user_data["last_card_time"]
            if time_since_last_card < COOLDOWN_TIME:
                remaining_time = COOLDOWN_TIME - time_since_last_card
                hours = int(remaining_time // 3600)
                minutes = int((remaining_time % 3600) // 60)
                await update.message.reply_text(
                    f"⏰ Next card available in {hours}h {minutes}m\n\n"
                    f"💡 You can craft additional attempts through the craft menu!"
                )
                return
            else:
                # If cooldown passed, give standard 3 attempts
                user_data["cards_today"] = CARDS_BEFORE_COOLDOWN

        # Use one attempt
        user_data["cards_today"] -= 1
        
        valid_rarities = [r for r, s in RARITY_SETTINGS.items() if s["chance"] > 0]
        weights = [RARITY_SETTINGS[r]["chance"] for r in valid_rarities]
        rarity = random.choices(valid_rarities, weights=weights, k=1)[0]

        card = random.choice(CARDS_DB[rarity])
        
        is_new = card["name"] not in user_data["cards"][rarity]
        
        if is_new:
            user_data["cards"][rarity].add(card["name"])
        else:
            user_data["duplicates"][rarity] = user_data["duplicates"].get(rarity, 0) + 1
            shards_per_duplicate = {
                "Common": 1,
                "Rare": 2, 
                "Epic": 3,
                "Legend": 5,
                "Mythic": 10
            }
            user_data["shards"] = user_data.get("shards", 0) + shards_per_duplicate.get(rarity, 1)

        card_sp = card.get("value", 0)
        user_data["total_sp"] += card_sp
        
        money_range = MONEY_RANGES[rarity]
        card_money = random.randint(money_range["min"], money_range["max"])
        user_data["money"] += card_money
        
        user_data["last_card_time"] = current_time

        if task_system:
            task_system.update_quest_progress(user_id, "daily_cards", 1)
            task_system.update_quest_progress(user_id, "weekly_cards", 1)

        media_url = card.get("animation") or card.get("photo")

        if is_new:
            caption = (
                f"✨ NEW CARD!\n\n"
                f"{RARITY_SETTINGS[rarity]['emoji']} {card['name']}\n\n"
                f"{RARITY_SETTINGS[rarity]['rarity_emoji']} Rarity: {rarity}\n"
                f"⚔️ Attack: {card.get('attack', 0):,}\n"
                f"❤️ Health: {card.get('health', 0):,}\n\n"
                f"💎 Value: {card_sp:,} SP"
            )
        else:
            caption = (
                f"{RARITY_SETTINGS[rarity]['emoji']} {card['name']}\n"
                f"(🔄Duplicate)\n\n"
                f"{RARITY_SETTINGS[rarity]['rarity_emoji']} Rarity: {rarity}\n"
                f"⚔️ Attack: {card.get('attack', 0):,}\n"
                f"❤️ Health: {card.get('health', 0):,}\n\n"
                f"💎 Value: {card_sp:,} SP"
            )

        # Show how many attempts left
        caption += f"\n\n🎴 Attempts left: {user_data['cards_today']}"

        await send_media(
            context=context,
            chat_id=update.message.chat_id,
            media_url=media_url,
            caption=caption
        )

    except Exception as e:
        logging.error(f"Error giving card: {str(e)}")
        await update.message.reply_text("⚠️ Error occurred while getting card")

async def show_collection(update: Update, user_id: int):
    try:
        user_data = user_db[user_id]
        duplicates = user_data.get("duplicates", {})
        shards = user_data.get("shards", 0)
        
        total_cards = sum(len(cards) for cards in user_data["cards"].values())
        if total_cards == 0:
            text = "❌ You don't have any cards yet\n\nClick '🎴 Get Card' to start your collection!"
            if update.message:
                await update.message.reply_text(text)
            else:
                query = update.callback_query
                await query.edit_message_text(text)
            return
        
        text = "Choose rarity:\n\n"
        text += f"🀄️ Shards: {shards}\n\n"
        
        keyboard = get_collection_keyboard(user_id)
        
        if update.message:
            await update.message.reply_text(text, reply_markup=keyboard)
        else:
            query = update.callback_query
            await query.edit_message_text(text, reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Error in show_collection: {e}")
        if update.message:
            await update.message.reply_text("❌ Error loading collection")

# ================== CRAFT ALL MATERIALS ==================
async def craft_all_materials(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    user_data = user_db[user_id]
    duplicates = user_data.get("duplicates", {})
    shards = user_data.get("shards", 0)
    
    total_attempts = 0
    used_materials = []
    
    craft_settings = {
        "Common": {"required": 10, "attempts": 1, "emoji": "⚡️", "name": "Common"},
        "Rare": {"required": 10, "attempts": 2, "emoji": "✨", "name": "Rare"},
        "Epic": {"required": 10, "attempts": 4, "emoji": "🐉", "name": "Epic"},
        "Legend": {"required": 10, "attempts": 8, "emoji": "🎲", "name": "Legendary"},
        "Mythic": {"required": 10, "attempts": 16, "emoji": "💎", "name": "Mythic"}
    }
    
    for rarity, setting in craft_settings.items():
        current_duplicates = duplicates.get(rarity, 0)
        if current_duplicates >= setting["required"]:
            batches = current_duplicates // setting["required"]
            used_duplicates = batches * setting["required"]
            attempts_from_rarity = batches * setting["attempts"]
            
            user_data["duplicates"][rarity] -= used_duplicates
            total_attempts += attempts_from_rarity
            used_materials.append(f"{used_duplicates} {setting['emoji']}")
    
    if shards >= 10:
        batches = shards // 10
        used_shards = batches * 10
        attempts_from_shards = batches * 1
        
        user_data["shards"] -= used_shards
        total_attempts += attempts_from_shards
        used_materials.append(f"{used_shards} 🀄️")
    
    if total_attempts == 0:
        await update.message.reply_text("❌ Not enough materials for crafting!")
        return
    
    # ADD ATTEMPTS TO cards_today
    user_data["cards_today"] += total_attempts
    
    if task_system:
        task_system.update_quest_progress(user_id, "craft_attempts", total_attempts)
    
    text = (
        f"🎉 Mass crafting completed!\n\n"
        f"📦 Materials used:\n"
        f"{chr(10).join(f'• {material}' for material in used_materials)}\n\n"
        f"🎁 Additional attempts received: {total_attempts}\n\n"
        f"🎴 Total available attempts: {user_data['cards_today']}\n\n"
        f"💡 Use the '🎴 Get Card' button!"
    )
    
    await update.message.reply_text(text)

# ================== ARENA FUNCTIONS ==================
async def show_arena_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if arena_system is None:
        await update.callback_query.answer("❌ Arena module unavailable", show_alert=True)
        return
        
    query = update.callback_query
    user_id = query.from_user.id
    user_data = user_db[user_id]
    
    # Check arena status
    arena_status = check_arena_availability(user_data)
    
    # Получаем информацию о команде
    team_info = get_arena_team_info(user_data)
    team_complete = is_arena_team_complete(user_data)
    
    status_text = ""
    if arena_status["available"] and team_complete:
        status_text = f"✅ Available battles: {arena_status['battles_remaining']}"
    elif not team_complete:
        status_text = "❌ Team not complete (5 cards required)"
    else:
        if arena_status["cooldown_remaining"] > 0:
            hours = int(arena_status["cooldown_remaining"] // 3600)
            minutes = int((arena_status["cooldown_remaining"] % 3600) // 60)
            status_text = f"⏰ Cooldown: {hours:02d}:{minutes:02d}"
        else:
            status_text = f"🎯 Limit reached: {arena_status['battles_used']}/{ARENA_BATTLES_PER_DAY}"
    
    text = (
        f"⚔️ Arena\n\n"
        f"🏆 Cups: {user_data['arena_cups']:,}\n"
        f"📊 Wins/Losses: {user_data['battles_won']}/{user_data['battles_lost']}\n\n"
        f"👥 Your Team:\n{team_info}\n\n"
        f"{status_text}"
    )
    
    buttons = [
        [InlineKeyboardButton("🔍 Find Opponent", callback_data="arena_find")],
        [InlineKeyboardButton("👥 My Team", callback_data="arena_team")],
        [InlineKeyboardButton("📊 Statistics", callback_data="arena_stats")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def show_arena_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if arena_system is None:
        await update.callback_query.answer("❌ Arena module unavailable", show_alert=True)
        return
    user_id = update.callback_query.from_user.id
    user_data = user_db[user_id]
    await arena_system.show_arena_team(update, context, user_data)

async def show_team_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if arena_system is None:
        await update.callback_query.answer("❌ Arena module unavailable", show_alert=True)
        return
    user_id = update.callback_query.from_user.id
    user_data = user_db[user_id]
    await arena_system.show_team_slot(update, context, user_data)

async def show_cards_by_rarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if arena_system is None:
        await update.callback_query.answer("❌ Arena module unavailable", show_alert=True)
        return
    user_id = update.callback_query.from_user.id
    user_data = user_db[user_id]
    await arena_system.show_cards_by_rarity(update, context, user_data)

async def select_card_for_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if arena_system is None:
        await update.callback_query.answer("❌ Arena module unavailable", show_alert=True)
        return
    
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    parts = data.split("_")
    slot_index = int(parts[2])
    card_name = " ".join(parts[3:])
    
    card_rarity = None
    for rarity, cards in CARDS_DB.items():
        for card in cards:
            if card["name"] == card_name:
                card_rarity = rarity
                break
        if card_rarity:
            break
    
    if not card_rarity:
        await query.answer("❌ Card not found", show_alert=True)
        return
    
    if card_name not in user_db[user_id]["cards"][card_rarity]:
        await query.answer("❌ You don't have this card", show_alert=True)
        return
    
    current_team = user_db[user_id].get("arena_team", [""] * 5)
    if card_name in current_team:
        await query.answer("❌ This card is already used in another slot", show_alert=True)
        return
    
    arena_system.update_arena_team(user_db[user_id], slot_index, card_name)
    
    user_data = user_db[user_id]
    await arena_system.show_arena_team(update, context, user_data)

async def find_arena_enemy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if arena_system is None:
        await update.callback_query.answer("❌ Arena module unavailable", show_alert=True)
        return
        
    query = update.callback_query
    user_id = query.from_user.id
    user_data = user_db[user_id]
    
    # Проверяем, полностью ли собрана команда
    if not is_arena_team_complete(user_data):
        await query.answer("❌ Your team is not complete! You need 5 cards in your arena team.", show_alert=True)
        return
    
    # Check arena availability
    arena_status = check_arena_availability(user_data)
    
    if not arena_status["available"]:
        if arena_status["cooldown_remaining"] > 0:
            hours = int(arena_status["cooldown_remaining"] // 3600)
            minutes = int((arena_status["cooldown_remaining"] % 3600) // 60)
            await query.answer(
                f"⏰ Next battle in {hours:02d}:{minutes:02d}\n"
                f"🎯 Battles left today: {arena_status['battles_remaining']}",
                show_alert=True
            )
        else:
            await query.answer(
                f"🎯 Daily limit reached: {ARENA_BATTLES_PER_DAY} battles",
                show_alert=True
            )
        return
    
    await query.answer("🔍 Searching for opponent...")
    await arena_system.find_arena_enemy(update, context, user_data)
    
    # Update last battle time and counter
    user_data["last_arena_battle"] = time.time()
    user_data["arena_battles_today"] += 1

async def process_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if arena_system is None:
        await update.callback_query.answer("❌ Arena module unavailable", show_alert=True)
        return
    user_id = update.callback_query.from_user.id
    user_data = user_db[user_id]
    await arena_system.process_battle(update, context, user_data)

# ================== PROMO CODE MANAGEMENT ==================
async def promo_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню управления промо-кодами"""
    user_id = update.effective_user.id
    ADMINS = [123456789]  # Ваш ID
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ Недостаточно прав")
        return
    
    text = (
        "🎫 *Управление промо-кодами*\n\n"
        "Доступные команды:\n"
        "▫️ /create_promo CODE REWARDS - Создать промо-код\n"
        "▫️ /list_promos - Список всех промо-кодов\n" 
        "▫️ /edit_promo CODE PARAM VALUE - Изменить промо-код\n"
        "▫️ /deactivate_promo CODE - Деактивировать промо-код\n"
        "▫️ /activate_promo CODE - Активировать промо-код\n"
        "▫️ /delete_promo CODE - Удалить промо-код\n"
        "▫️ /promo_stats CODE - Статистика по промо-коду\n"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def list_promos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все промо-коды"""
    user_id = update.effective_user.id
    ADMINS = [123456789]
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ Недостаточно прав")
        return
    
    stats = promo_system.get_promo_stats()
    
    if not stats['details']:
        await update.message.reply_text("📭 Нет активных промо-кодов")
        return
    
    text = "🎫 *Все промо-коды:*\n\n"
    
    for code, details in stats['details'].items():
        status = "🟢" if details.get('is_active', True) else "🔴"
        uses = f"{details.get('uses_count', 0)}"
        if details.get('max_uses'):
            uses += f"/{details['max_uses']}"
        
        expires = "Бессрочно"
        if details.get('expires_at'):
            from datetime import datetime
            exp_time = datetime.fromtimestamp(details['expires_at']).strftime('%d.%m.%Y %H:%M')
            expires = exp_time
        
        text += f"{status} *{code}*\n"
        text += f"   🎁 {details['rewards']}\n"
        text += f"   📊 Использовано: {uses}\n"
        text += f"   ⏰ Истекает: {expires}\n\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def edit_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменить параметры промо-кода"""
    user_id = update.effective_user.id
    ADMINS = [123456789]
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ Недостаточно прав")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text(
            "🔧 Использование:\n"
            "▫️ /edit_promo CODE PARAM VALUE\n\n"
            "Доступные параметры:\n"
            "▫️ max_uses NUMBER - макс. использований\n"
            "▫️ expires_hours HOURS - срок действия в часах\n"
            "▫️ is_active true/false - активность\n\n"
            "Примеры:\n"
            "▫️ /edit_promo TEST1 max_uses 100\n"
            "▫️ /edit_promo TEST2 expires_hours 48\n"
            "▫️ /edit_promo TEST3 is_active false"
        )
        return
    
    code = context.args[0].upper()
    param = context.args[1]
    value = context.args[2]
    
    if code not in promo_system.promo_codes:
        await update.message.reply_text(f"❌ Промо-код {code} не найден")
        return
    
    try:
        if promo_system.edit_promo_code(code, param, value):
            await update.message.reply_text(f"✅ Промо-код {code} обновлен!")
        else:
            await update.message.reply_text("❌ Неизвестный параметр")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def deactivate_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Деактивировать промо-код"""
    user_id = update.effective_user.id
    ADMINS = [123456789]
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ Недостаточно прав")
        return
    
    if not context.args:
        await update.message.reply_text("Укажите код: /deactivate_promo CODE")
        return
    
    code = context.args[0].upper()
    
    if promo_system.deactivate_promo_code(code):
        await update.message.reply_text(f"🔴 Промо-код {code} деактивирован")
    else:
        await update.message.reply_text(f"❌ Промо-код {code} не найден")

async def activate_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Активировать промо-код"""
    user_id = update.effective_user.id
    ADMINS = [123456789]
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ Недостаточно прав")
        return
    
    if not context.args:
        await update.message.reply_text("Укажите код: /activate_promo CODE")
        return
    
    code = context.args[0].upper()
    
    if promo_system.activate_promo_code(code):
        await update.message.reply_text(f"🟢 Промо-код {code} активирован")
    else:
        await update.message.reply_text(f"❌ Промо-код {code} не найден")

async def delete_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить промо-код"""
    user_id = update.effective_user.id
    ADMINS = [123456789]
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ Недостаточно прав")
        return
    
    if not context.args:
        await update.message.reply_text("Укажите код: /delete_promo CODE")
        return
    
    code = context.args[0].upper()
    
    if promo_system.delete_promo_code(code):
        await update.message.reply_text(f"🗑️ Промо-код {code} удален")
    else:
        await update.message.reply_text(f"❌ Промо-код {code} не найден")

async def promo_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальная статистика по промо-коду"""
    user_id = update.effective_user.id
    ADMINS = [123456789]
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ Недостаточно прав")
        return
    
    if not context.args:
        await update.message.reply_text("Укажите код: /promo_info CODE")
        return
    
    code = context.args[0].upper()
    
    promo_info = promo_system.get_promo_info(code)
    if not promo_info:
        await update.message.reply_text(f"❌ Промо-код {code} не найден")
        return
    
    text = f"📊 *Статистика промо-кода {code}:*\n\n"
    text += f"🎁 Награды: {promo_info['rewards']}\n"
    text += f"📊 Использовано: {promo_info.get('uses_count', 0)}"
    if promo_info.get('max_uses'):
        text += f" / {promo_info['max_uses']}"
    text += f"\n🔄 Активен: {'✅ Да' if promo_info.get('is_active', True) else '❌ Нет'}\n"
    
    if promo_info.get('expires_at'):
        from datetime import datetime
        exp_time = datetime.fromtimestamp(promo_info['expires_at']).strftime('%d.%m.%Y %H:%M')
        remaining = promo_info['expires_at'] - time.time()
        hours = int(remaining // 3600)
        text += f"⏰ Истекает: {exp_time}\n"
        text += f"⏳ Осталось: {hours} часов\n"
    else:
        text += "⏰ Срок: Бессрочно\n"
    
    created_time = datetime.fromtimestamp(promo_info.get('created_at', time.time()))
    text += f"📅 Создан: {created_time.strftime('%d.%m.%Y %H:%M')}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

# ================== PROMO CODE SYSTEM ==================
async def promo_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /promo command"""
    if not context.args:
        await update.message.reply_text(
            "🎁 Promo code usage:\n"
            "▫️ /promo CODE\n\n"
            "💡 Example: /promo WELCOME2024"
        )
        return
    
    code = " ".join(context.args)
    user_id = update.effective_user.id
    
    result = promo_system.apply_promo_code(code, user_id)
    await update.message.reply_text(result["message"])

async def create_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create promo code (admin only)"""
    user_id = update.effective_user.id
    
    # Admin check (replace with your ID)
    ADMINS = [123456789]  # Replace with your Telegram ID
    if user_id not in ADMINS:
        await update.message.reply_text("❌ Insufficient permissions")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "🔧 Create promo code:\n"
            "▫️ /create_promo CODE REWARDS\n\n"
            "💡 Examples:\n"
            "▫️ /create_promo TEST1 money:1000,sp:500,cards_today:3\n"
            "▫️ /create_promo TEST2 money:5000,shards:10 expires:24 uses:50\n"
            "▫️ /create_promo TEST3 cards:Common-[CardName1,CardName2]"
        )
        return
    
    code = context.args[0]
    rewards_str = context.args[1]
    
    # Parse rewards
    rewards = {}
    for item in rewards_str.split(','):
        if ':' in item:
            key, value = item.split(':', 1)
            if key in ['money', 'sp', 'cards_today', 'arena_battles', 'shards']:
                rewards[key] = int(value)
            elif key == 'cards':
                # Format: Common-[Card1,Card2]
                rarity, cards_str = value.split('-', 1)
                card_names = [c.strip() for c in cards_str.strip('[]').split(',')]
                rewards['cards'] = {rarity: card_names}
    
    # Additional parameters
    expires_hours = None
    max_uses = None
    
    for i in range(2, len(context.args)):
        if context.args[i].startswith('expires:'):
            expires_hours = int(context.args[i].split(':')[1])
        elif context.args[i].startswith('uses:'):
            max_uses = int(context.args[i].split(':')[1])
    
    promo_system.create_promo_code(code, rewards, max_uses, expires_hours)
    
    await update.message.reply_text(
        f"✅ Promo code created: {code.upper()}\n"
        f"🎁 Rewards: {rewards}\n"
        f"⏰ Valid for: {expires_hours or '∞'} hours\n"
        f"🎯 Uses: {max_uses or '∞'}"
    )

async def promo_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Promo code statistics (admin only)"""
    user_id = update.effective_user.id
    ADMINS = [123456789]  # Replace with your Telegram ID
    
    if user_id not in ADMINS:
        await update.message.reply_text("❌ Insufficient permissions")
        return
    
    stats = promo_system.get_promo_stats()
    
    text = f"📊 Promo code statistics:\n\n"
    text += f"📁 Total codes: {stats['total_codes']}\n"
    text += f"🟢 Active: {stats['active_codes']}\n\n"
    
    for code, details in stats['details'].items():
        text += f"🔹 {code}:\n"
        text += f"   🎁 {details['rewards']}\n"
        text += f"   📊 Used: {details.get('uses_count', 0)}"
        if details.get('max_uses'):
            text += f"/{details['max_uses']}"
        text += f"\n   ⏰ Expires: {details.get('expires_at', 'Never')}\n\n"
    
    await update.message.reply_text(text)

async def show_promo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows promo code menu"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "🎫 Promo Codes\n\n"
        "💎 Use promo codes to get bonuses!\n\n"
        "🔹 To activate a promo code, use command:\n"
        "▫️ /promo CODE\n\n"
        "🔹 Example:\n"
        "▫️ <code>/promo WELCOME2024</code>\n\n"
        "💡 Follow our updates to not miss new promo codes!"
    )
    
    buttons = [
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# ================== CARD COMBINING ==================
async def show_combine_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not COMBINE_DATA:
        await query.edit_message_text("⛔ No available recipes")
        return

    buttons = [
        [InlineKeyboardButton(f"🧬 {card['name']}", callback_data=f"combine_{card['name']}")]
        for card in COMBINE_DATA
    ]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")])

    await query.edit_message_text(
        "🔮 Choose card to create:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_combine_details(query: CallbackQuery, card_name: str):
    try:
        user_id = query.from_user.id
        user_data = user_db[user_id]

        card = next((c for c in COMBINE_DATA if c["name"].lower() == card_name.lower()), None)
        if not card:
            await query.answer("⛔ Recipe not found", show_alert=True)
            return

        components = []
        for req in card["required_cards"]:
            has_item = any(req in user_data["cards"][rarity] for rarity in user_data["cards"])
            components.append(f"• {req} - {'✅' if has_item else '❌'}")

        sp_status = "✅" if user_data["total_sp"] >= card["required_sp"] else "❌"
        money_status = "✅" if user_data["money"] >= card["required_money"] else "❌"

        text = (
            f"🧬 {card['name']}\n\n"
            f"🔮 Required cards:\n" + "\n".join(components) + "\n\n"
            f"💰 Resources:\n"
            f"• {card['required_sp']:,} SP - {sp_status}\n"
            f"• {card['required_money']:,} Money - {money_status}"
        )

        preview = card.get("preview", "")
        if preview:
            await query.message.reply_photo(
                photo=preview,
                caption=text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛠 Create", callback_data=f"craft_{card['name']}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="combine")]
                ])
            )
        else:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛠 Create", callback_data=f"craft_{card['name']}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="combine")]
                ])
            )

    except Exception as e:
        logging.error(f"Error in combine details: {str(e)}")
        await query.answer("⚠️ Error loading recipe")

async def execute_combine(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, card_name: str):
    try:
        user_id = query.from_user.id
        user_data = user_db[user_id]

        card = next((c for c in COMBINE_DATA if c["name"].lower() == card_name.lower()), None)
        if not card:
            await query.answer("⛔ Recipe not found", show_alert=True)
            return

        # ДЕБАГ: Проверяем что нашли в COMBINE_DATA
        logging.info(f"🔍 Found in COMBINE_DATA: {card['name']}")
        logging.info(f"🔍 Combine card data: {card}")

        missing = []
        for req in card["required_cards"]:
            if not any(req in user_data["cards"][r] for r in user_data["cards"]):
                missing.append(req)

        if missing:
            await query.answer(f"⛔ Missing: {', '.join(missing)}", show_alert=True)
            return

        if user_data["total_sp"] < card["required_sp"]:
            await query.answer(f"⛔ Need {card['required_sp'] - user_data['total_sp']} more SP", show_alert=True)
            return

        if user_data["money"] < card["required_money"]:
            await query.answer(f"⛔ Need {card['required_money'] - user_data['money']} more money", show_alert=True)
            return

        for req in card["required_cards"]:
            for rarity in list(user_data["cards"]):
                if req in user_data["cards"][rarity]:
                    user_data["cards"][rarity].remove(req)
                    break

        user_data["cards"]["Ultimate"].add(card["name"])
        user_data["total_sp"] -= card["required_sp"]
        user_data["money"] -= card["required_money"]

        # Ищем в CARDS_DB
        ultimate_card = next((c for c in CARDS_DB["Ultimate"] if c["name"] == card["name"]), None)
        
        # ДЕБАГ: Проверяем что нашли в CARDS_DB
        if ultimate_card:
            logging.info(f"✅ Found in CARDS_DB: {ultimate_card['name']}")
            logging.info(f"✅ Animation URL: {ultimate_card.get('animation', 'NOT FOUND')}")
            logging.info(f"✅ Photo URL: {ultimate_card.get('photo', 'NOT FOUND')}")
        else:
            logging.error(f"❌ Card {card['name']} not found in CARDS_DB['Ultimate']")
            logging.info(f"❌ Available Ultimate cards: {[c['name'] for c in CARDS_DB['Ultimate']]}")

        caption = (
            f"🎉 Successfully created:\n\n"
            f"🧬 {card['name']}\n\n"
            f"👑 Rarity: Ultimate\n"
            f"⚔️ Attack: {card.get('attack', 0):,}\n"
            f"❤️ Health: {card.get('health', 0):,}\n\n"
            f"💠 Value: {card.get('value', 0):,} SP"
        )

        # Пробуем разные варианты получения медиа
        media_url = None
        if ultimate_card:
            media_url = ultimate_card.get("animation") or ultimate_card.get("photo")

        if media_url:
            logging.info(f"🔄 Attempting to send media: {media_url}")
            try:
                await send_media(
                    context=context,
                    chat_id=query.message.chat_id,
                    media_url=media_url,
                    caption=caption,
                    reply_markup=get_main_keyboard()
                )
                await query.message.delete()
                return
            except Exception as media_error:
                logging.error(f"❌ Media send failed: {media_error}")
                # Fallback - отправляем только текст
                await query.message.reply_text(
                    caption + "\n\n⚠️ Media temporarily unavailable",
                    reply_markup=get_main_keyboard()
                )
                await query.message.delete()
        else:
            # Если медиа нет, отправляем только текст
            logging.warning("⚠️ No media URL found for ultimate card")
            await query.message.reply_text(
                caption + "\n\n🖼️ No image available",
                reply_markup=get_main_keyboard()
            )
            await query.message.delete()

    except Exception as e:
        logging.error(f"Crafting error: {str(e)}")
        await query.answer("⚠️ Error creating card", show_alert=True)

# ================== BUTTON HANDLER ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    logging.info(f"🔄 Processing callback: {data} from user {user_id}")

    try:
        # ================== CRAFT HANDLER - FIRST ==================
        if data == "craft_menu":
            logging.info(f"🎯🎯🎯 PROCESSING CRAFT_MENU for user {user_id}")
            
            if craft_system is None:
                logging.error("❌ craft_system is None!")
                await query.answer("❌ Craft system unavailable", show_alert=True)
                return
            
            if not hasattr(craft_system, 'show_craft_menu'):
                logging.error("❌ craft_system doesn't have show_craft_menu method!")
                await query.answer("❌ Craft method not found", show_alert=True)
                return
            
            try:
                if user_id not in user_db:
                    logging.info(f"🆕 Creating new user {user_id}")
                    user_db[user_id] = {
                        "cards": defaultdict(set),
                        "total_sp": 0,
                        "money": 0,
                        "username": query.from_user.full_name,
                        "last_card_time": 0,
                        "cards_today": CARDS_BEFORE_COOLDOWN,
                        "arena_team": [],
                        "arena_cups": 0,
                        "battles_won": 0,
                        "battles_lost": 0,
                        "last_bonus_time": 0,
                        "completed_quests": [],
                        "duplicates": {"Common": 0, "Rare": 0, "Epic": 0, "Legend": 0, "Mythic": 0},
                        "shards": 0,
                        "craft_attempts": 0,
                        "last_arena_battle": 0,
                        "arena_battles_today": 0,
                        "last_arena_reset": time.time(),
                        "used_promo_codes": set()
                    }
                
                logging.info(f"🔄 CALLING show_craft_menu for user_id: {user_id}")
                await craft_system.show_craft_menu(update, context, user_id)
                logging.info("✅ Craft menu successfully shown")
                return
                
            except Exception as e:
                logging.error(f"❌ CRITICAL Error in craft_menu: {e}", exc_info=True)
                await query.answer("❌ Error opening craft menu", show_alert=True)
                return

        # ================== CRAFT BUTTON HANDLERS ==================
        elif data == "craft_common":
            logging.info("🎯 Craft common cards")
            if craft_system:
                await craft_system.craft_from_duplicates(update, context, user_id, "common")
            else:
                await query.answer("❌ Craft system unavailable", show_alert=True)
                
        elif data == "craft_rare":
            logging.info("🎯 Craft rare cards")
            if craft_system:
                await craft_system.craft_from_duplicates(update, context, user_id, "rare")
            else:
                await query.answer("❌ Craft system unavailable", show_alert=True)
                
        elif data == "craft_epic":
            logging.info("🎯 Craft epic cards")
            if craft_system:
                await craft_system.craft_from_duplicates(update, context, user_id, "epic")
            else:
                await query.answer("❌ Craft system unavailable", show_alert=True)
                
        elif data == "craft_legend":
            logging.info("🎯 Craft legendary cards")
            if craft_system:
                await craft_system.craft_from_duplicates(update, context, user_id, "legend")
            else:
                await query.answer("❌ Craft system unavailable", show_alert=True)
                
        elif data == "craft_mythic":
            logging.info("🎯 Craft mythic cards")
            if craft_system:
                await craft_system.craft_from_duplicates(update, context, user_id, "mythic")
            else:
                await query.answer("❌ Craft system unavailable", show_alert=True)
                
        elif data == "craft_shards":
            logging.info("🎯 Craft shards")
            if craft_system:
                await craft_system.craft_from_shards(update, context, user_id)
            else:
                await query.answer("❌ Craft system unavailable", show_alert=True)

        # ================== PROMO CODE HANDLERS ==================
        elif data == "promo_menu":
            await show_promo_menu(update, context)

        # ================== OTHER HANDLERS ==================
        elif data.startswith("collection_"):
            rarity = data.split("_", 1)[1]
            await safe_show_card_details(query, user_id, rarity, 0)

        elif data.startswith("nav_"):
            try:
                parts = data.split("_")
                if len(parts) >= 3:
                    rarity = parts[1]
                    index = int(parts[2])
                    
                    if rarity not in RARITY_SETTINGS:
                        await query.answer("❌ Unknown rarity", show_alert=True)
                        return
                        
                    user_cards = list(user_db[user_id]["cards"][rarity])
                    if not user_cards:
                        await query.answer("❌ You don't have cards of this rarity", show_alert=True)
                        return
                        
                    if index < 0:
                        index = 0
                    elif index >= len(user_cards):
                        index = len(user_cards) - 1
                        
                    await safe_show_card_details(query, user_id, rarity, index)
                else:
                    await query.answer("❌ Invalid navigation format", show_alert=True)
            except ValueError:
                await query.answer("❌ Error in card number", show_alert=True)
            except Exception as e:
                logging.error(f"Navigation error: {e}")
                await query.answer("❌ Navigation error", show_alert=True)

        elif data == "back_collection":
            try:
                # Используем новое сообщение вместо редактирования
                user_data = user_db[user_id]
                duplicates = user_data.get("duplicates", {})
                shards = user_data.get("shards", 0)
                
                text = "Choose rarity:\n\n"
                text += f"🀄️ Shards: {shards}\n\n"
                
                keyboard = get_collection_keyboard(user_id)
                
                await query.message.reply_text(text, reply_markup=keyboard)
                await query.message.delete()
            except Exception as e:
                logging.error(f"Error returning to collection: {e}")
                await query.answer("❌ Error", show_alert=True)

        elif data == "combine":
            await show_combine_menu(update, context)

        elif data.startswith("combine_"):
            card_name = data.split("_", 1)[1]
            await show_combine_details(query, card_name)

        elif data.startswith("craft_"):
            card_name = data.split("_", 1)[1]
            await execute_combine(query, context, card_name)

        # ================== RATING HANDLERS ==================
        elif data == "rating":
            await rating_system.show_rating_menu(update, context, user_id)
            
        elif data.startswith("rating_"):
            category = data.split("_", 1)[1]
            if category == "back":
                await rating_system.show_rating_menu(update, context, user_id)
            else:
                await rating_system.show_rating(update, context, user_id, category)

        # ================== REFERRAL HANDLERS ==================
        elif data == "referral":
            await referral_system.show_referral_menu(update, context, user_id)
            
        elif data == "referral_list":
            await referral_system.show_referral_list(update, context, user_id)

        # ================== QUEST HANDLERS ==================
        elif data == "quests":
            if task_system:
                await task_system.show_quests_menu(update, context, user_id)
            else:
                await query.answer("❌ Task system unavailable", show_alert=True)
                
        elif data == "quests_daily":
            if task_system:
                try:
                    await task_system.show_daily_quests(update, context, user_id)
                except Exception as e:
                    if "Message is not modified" not in str(e):
                        logging.error(f"Error showing daily quests: {e}")
            else:
                await query.answer("❌ Task system unavailable", show_alert=True)
                
        elif data == "quests_weekly":
            if task_system:
                try:
                    await task_system.show_weekly_quests(update, context, user_id)
                except Exception as e:
                    if "Message is not modified" not in str(e):
                        logging.error(f"Error showing weekly quests: {e}")
            else:
                await query.answer("❌ Task system unavailable", show_alert=True)
                
        elif data == "quests_achievements":
            if task_system:
                await task_system.show_achievements(update, context, user_id)
            else:
                await query.answer("❌ Task system unavailable", show_alert=True)
                
        elif data == "claim_daily_quests":
            if task_system:
                await task_system.claim_quest_rewards(update, context, user_id, "daily")
            else:
                await query.answer("❌ Task system unavailable", show_alert=True)
                
        elif data == "claim_weekly_quests":
            if task_system:
                await task_system.claim_quest_rewards(update, context, user_id, "weekly")
            else:
                await query.answer("❌ Task system unavailable", show_alert=True)
                
        elif data == "claim_achievements":
            if task_system:
                await task_system.claim_quest_rewards(update, context, user_id, "achievements")
            else:
                await query.answer("❌ Task system unavailable", show_alert=True)
                
        elif data == "claim_all_quests":
            if task_system:
                await task_system.claim_all_rewards(update, context, user_id)
            else:
                await query.answer("❌ Task system unavailable", show_alert=True)

        # ================== BONUS HANDLERS ==================
        elif data == "bonuses":
            if bonus_system:
                await bonus_system.show_bonuses_menu(update, context, user_id)
            else:
                await query.answer("❌ Bonus system unavailable", show_alert=True)
                
        elif data == "claim_available_bonuses":
            if bonus_system:
                await bonus_system.claim_available_bonuses(update, context, user_id)
            else:
                await query.answer("❌ Bonus system unavailable", show_alert=True)

        # ================== ARENA HANDLERS ==================
        elif data == "arena":
            await show_arena_menu(update, context)
            
        elif data == "arena_team":
            await show_arena_team(update, context)
            
        elif data.startswith("team_slot_"):
            await show_team_slot(update, context)
            
        elif data.startswith("choose_rarity_"):
            await show_cards_by_rarity(update, context)
            
        elif data.startswith("select_card_"):
            await select_card_for_team(update, context)
            
        elif data == "arena_find":
            await find_arena_enemy(update, context)
            
        elif data == "battle_attack":
            await arena_system.process_battle(update, context, user_db[user_id])
            
        elif data == "start_round":
            await arena_system.process_round(update, context, user_db[user_id])
            
        elif data == "continue_round":
            await arena_system.process_round(update, context, user_db[user_id])
            
        elif data == "finish_battle":
            await arena_system.show_battle_result(update, context, user_db[user_id])

        elif data == "change_universe":
            await show_universe_menu(update, context, user_id)

        elif data == "back_to_profile":
            await show_profile(update, context)

        elif data == "back_to_main":
            await query.edit_message_text("Main menu:", reply_markup=get_main_keyboard())

        elif data == "none":
            pass

        else:
            await query.edit_message_text("🚧 Section under development")

    except Exception as e:
        logging.error(f"❌ General button processing error: {str(e)}", exc_info=True)
        try:
            await query.answer("⚠️ An error occurred", show_alert=True)
        except:
            pass

# ================== UNIVERSE CHANGE FUNCTION ==================
async def show_universe_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    await query.answer()
    
    user_data = user_db[user_id]
    username = user_data.get("username", "Player")
    
    text = (
        f"🌌 {username}, universe change\n\n"
        f"🚧 Section under development!\n\n"
        f"📡 Coming soon:\n"
        f"• Switch between different universes\n"
        f"• Collect unique cards\n"
        f"• Discover new game mechanics\n"
        f"• Explore different worlds\n\n"
        f"💫 Stay tuned for updates!"
    )
    
    buttons = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="change_universe")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================== LAUNCH ==================
if __name__ == "__main__":
    app = ApplicationBuilder() \
        .token(TOKEN) \
        .connect_timeout(30) \
        .read_timeout(30) \
        .pool_timeout(30) \
        .build()

    logging.info("🔄 Starting bot with COMPLETE PROMO CODE MANAGEMENT...")

    # Main handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Promo code handlers
    app.add_handler(CommandHandler("promo", promo_code_command))
    app.add_handler(CommandHandler("create_promo", create_promo_command))
    app.add_handler(CommandHandler("promo_stats", promo_stats_command))
    
    # New promo management handlers
    app.add_handler(CommandHandler("promo_manage", promo_management))
    app.add_handler(CommandHandler("list_promos", list_promos_command))
    app.add_handler(CommandHandler("edit_promo", edit_promo_command))
    app.add_handler(CommandHandler("deactivate_promo", deactivate_promo_command))
    app.add_handler(CommandHandler("activate_promo", activate_promo_command))
    app.add_handler(CommandHandler("delete_promo", delete_promo_command))
    app.add_handler(CommandHandler("promo_info", promo_info_command))
    
    # Debug handlers
    app.add_handler(CommandHandler("debug_card", debug_card))
    app.add_handler(CommandHandler("debug_ultimate", debug_ultimate_card))
    app.add_handler(CommandHandler("test_onedrive", test_onedrive))
    app.add_handler(CommandHandler("fix_cards", fix_problematic_cards))

    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logging.error(f"❌ Error in handler: {context.error}", exc_info=True)
    
    app.add_error_handler(error_handler)

    try:
        logging.info("✅ Bot ready to work! Waiting for messages...")
        logging.info("🎫 Promo code management: COMPLETE")
        app.run_polling(
            poll_interval=1,
            timeout=30,
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query']
        )
    except Exception as e:
        logging.critical(f"💥 Critical error: {str(e)}", exc_info=True)
    finally:
        save_user_data()
