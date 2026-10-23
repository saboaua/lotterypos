"""Constants for Lottery POS."""
DOMAIN = "lottery_pos"
STORAGE_KEY = "lottery_pos.data"
STORAGE_VERSION = 1
PANEL_URL = "lottery-pos"
STATIC_URL = "/lottery_pos_static/lottery-panel.js"
SIGNAL_UPDATE = f"{DOMAIN}_update"
PLATFORMS = ["sensor"]
VERSION = "0.7.4"

# draw_time = informational, cutoff = last minute to sell for TODAY's draw (HH:MM local)
DEFAULT_GAMES = [
    {"id": "diario", "name": "Diario", "color": "#22c55e", "draw_time": "13:00", "cutoff": "12:45", "logo": ""},
    {"id": "corsow", "name": "Corsow", "color": "#f59e0b", "draw_time": "13:00", "cutoff": "12:45", "logo": ""},
    {"id": "super4", "name": "Super-4", "color": "#3b82f6", "draw_time": "13:00", "cutoff": "12:45", "logo": ""},
    {"id": "flamingo", "name": "Flamingo", "color": "#a855f7", "draw_time": "13:00", "cutoff": "12:45", "logo": ""},
    {"id": "philb_am", "name": "Philb-AM", "color": "#84cc16", "draw_time": "11:00", "cutoff": "10:45", "logo": ""},
    {"id": "philb_pm", "name": "Philb-PM", "color": "#ef4444", "draw_time": "19:00", "cutoff": "18:45", "logo": ""},
]

# mode: exact | perm | bf | back | chances  (see README). multiplier = payout per 1.00 staked. PLACEHOLDERS - edit to your rules.
DEFAULT_BET_TYPES = [
    {"key": "4_cifra", "label": "4 Cifra", "digits": 4, "mode": "exact", "multiplier": 5000},
    {"key": "3_cifra", "label": "3 Cifra", "digits": 3, "mode": "exact", "multiplier": 500},
    {"key": "2_cifra_3ch", "label": "2 Cifra 3CH", "digits": 2, "mode": "chances", "multiplier": 20},
    {"key": "4_skina", "label": "4 Skina", "digits": 4, "mode": "perm", "multiplier": 200},
    {"key": "3_skina", "label": "3 Skina", "digits": 3, "mode": "perm", "multiplier": 80},
    {"key": "2_cifra_bf", "label": "2 Cifra B/F", "digits": 2, "mode": "bf", "multiplier": 40},
    {"key": "2_cifra_b", "label": "2 Cifra B", "digits": 2, "mode": "back", "multiplier": 70},
]

TICKET_DEFAULTS = {
    "font": "mono", "size": 12, "width": 72, "align": "center", "header": "", "footer": "Good luck!",
    "show_logo": True, "logo_height": 40, "show_name": True, "show_retailer": True, "show_datetime": True,
    "bold_total": True, "show_barcode": True, "show_qr": False, "qr_size": 28, "qr_prefix": "",
}

# trigger: min_plays | min_games | min_amount
# games: [] = all games; otherwise only those game ids count toward the trigger
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
