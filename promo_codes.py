import json
import os
import logging
from datetime import datetime, timedelta

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
                # Convert date strings back to objects
                for code, details in data.items():
                    if details.get("expires_at"):
                        details["expires_at"] = datetime.fromisoformat(details["expires_at"])
                self.promo_codes = data
        except Exception as e:
            logging.error(f"Error loading promo codes: {e}")
            self.promo_codes = {}

    def save_promo_codes(self):
        """Saves promo codes to file"""
        try:
            # Convert datetime to strings for JSON
            data_to_save = {}
            for code, details in self.promo_codes.items():
                data_to_save[code] = details.copy()
                if data_to_save[code].get("expires_at"):
                    data_to_save[code]["expires_at"] = data_to_save[code]["expires_at"].isoformat()

            with open(self.promo_codes_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving promo codes: {e}")

    def create_promo_code(self, code: str, rewards: dict,
                         max_uses: int = None,
                         expires_in_hours: int = None,
                         is_active: bool = True):
        """Creates new promo code"""
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)

        self.promo_codes[code.upper()] = {
            "rewards": rewards,
            "max_uses": max_uses,
            "uses_count": 0,
            "expires_at": expires_at,
            "is_active": is_active,
            "created_at": datetime.now().isoformat()
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
        if promo.get("expires_at") and datetime.now() > promo["expires_at"]:
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

# Create global instance
promo_system = None
