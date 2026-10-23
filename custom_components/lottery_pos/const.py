"""Constants for Lottery POS."""
DOMAIN = "lottery_pos"
STORAGE_KEY = "lottery_pos.data"
STORAGE_VERSION = 1
PANEL_URL = "lottery-pos"
STATIC_URL = "/lottery_pos_static/lottery-panel.js"
SIGNAL_UPDATE = f"{DOMAIN}_update"
PLATFORMS = ["sensor"]
VERSION = "0.9.4"

# Western zodiac signs (Aries … Pisces)
ZODIAC_SYMBOLS = [
    {"id": "aries", "label": "Aries", "emoji": "♈"},
    {"id": "taurus", "label": "Taurus", "emoji": "♉"},
    {"id": "gemini", "label": "Gemini", "emoji": "♊"},
    {"id": "cancer", "label": "Cancer", "emoji": "♋"},
    {"id": "leo", "label": "Leo", "emoji": "♌"},
    {"id": "virgo", "label": "Virgo", "emoji": "♍"},
    {"id": "libra", "label": "Libra", "emoji": "♎"},
    {"id": "scorpio", "label": "Scorpio", "emoji": "♏"},
    {"id": "sagittarius", "label": "Sagittarius", "emoji": "♐"},
    {"id": "capricorn", "label": "Capricorn", "emoji": "♑"},
    {"id": "aquarius", "label": "Aquarius", "emoji": "♒"},
    {"id": "pisces", "label": "Pisces", "emoji": "♓"},
]
# legacy Chinese animal ids → ignore / migrate away
_LEGACY_ZODIAC_IDS = {"rat","ox","tiger","rabbit","dragon","snake","horse","goat","monkey","rooster","dog","pig"}

# Play Whe marks (Trinidad & Tobago style): one number 1–36, each with a traditional name
PLAY_WHE_MARKS = [
    {"id": "1", "num": 1, "label": "Centipede", "emoji": "🐛"},
    {"id": "2", "num": 2, "label": "Old Lady", "emoji": "👵"},
    {"id": "3", "num": 3, "label": "Carriage", "emoji": "🛒"},
    {"id": "4", "num": 4, "label": "Dead Man", "emoji": "💀"},
    {"id": "5", "num": 5, "label": "Parson Man", "emoji": "⛪"},
    {"id": "6", "num": 6, "label": "Belly", "emoji": "🤰"},
    {"id": "7", "num": 7, "label": "Hog", "emoji": "🐷"},
    {"id": "8", "num": 8, "label": "Tiger", "emoji": "🐯"},
    {"id": "9", "num": 9, "label": "Cattle", "emoji": "🐮"},
    {"id": "10", "num": 10, "label": "Monkey", "emoji": "🐵"},
    {"id": "11", "num": 11, "label": "Corbeau", "emoji": "🐦‍⬛"},
    {"id": "12", "num": 12, "label": "King", "emoji": "👑"},
    {"id": "13", "num": 13, "label": "Crapaud", "emoji": "🐸"},
    {"id": "14", "num": 14, "label": "Money", "emoji": "💰"},
    {"id": "15", "num": 15, "label": "Sick Woman", "emoji": "🤒"},
    {"id": "16", "num": 16, "label": "Jamette", "emoji": "💃"},
    {"id": "17", "num": 17, "label": "Pigeon", "emoji": "🕊️"},
    {"id": "18", "num": 18, "label": "Water Boat", "emoji": "⛵"},
    {"id": "19", "num": 19, "label": "Horse", "emoji": "🐴"},
    {"id": "20", "num": 20, "label": "Dog", "emoji": "🐶"},
    {"id": "21", "num": 21, "label": "Mouth", "emoji": "👄"},
    {"id": "22", "num": 22, "label": "Rat", "emoji": "🐀"},
    {"id": "23", "num": 23, "label": "House", "emoji": "🏠"},
    {"id": "24", "num": 24, "label": "Queen", "emoji": "👸"},
    {"id": "25", "num": 25, "label": "Morocoy", "emoji": "🐢"},
    {"id": "26", "num": 26, "label": "Fowl", "emoji": "🐔"},
    {"id": "27", "num": 27, "label": "Little Snake", "emoji": "🐍"},
    {"id": "28", "num": 28, "label": "Red Fish", "emoji": "🐟"},
    {"id": "29", "num": 29, "label": "Opium Man", "emoji": "🚬"},
    {"id": "30", "num": 30, "label": "House Cat", "emoji": "🐱"},
    {"id": "31", "num": 31, "label": "Parson Wife", "emoji": "👩"},
    {"id": "32", "num": 32, "label": "Shrimp", "emoji": "🦐"},
    {"id": "33", "num": 33, "label": "Spider", "emoji": "🕷️"},
    {"id": "34", "num": 34, "label": "Blind Man", "emoji": "🕶️"},
    {"id": "35", "num": 35, "label": "Big Snake", "emoji": "🐍"},
    {"id": "36", "num": 36, "label": "Donkey", "emoji": "🫏"},
]

# draw_time = informational, cutoff = last minute to sell for TODAY's draw (HH:MM local)
# format: digit | zodiac | jackpot | whe
# sessions: optional list of same-day draw slots so one game covers multiple draws
DEFAULT_GAMES = [
    {"id": "diario", "name": "Diario", "color": "#22c55e", "draw_time": "13:00", "cutoff": "12:45", "logo": "",
     "format": "digit", "digits": 4, "sessions": []},
    {"id": "corsow", "name": "Corsow", "color": "#f59e0b", "draw_time": "13:00", "cutoff": "12:45", "logo": "",
     "format": "digit", "digits": 4, "sessions": []},
    {"id": "super4", "name": "Super-4", "color": "#3b82f6", "draw_time": "13:00", "cutoff": "12:45", "logo": "",
     "format": "digit", "digits": 4, "sessions": []},
    {"id": "flamingo", "name": "Flamingo", "color": "#a855f7", "draw_time": "13:00", "cutoff": "12:45", "logo": "",
     "format": "digit", "digits": 4, "sessions": []},
    # Single Phillipsburg game with AM + PM sessions (replaces separate Philb-AM / Philb-PM)
    {"id": "philb", "name": "Phillipsburg", "color": "#84cc16", "draw_time": "11:00", "cutoff": "10:45", "logo": "",
     "format": "digit", "digits": 4,
     "sessions": [
         {"id": "am", "label": "AM", "draw_time": "11:00", "cutoff": "10:45"},
         {"id": "pm", "label": "PM", "draw_time": "19:00", "cutoff": "18:45"},
     ]},
    # Play Whe: pick one mark 1–36, four daily sessions
    {"id": "playwhe", "name": "Play Whe", "color": "#e11d48", "draw_time": "10:30", "cutoff": "10:15", "logo": "",
     "format": "whe", "digits": 2, "min_stake": 1.0, "max_stake": 100,
     "bet_types": ["play_whe"],
     "sessions": [
         {"id": "morning", "label": "Morning", "draw_time": "10:30", "cutoff": "10:15"},
         {"id": "midday", "label": "Midday", "draw_time": "13:00", "cutoff": "12:45"},
         {"id": "afternoon", "label": "Afternoon", "draw_time": "16:00", "cutoff": "15:45"},
         {"id": "evening", "label": "Evening", "draw_time": "19:00", "cutoff": "18:45"},
     ]},
]

# mode: exact | perm | bf | back | chances | zodiac | jackpot | whe
DEFAULT_BET_TYPES = [
    {"key": "4_cifra", "label": "4 Cifra", "digits": 4, "mode": "exact", "multiplier": 5000, "min_stake": 0.5, "max_stake": 100},
    {"key": "3_cifra", "label": "3 Cifra", "digits": 3, "mode": "exact", "multiplier": 500, "min_stake": 0.5, "max_stake": 100},
    {"key": "2_cifra_3ch", "label": "2 Cifra 3CH", "digits": 2, "mode": "chances", "multiplier": 20, "min_stake": 0.5, "max_stake": 50},
    {"key": "4_skina", "label": "4 Skina", "digits": 4, "mode": "perm", "multiplier": 200, "min_stake": 0.5, "max_stake": 100},
    {"key": "3_skina", "label": "3 Skina", "digits": 3, "mode": "perm", "multiplier": 80, "min_stake": 0.5, "max_stake": 100},
    {"key": "2_cifra_bf", "label": "2 Cifra B/F", "digits": 2, "mode": "bf", "multiplier": 40, "min_stake": 0.5, "max_stake": 50},
    {"key": "2_cifra_b", "label": "2 Cifra B", "digits": 2, "mode": "back", "multiplier": 70, "min_stake": 0.5, "max_stake": 50},
    {"key": "zodiac", "label": "Zodiac", "digits": 2, "mode": "zodiac", "multiplier": 50, "min_stake": 1, "max_stake": 50},
    {"key": "play_whe", "label": "Play Whe", "digits": 2, "mode": "whe", "multiplier": 24, "min_stake": 1, "max_stake": 100},
    {"key": "jackpot", "label": "Jackpot", "digits": 0, "mode": "jackpot", "multiplier": 1, "min_stake": 1, "max_stake": 20},
]

TICKET_DEFAULTS = {
    "font": "mono", "size": 12, "width": 72, "align": "center", "header": "", "footer": "Good luck!",
    "show_logo": True, "logo_height": 40, "show_name": True, "show_retailer": True, "show_datetime": True,
    "bold_total": True, "show_barcode": True, "show_qr": False, "qr_size": 28, "qr_prefix": "",
    "show_jackpot": False, "jackpot_mode": "auto", "jackpot_text": "", "jackpot_game": "",
    "messages": [],
}

DEFAULT_PROMOTIONS = [
    {
        "id": "buy3",
        "name": "Buy 3 Plays Promo",
        "enabled": False,
        "trigger": "min_plays",
        "trigger_value": 3,
        "games": [],
        "code_digits": 6,
        "label": "Qualified for promotion",
        "instruction": "Visit www.shocolottery.com and check if you have won",
        "url": "https://www.shocolottery.com",
        "start_at": "",
        "end_at": "",
        "prize": 0.0,
        "prizes": [
            {"label": "Cash prize", "amount": 100.0, "quantity": 5},
            {"label": "Consolation", "amount": 25.0, "quantity": 20},
        ],
    },
]
