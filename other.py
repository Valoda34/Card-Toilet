# other.py
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import json
import logging
from data import user_db, CARDS_DB, COMBINE_DATA, get_main_keyboard, RARITY_SETTINGS

async def handle_arena(update, context, user_db):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = user_db[user_id]
    
    # Calculate team stats
    attack = sum(card.get('attack', 0) for card in user_data['team'] if card)
    health = sum(card.get('health', 0) for card in user_data['team'] if card)
    
    # Format team display
    team_display = []
    for i, card in enumerate(user_data['team']):
        prefix = "┏➤" if i == 0 else "┗➤" if i == 4 else "┣➤"
        if card:
            rarity_emoji = next(
                (RARITY_SETTINGS[r]['emoji'] for r in RARITY_SETTINGS 
                if any(c['name'] == card['name'] for c in CARDS_DB.get(r, [])),
                "🔘"
            )
            team_display.append(f"{prefix} {rarity_emoji} {card['name']}")
        else:
            team_display.append(f"{prefix} Empty")
    
    text = (
        f"{user_data['username']}, you can assemble a team of cards and fight other players.\n\n"
        f"🍤 Your team\n" + "\n".join(team_display) + "\n\n"
        f"🏆 Cups: 0\n"
        f"🗡️ Attack: {attack:,}\n"
        f"❤️ Health: {health:,}"
    )
    
    keyboard = [
        [InlineKeyboardButton("Find the Enemy", callback_data="arena_fight"),
         InlineKeyboardButton("Team", callback_data="arena_edit")],
        [InlineKeyboardButton("World Boss", callback_data="world_boss"),
         InlineKeyboardButton("Statistics", callback_data="arena_stats")],
        [InlineKeyboardButton("Back", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_arena_edit(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = user_db[user_id]
    
    # Format team display with ❌ for empty slots
    team_display = []
    for i, card in enumerate(user_data['team']):
        prefix = "┏➤" if i == 0 else "┗➤" if i == 4 else "┣➤"
        if card:
            rarity_emoji = next(
                (RARITY_SETTINGS[r]['emoji'] for r in RARITY_SETTINGS 
                if any(c['name'] == card['name'] for c in CARDS_DB.get(r, [])),
                "🔘"
            )
            team_display.append(f"{prefix} {rarity_emoji} {card['name']}")
        else:
            team_display.append(f"{prefix} ❌")
    
    text = (
        f"🏕{user_data['username']}, to assemble a team, click on the slots below and choose a card.\n\n"
        f"🍤 Your team\n" + "\n".join(team_display)
    )
    
    # Create slot buttons (5 buttons with ❎ emoji)
    slot_buttons = [
        InlineKeyboardButton("❎", callback_data=f"team_slot_{i}")
        for i in range(5)
    ]
    
    keyboard = [
        slot_buttons,
        [InlineKeyboardButton("Back", callback_data="arena_back")]
    ]
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_team_slot_select(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    
    text = (
        f"🃏 {user_db[user_id]['username']}, choose a card.\n"
        f"➖➖➖➖➖➖"
    )
    
    # Create rarity selection buttons
    keyboard = []
    for rarity in RARITY_SETTINGS:
        if user_db[user_id]['cards'][rarity]:
            keyboard.append([
                InlineKeyboardButton(
                    f"{RARITY_SETTINGS[rarity]['emoji']} {rarity}",
                    callback_data=f"team_rarity_{rarity}")
            ])
    
    keyboard.append([InlineKeyboardButton("Back", callback_data="arena_edit")])
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_team_rarity_select(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    rarity = query.data.split("_")[2]
    
    # Get user's cards of selected rarity sorted by attack+health (strongest first)
    user_cards = []
    for card_name in user_db[user_id]['cards'][rarity]:
        card = next((c for c in CARDS_DB[rarity] if c['name'] == card_name), None)
        if card:
            user_cards.append(card)
    
    # Sort by strength (attack + health)
    user_cards.sort(key=lambda x: x.get('attack', 0) + x.get('health', 0), reverse=True)
    
    # Create card selection buttons
    keyboard = []
    for card in user_cards:
        keyboard.append([
            InlineKeyboardButton(
                f"{card['name']} (⚔{card.get('attack', 0):,} ❤{card.get('health', 0):,})",
                callback_data=f"team_card_{card['name']}")
        ])
    
    keyboard.append([InlineKeyboardButton("Back", callback_data="team_select")])
    
    await query.edit_message_text(
        text=query.message.text,  # Keep the same text
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_team_card_select(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    card_name = query.data.split("_", 2)[2]
    
    # Get the stored slot index
    slot_index = context.user_data.get("selected_slot", 0)
    
    # Find the card in database
    selected_card = None
    for rarity in CARDS_DB:
        for card in CARDS_DB[rarity]:
            if card['name'] == card_name:
                selected_card = card
                break
        if selected_card:
            break
    
    if selected_card:
        # Update user's team
        user_db[user_id]['team'][slot_index] = selected_card
    
    # Return to team edit screen
    await handle_arena_edit(update, context)

async def handle_arena_fight(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = user_db[user_id]
    
    # Check if team is complete
    if None in user_data['team'] or any(card is None for card in user_data['team']):
        await query.answer("⚠️ Please complete your team first!", show_alert=True)
        return
    
    # Simulate finding opponent
    opponent_name = "SkibidiBoss"
    
    # Format team display for user
    user_team_display = []
    for i, card in enumerate(user_data['team']):
        prefix = "┏➤" if i == 0 else "┗➤" if i == 4 else "┣➤"
        if card:
            rarity_emoji = next(
                (RARITY_SETTINGS[r]['emoji'] for r in RARITY_SETTINGS 
                if any(c['name'] == card['name'] for c in CARDS_DB.get(r, [])),
                "🔘"
            )
            user_team_display.append(f"{prefix} {rarity_emoji} {card['name']}")
    
    # Simulate opponent team (for demo)
    opponent_team = [
        {"name": "Titan Cameraman", "attack": 15000, "health": 20000},
        {"name": "G-Toilet", "attack": 12000, "health": 18000},
        {"name": "Speaker Titan", "attack": 18000, "health": 22000},
        {"name": "TV Woman", "attack": 14000, "health": 16000},
        {"name": "Cinema Titan", "attack": 16000, "health": 19000}
    ]
    
    # Format team display for opponent
    opponent_team_display = []
    for i, card in enumerate(opponent_team):
        prefix = "┏➤" if i == 0 else "┗➤" if i == 4 else "┣➤"
        opponent_team_display.append(f"{prefix} {card['name']}")
    
    text = (
        f"⚔️ Battle between {user_data['username']} and {opponent_name}\n\n"
        f"{user_data['username']}'s team:\n" + "\n".join(user_team_display) + "\n\n"
        f"{opponent_name}'s team:\n" + "\n".join(opponent_team_display)
    )
    
    keyboard = [
        [InlineKeyboardButton("Attack", callback_data="arena_attack")],
        [InlineKeyboardButton("Back", callback_data="arena_back")]
    ]
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_arena_attack(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = user_db[user_id]
    
    # Calculate user stats
    user_attack = sum(card.get('attack', 0) for card in user_data['team'])
    user_health = sum(card.get('health', 0) for card in user_data['team'])
    
    # Simulate battle result (user wins if attack > 50000)
    battle_result = "won" if user_attack > 50000 else "lost"
    
    text = (
        f"🔥 The final battle!\n\n"
        f"{user_data['username']} {battle_result} the fight!\n\n"
        f"⚔️ Your attack power: {user_attack:,}\n"
        f"🛡️ Your health: {user_health:,}"
    )
    
    # Add rewards for winning
    if battle_result == "won":
        user_data['money'] += 5000
        user_data['total_sp'] += 1000
        text += "\n\n🎉 Reward: 5000 money + 1000 SP"
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back to Arena", callback_data="arena_back")]
        ])
    )

# Остальные функции остаются без изменений
async def handle_rating(update, user_db):
    # ... (существующий код)

async def handle_referral(update, context, user_db):
    # ... (существующий код)

async def show_combine_menu(update, context):
    # ... (существующий код)

async def show_combine_details(query, card_name):
    # ... (существующий код)

async def execute_combine(query, context, card_name):
    # ... (существующий код)
