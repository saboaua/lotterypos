"""Constants for Lottery POS."""
DOMAIN = "lottery_pos"
STORAGE_KEY = "lottery_pos.data"
STORAGE_VERSION = 1
PANEL_URL = "lottery-pos"
STATIC_URL = "/lottery_pos_static/lottery-panel.js"
SIGNAL_UPDATE = f"{DOMAIN}_update"
PLATFORMS = ["sensor"]
VERSION = "0.5.0"

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
