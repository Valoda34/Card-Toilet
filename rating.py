import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

class RatingSystem:
    def __init__(self, user_db, cards_db):
        self.user_db = user_db
        self.cards_db = cards_db
        logging.info("🔄 Rating system initialization")

    def calculate_total_score(self, user_data):
        """Calculates total rating based on all indicators"""
        total_cards = sum(len(cards) for cards in user_data["cards"].values())
        total_sp = user_data.get("total_sp", 0)
        money = user_data.get("money", 0)
        mythic_cards = len(user_data["cards"].get("Mythic", []))
        arena_wins = user_data.get("battles_won", 0)
        arena_cups = user_data.get("arena_cups", 0)

        # Total rating formula (weights can be adjusted)
        total_score = (
            total_cards * 1000 +          # Cards
            total_sp * 0.1 +              # SP
            money * 0.001 +               # Money
            mythic_cards * 100000 +       # Mythic cards
            arena_wins * 5000 +           # Arena wins
            arena_cups * 100              # Arena cups
        )

        return total_score

    def get_top_players(self, category="total", limit=10):
        """Returns top players by category"""
        players = []

        for user_id, user_data in self.user_db.items():
            # Remove username filter to show all players
            # Even if someone doesn't have username, use default name
            username = user_data.get("username", f"Player {user_id}")                                                  
            if category == "total":                                                                                                   
                score = self.calculate_total_score(user_data)
            elif category == "sp":
                score = user_data.get("total_sp", 0)
            elif category == "money":                                                                                                 
                score = user_data.get("money", 0)
            elif category == "mythic":
                score = len(user_data["cards"].get("Mythic", []))                                                                 
            else:
                score = 0
                                                                                                                                  
            players.append({
                "user_id": user_id,
                "username": username,                                                                                                 
                "score": score,
                "total_cards": sum(len(cards) for cards in user_data["cards"].values()),
                "total_sp": user_data.get("total_sp", 0),                                                                             
                "money": user_data.get("money", 0),
                "mythic_cards": len(user_data["cards"].get("Mythic", [])),
                "arena_wins": user_data.get("battles_won", 0),                                                                        
                "arena_cups": user_data.get("arena_cups", 0)
            })
                                                                                                                              
        # Sort by descending score
        players.sort(key=lambda x: x["score"], reverse=True)
        return players[:limit]                                                                                        
    
    def get_user_rank(self, user_id, category="total"):
        """Returns user's position in rating"""                                                                        
        players = self.get_top_players(category, limit=10000)  # Take all players for accurate position

        # Find user index in sorted list                                                                
        for index, player in enumerate(players):
            if player["user_id"] == user_id:
                return index + 1                                                                                      
        
        # If user not found in top, return total count + 1
        return len(players) + 1                                                                                       
    
    def format_score(self, score, category):
        """Formats score for display"""                                                                                
        if category == "total":
            if score >= 1_000_000:
                return f"{score/1_000_000:.1f}m pts"                                                                              
            elif score >= 1_000:
                return f"{score/1_000:.1f}k pts"
            else:                                                                                                                     
                return f"{score:.0f} pts"
        elif category == "sp":
            if score >= 1_000_000:                                                                                                    
                return f"{score/1_000_000:.1f}m SP"
            elif score >= 1_000:
                return f"{score/1_000:.1f}k SP"                                                                                   
            else:
                return f"{score:,} SP"
        elif category == "money":                                                                                                 
            if score >= 1_000_000:
                return f"{score/1_000_000:.1f}m $"
            elif score >= 1_000:                                                                                                      
                return f"{score/1_000:.1f}k $"
            else:
                return f"{score:,} $"                                                                                         
        elif category == "mythic":
            return f"{score:,} cards"
        return f"{score:,}"                                                                                           
    
    def get_category_name(self, category):                                                                                    
        """Returns category name"""
        names = {                                                                                                                 
            "total": "🏆 Overall Top",
            "sp": "💎 Top SP",                                                                                                    
            "money": "💰 Top Money",
            "mythic": "🔮 Top Mythic"
        }                                                                                                                     
        return names.get(category, "Rating")
                                                                                                                          
    async def show_rating_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Shows rating menu"""                                                                                        
        query = update.callback_query
        await query.answer()
                                                                                                                              
        user_data = self.user_db[user_id]
        username = user_data.get("username", "Player")                                                                 
        text = f"💬 {username}, choose category."                                                                    
        
        # VERTICAL BUTTONS (in columns)
        buttons = [                                                                                                               
            [InlineKeyboardButton("🏆 Overall Top", callback_data="rating_total")],
            [InlineKeyboardButton("💎 Top SP", callback_data="rating_sp")],
            [InlineKeyboardButton("💰 Top Money", callback_data="rating_money")],                                                 
            [InlineKeyboardButton("🔮 Top Mythic", callback_data="rating_mythic")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_profile")]                                               
        ]
                                                                                                                              
        await query.edit_message_text(
            text,                                                                                                                 
            reply_markup=InlineKeyboardMarkup(buttons)
        )                                                                                                             
    
    async def show_rating(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, category="total"):
        """Shows rating by category"""                                                                                 
        query = update.callback_query
        await query.answer()
                                                                                                                              
        user_data = self.user_db[user_id]
        username = user_data.get("username", "Player")                                                                 
        
        # Get top players (ALL players, not just current)
        top_players = self.get_top_players(category, 10)
        user_rank = self.get_user_rank(user_id, category)                                                                     
        category_name = self.get_category_name(category)
                                                                                                                              
        # Format text
        text = f"🏆 {username}, here are top-10 players of all time in Skibidi Toilet universe.\n"
        text += f"📊 Category: {category_name}\n"                                                                            
        text += "➖➖➖➖➖➖\n"

        # Add top players (all from database)                                                                                
        for i, player in enumerate(top_players, 1):
            score_text = self.format_score(player["score"], category)                                                 
            
            # Format name (trim if too long)                                                                     
            display_name = player["username"]
            if len(display_name) > 20:                                                                                                
                display_name = display_name[:17] + "..."
                                                                                                                                  
            # Add emoji for first three places
            medal = ""
            if i == 1:                                                                                                                
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "                                                                                                     
            elif i == 3:
                medal = "🥉 "                                                                                         
            
            text += f"{medal}{i}. {display_name} - {score_text}\n"                                                    
        
        text += "➖➖➖➖➖➖\n"                                                                                      
        
        # Show current user's position among all                                                                   
        total_players = len(self.user_db)
        text += f"⏺️ Your position: {user_rank} of {total_players}\n"
                                                                                                                              
        # Add user statistics
        user_score = 0
        if category == "total":                                                                                                   
            user_score = self.calculate_total_score(user_data)
        elif category == "sp":                                                                                                    
            user_score = user_data.get("total_sp", 0)
        elif category == "money":                                                                                                 
            user_score = user_data.get("money", 0)
        elif category == "mythic":                                                                                                
            user_score = len(user_data["cards"].get("Mythic", []))
                                                                                                                              
        user_score_text = self.format_score(user_score, category)
        text += f"📈 Your score: {user_score_text}\n"
                                                                                                                              
        # If user not in top-10, show them separately
        if user_rank > 10:
            text += f"\n🎯 Your position: {user_rank}. {username} - {user_score_text}\n"                               
        
        # VERTICAL NAVIGATION BUTTONS (in columns)                                                                           
        buttons = [
            [InlineKeyboardButton("🏆 Overall Top", callback_data="rating_total")],                                                 
            [InlineKeyboardButton("💎 Top SP", callback_data="rating_sp")],
            [InlineKeyboardButton("💰 Top Money", callback_data="rating_money")],                                                 
            [InlineKeyboardButton("🔮 Top Mythic", callback_data="rating_mythic")],
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"rating_{category}")],                                            
            [InlineKeyboardButton("🔙 Back", callback_data="rating_back")]
        ]
                                                                                                                              
        await query.edit_message_text(
            text,                                                                                                                 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
