"""Constants for Lottery POS."""
DOMAIN = "lottery_pos"
STORAGE_KEY = "lottery_pos.data"
STORAGE_VERSION = 1
PANEL_URL = "lottery-pos"
STATIC_URL = "/lottery_pos_static/lottery-panel.js"
LEAFLET_URL = "/lottery_pos_static/leaflet"
PANEL_URL_OFFICE = "lottery-office"
SIGNAL_UPDATE = f"{DOMAIN}_update"
PLATFORMS = ["sensor"]
VERSION = "0.10.0"

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
    "show_logo": True, "logo_height": 40, "show_name": True, "show_retailer": True,
    "show_retailer_number": True, "show_retailer_address": True, "show_retailer_phone": False,
    "show_datetime": True, "bold_total": True, "show_barcode": True, "show_qr": False,
    "qr_size": 28, "qr_prefix": "", "show_jackpot": False, "jackpot_mode": "auto",
    "jackpot_text": "", "jackpot_game": "", "border_box": False, "divider": "dashed",
    "padding": 2, "line_gap": 2, "messages": [],
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

# Demo retailers across Aruba (lat/lng for map). Active mix for UI testing.
DEFAULT_RETAILERS = [
    {"id": "r001", "number": "001", "name": "Main Shop", "first_name": "Carlos", "last_name": "Croes", "address": "Caya G. F. Betico Croes 45, Oranjestad", "phone": "+297 582 1001", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": True, "lat": 12.5264, "lng": -70.0358},
    {"id": "r002", "number": "002", "name": "Lucky Shoco", "first_name": "Maria", "last_name": "Frans", "address": "L.G. Smith Blvd 82, Oranjestad", "phone": "+297 582 1002", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 0.0, "active": True, "lat": 12.5190, "lng": -70.0365},
    {"id": "r003", "number": "003", "name": "Palm Beach Kiosk", "first_name": "John", "last_name": "Kelly", "address": "J.E. Irausquin Blvd 230, Palm Beach", "phone": "+297 586 2003", "commission": 12.0, "commission_sell": 12.0, "commission_redeem": 2.0, "active": True, "lat": 12.5681, "lng": -70.0450},
    {"id": "r004", "number": "004", "name": "Noord Express", "first_name": "Ana", "last_name": "Wever", "address": "Bubali 95, Noord", "phone": "+297 586 2004", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 1.5, "active": True, "lat": 12.5660, "lng": -70.0320},
    {"id": "r005", "number": "005", "name": "Santa Cruz Mart", "first_name": "Pedro", "last_name": "Tromp", "address": "Santa Cruz 12", "phone": "+297 585 3005", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": True, "lat": 12.5080, "lng": -69.9800},
    {"id": "r006", "number": "006", "name": "Paradera Plaza", "first_name": "Sofia", "last_name": "Maduro", "address": "Paradera 8", "phone": "+297 585 3006", "commission": 11.0, "commission_sell": 11.0, "commission_redeem": 2.0, "active": True, "lat": 12.5350, "lng": -69.9950},
    {"id": "r007", "number": "007", "name": "San Nicolas Hub", "first_name": "Luis", "last_name": "Kock", "address": "Bernardstraat 22, San Nicolas", "phone": "+297 584 4007", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": True, "lat": 12.4360, "lng": -69.9080},
    {"id": "r008", "number": "008", "name": "Savaneta Corner", "first_name": "Elena", "last_name": "Geerman", "address": "Savaneta 40", "phone": "+297 584 4008", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 1.0, "active": True, "lat": 12.4520, "lng": -69.9380},
    {"id": "r009", "number": "009", "name": "Pos Chiquito Store", "first_name": "Marco", "last_name": "Oduber", "address": "Pos Chiquito 5", "phone": "+297 585 3009", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": False, "lat": 12.4700, "lng": -69.9600},
    {"id": "r010", "number": "010", "name": "Eagle Beach Spot", "first_name": "Nina", "last_name": "Arends", "address": "Eagle Beach 15", "phone": "+297 587 5010", "commission": 12.0, "commission_sell": 12.0, "commission_redeem": 2.0, "active": True, "lat": 12.5450, "lng": -70.0570},
    {"id": "r011", "number": "011", "name": "Airport Express", "first_name": "David", "last_name": "Lopez", "address": "Queen Beatrix Airport Arrivals", "phone": "+297 582 1011", "commission": 8.0, "commission_sell": 8.0, "commission_redeem": 1.0, "active": True, "lat": 12.5014, "lng": -70.0152},
    {"id": "r012", "number": "012", "name": "Tanki Leendert Mini", "first_name": "Rosa", "last_name": "Dirksz", "address": "Tanki Leendert 3", "phone": "+297 585 3012", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": True, "lat": 12.5200, "lng": -70.0100},
    {"id": "r013", "number": "013", "name": "Piedra Plat Market", "first_name": "Hugo", "last_name": "Thiel", "address": "Piedra Plat 7", "phone": "+297 585 3013", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": True, "lat": 12.4900, "lng": -69.9700},
    {"id": "r014", "number": "014", "name": "Brasil Market", "first_name": "Camila", "last_name": "Silva", "address": "Brasil 18, San Nicolas", "phone": "+297 584 4014", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": True, "lat": 12.4400, "lng": -69.9200},
    {"id": "r015", "number": "015", "name": "Cero Colorado Kiosk", "first_name": "Ivan", "last_name": "Rasmijn", "address": "Cero Colorado Rd", "phone": "+297 584 4015", "commission": 9.0, "commission_sell": 9.0, "commission_redeem": 1.5, "active": False, "lat": 12.4250, "lng": -69.8800},
    {"id": "r016", "number": "016", "name": "Malmok Beach Shop", "first_name": "Julia", "last_name": "Werleman", "address": "Malmok Beach", "phone": "+297 586 2016", "commission": 11.0, "commission_sell": 11.0, "commission_redeem": 2.0, "active": True, "lat": 12.5950, "lng": -70.0500},
    {"id": "r017", "number": "017", "name": "Downtown Lottery", "first_name": "Oscar", "last_name": "Figaroa", "address": "Wilhelminastraat 10, Oranjestad", "phone": "+297 582 1017", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": True, "lat": 12.5180, "lng": -70.0330},
    {"id": "r018", "number": "018", "name": "Bushiri Port Shop", "first_name": "Paula", "last_name": "Ras", "address": "Bushiri Port", "phone": "+297 582 1018", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": True, "lat": 12.5150, "lng": -70.0400},
    {"id": "r019", "number": "019", "name": "Seroe Blanco Store", "first_name": "Rico", "last_name": "Thijsen", "address": "Seroe Blanco 2", "phone": "+297 585 3019", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": True, "lat": 12.5000, "lng": -69.9900},
    {"id": "r020", "number": "020", "name": "Wayaca Center", "first_name": "Tina", "last_name": "Croes", "address": "Wayaca 9, Oranjestad", "phone": "+297 582 1020", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": True, "lat": 12.5100, "lng": -70.0250},
]

# Demo retailer logins (username shopNNN / password demoNNN). Hashes only - the passwords are public.
DEMO_LOGINS = {
    "r001": {"username": "shop001", "pw_hash": "pbkdf2_sha256$200000$9352967f2578b1bf6e3c99a486296576$dabb4192558446db0767666c659ac6c93afde6fe28244e21e9d06418ca3b0601"},
    "r002": {"username": "shop002", "pw_hash": "pbkdf2_sha256$200000$4e8d85168415605f70444a1eb225e00e$af395cff7a4dad2eddce1ecd1cde52a4cb12f0f5f48fe0d740599ebf059189bc"},
    "r003": {"username": "shop003", "pw_hash": "pbkdf2_sha256$200000$50c76c717bfe265c594ad44e1006fa34$3a0a4195ecb5f4b4fbed3872f83e6967583503ca12a3d75d240de29259825be4"},
    "r004": {"username": "shop004", "pw_hash": "pbkdf2_sha256$200000$dddab50f918f5664c39e8de8abcd63ee$951fbde392728fb105520910ceb52a152b762dcdb86e0c79dd96ccbaaa438852"},
    "r005": {"username": "shop005", "pw_hash": "pbkdf2_sha256$200000$96b4d3a9ebf55c4e3e78451cfafb0be5$a708e7085534e3a7881ad70cb3cd0038b54e3e38feebce2d66b069b2ce159372"},
    "r006": {"username": "shop006", "pw_hash": "pbkdf2_sha256$200000$1b2d46147d9ae57b486d3064168d1c3a$01ed5c9f1c20bf243a8cadee84de4f73abb8918781520d962dab9d3d8193a6d5"},
    "r007": {"username": "shop007", "pw_hash": "pbkdf2_sha256$200000$b27d64cedb8dd68f9dcbbf21a76bcaaa$6a3cbe5857532474ff6bea04e4db32f30ba8f28356a5eae9a67136184cd49d11"},
    "r008": {"username": "shop008", "pw_hash": "pbkdf2_sha256$200000$0370e45241f3be3598e725b3721ecd14$4c42793aa72b72b2c8b2d40e116e2d2cacbb473153317a0c077fc8256cf1f54e"},
    "r009": {"username": "shop009", "pw_hash": "pbkdf2_sha256$200000$050f9b4d685d29d5fb6fd3798439b437$422cac5091c876e2f48453a0bd04b4bd1d0b1a30fbe854ed8b159d2d465e81cc"},
    "r010": {"username": "shop010", "pw_hash": "pbkdf2_sha256$200000$fe9b10d5347b42bb2be0a1db326c624a$f13a59f96941e0937b32238a290e057d82968032ac781b3763f1d848204e1ee4"},
    "r011": {"username": "shop011", "pw_hash": "pbkdf2_sha256$200000$bee18d38f8100346a32586cefa33438d$39473fc88a266b9f426f6add7ec4b7495c6c7bdbebbfdb67c690e509f7b907bc"},
    "r012": {"username": "shop012", "pw_hash": "pbkdf2_sha256$200000$8dfb5d4262c26d3558232b6bc871c6ae$79f6057eb8f1defb8892a744a2c54319eedc2d4042d41974b1bc36f0e62254fc"},
    "r013": {"username": "shop013", "pw_hash": "pbkdf2_sha256$200000$9cd15b161d5217ba9f8786e34895a020$72c90c189fdb41eade5a9d1325ef5d1e1d1736a093597b5d1ad892423a8d4279"},
    "r014": {"username": "shop014", "pw_hash": "pbkdf2_sha256$200000$d9b2d5114c228847dbed7e750e355c99$1b7181e6f5dbdb356e3758f3e8b216a0840f644ca6d00faaeb1b7b5c75ea391c"},
    "r015": {"username": "shop015", "pw_hash": "pbkdf2_sha256$200000$f4e0a4145d2bf13886d0a7f2ff3df540$e85d81aa05f7e204531303eaba43d31c678d307644e6e85ba42386668f13964e"},
    "r016": {"username": "shop016", "pw_hash": "pbkdf2_sha256$200000$e17fedb0379e63eddce7d8a6f1cdf401$7a27e8ca2d919a9bbdb905a4167598a557502f6613f993ce58259fcec4582ff0"},
    "r017": {"username": "shop017", "pw_hash": "pbkdf2_sha256$200000$8201611653062b6cfe1b722cda8f5861$cf8827f85af1ce69d1b05858a9ab1a7d448cf739914160d373a8d95a37759d36"},
    "r018": {"username": "shop018", "pw_hash": "pbkdf2_sha256$200000$203eb955517aaccd4a4dc1ee2a19b568$ce33b0893250608d90aa44d47c4329b68967156188ea09d2f1850c349da8fd07"},
    "r019": {"username": "shop019", "pw_hash": "pbkdf2_sha256$200000$31cdb41158b72bdfaaab34239fca03fe$960d30fe32e5ff9bb655a94edf3c26ecfdc996b88c237f9d1cbe264cb9ba4194"},
    "r020": {"username": "shop020", "pw_hash": "pbkdf2_sha256$200000$3c7e9431127a081dfdbbd20a16dace55$64e5a246a3e67cab3916bf93ab92adb5415fef2fde063ce29f44d24c85ccfcc6"},
}
