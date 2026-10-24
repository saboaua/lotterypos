# Lottery POS for Home Assistant (HACS)

Retailer-facing lottery terminal + back office for number games:
games bar, draw date, bet types, keypad, ticket list, send/print, replay, cancel, redeem, results and reports.

## Install
1. HACS → Custom repositories → add this repo (type **Integration**), or copy `custom_components/lottery_pos` into `/config/custom_components/`.
2. Restart Home Assistant → Settings → Devices & services → Add integration → **Lottery POS** (set currency, default `AWG`).
3. Two items appear in the sidebar: **Lottery Sell** (retailer tablet) and **Lottery Back Office** (owner).
4. A persistent notification shows the generated **owner** password - sign in to *Lottery Back Office* and choose your own.
Optional: put a logo at `/config/www/lottery_logo.png` (shown top-left) and game logos at `/config/www/lottery/<game>.png`, then reference them as `/local/lottery/<game>.png` with the `add_game` service.

## Selling
Pick game(s) (several can be selected at once) → draw date → bet type → type the number → amount (keypad or preset .25/.50/…) → **Add to ticket**. Tap a line to edit it, ✕ to delete. **Send & Print** saves the ticket and opens a receipt with a Code 39 barcode.
Physical keyboard works too (digits, Backspace, Tab = switch field, Enter = add).
Scanner: the scan box accepts the barcode. Winning ticket → asks to pay; otherwise its lines are loaded for replay. Buttons: Replay last, Último ticket, Copia number, Cancel, Redeem, Print resultado, Print report, Quick pick.

## Sign-in and roles (v0.10)
| Panel | Who | Sees |
|---|---|---|
| **Lottery Sell** | a retailer (shop) | the sell screen for **its own shop only** |
| **Lottery Back Office** | the lottery owner | games, schedule, holidays, promotions, retailers, results, reports |

Both ask for a **username and password** (separate from Home Assistant users). Rules are enforced on the server, not just hidden in the screen: a shop can never sell, cancel or report as another shop, and a shop login is refused by the back office. 5 wrong passwords lock the username for 5 minutes; owner sessions expire after 30 min idle, retailer sessions after 12 h. Passwords are stored as salted PBKDF2 hashes.

* **Owner**: username `owner`, random password in a persistent notification at first start (must be changed at first sign-in). Forgot it? Run action `lottery_pos.reset_owner_password` (Home Assistant admins only).
* **Retailers**: *Back office -> Retailers -> expand a shop -> Sell login*. Set a username and *Set password* (blank = random, shown once; the shop must change it at first sign-in). New retailers get `shop<number>` as username.
* **Demo accounts**: the 20 sample shops can sign in as `shop001 / demo001` ... `shop020 / demo020` (two of them are disabled to show the red state). **Remove them before going live**: *Back office -> Account -> Remove demo passwords*.

## Draw schedule, holidays and when games are on sale (v0.10)
* **Rolling sales**: a draw goes on sale as soon as the previous one has closed. After the midday cut-off the evening draw is on sale; after the last draw of the day, tomorrow's draw is. The sell screen lists the next draws as buttons and selects the next open one automatically.
* **One draw per day**: in *Games & schedule*, tick *One draw per day* and pick **Midday or Evening (or no draw) for each weekday** - a weekday can only have one draw. Midday/Evening sessions are created automatically if the game has none. Multi-draw tickets follow the pattern.
* **Draw calendar** tab: weekly pattern of every game, a full-year calendar (filter per game, CSV, print) and the **holiday list**. *Add Aruba holidays* fills the public holidays (Easter-based ones calculated) - **verify them against the official calendar**. On a holiday no draw exists and games cannot be sold; adding a holiday warns if tickets were already sold for it.
* **Advance sales limit** (default 30 days) is set in the same tab.

## Results (v0.10)
* **Manual entry** adapts to the game: a 4-digit game accepts exactly 4 digits per box (typing is limited and non-digits are dropped), Play Whe one mark 1-36, jackpots the right number of balls. The server validates too, and refuses results before the draw's cut-off.
* **Automatic import** every 10 minutes while a closed draw has no result, plus *Fetch results now*. Fixes over 0.9.x: the import ran in a background thread and raised Home Assistant thread-safety errors; midday and evening rows overwrote each other; `Phillipsburg` never matched `PHILIPSBURG_AM`; one failing request cancelled everything. Now each request fails on its own with retries, names are matched leniently, AM/PM rows go to the right session, existing different results are never overwritten silently, and the report lists what was imported, unchanged, skipped (with the reason) and which sources failed. If a game is not matched, add its source code under **Result codes** (`CODE` or `CODE:session`).

## Retailer map
*Retailers* shows a real **Leaflet / OpenStreetMap** map (library bundled, tiles need internet). Green = active, red = disabled; click a pin to edit. In a shop's form use *Pick on map* or type latitude/longitude.

## Back office (owner)
Tabs: Games & schedule, **Draw calendar**, Branding & message, Ticket design, Promotions, Results & winners, Reports, Retailers, **Account**. Details:

| Tab | What you can do |
|---|---|
| **Games & schedule** | Per game: name, color, logo, when sales open, cut-off, draw time, draw weekdays, allowed bet types, show/hide on the sell screen. Edit bet type labels, payouts and on/off. Add games. |
| **Branding & message** | Lottery name + logo; the LED-style scrolling message (text, speed, color, on/off). |
| **Ticket design** | Font, size, paper width (48/58/72/80 mm), alignment, header/footer text, **logo on top** (toggle + height in px), name, retailer, date, bold total, **barcode** and **QR code** (size + optional prefix). Live preview and *Print test ticket*. |
| **Promotions** | Create promotions with **game scope** (all games or selected games only) and triggers: **min. plays**, **min. distinct games**, or **min. purchase amount**. When a ticket qualifies, a unique code (4–10 digits) is printed under the plays with label + instruction. Live ticket preview per promotion. |
| **Results & winners** | Enter 1st/2nd/3rd numbers (tickets settle automatically). See per draw how many tickets played, how many won and prizes; list of winning tickets with a **Pay** button; paid vs unpaid totals. |
| **Reports** | Pick dates: tickets sold, cancelled, plays, sales, commission, prizes won/paid, **unpaid prize liability**, **open exposure** (worst case on undrawn plays) and net - by retailer and by game. Print or download CSV. |
| **Retailers** | Edit name, commission %, active; add retailers. |

Scanning: a barcode scanner or a 2D/QR scanner types the code into the scan box on the Sell screen. The ticket number is read from the end of the code, so a QR prefix is fine. A winning ticket asks to pay; any other ticket loads its plays for replay.

## Bet types (defaults – EDIT in `const.py` to your real rules/payouts)
| Bet | Digits | Wins when | Payout x |
|---|---|---|---|
| 4 Cifra | 4 | = 1st prize | 5000 |
| 3 Cifra | 3 | = last 3 of 1st | 500 |
| 2 Cifra 3CH | 2 | = last 2 of any of 3 prizes (pays per hit) | 20 |
| 4 Skina | 4 | any order of 1st | 200 |
| 3 Skina | 3 | any order of last 3 of 1st | 80 |
| 2 Cifra B/F | 2 | = first 2 or last 2 of 1st | 40 |
| 2 Cifra B | 2 | = last 2 of 1st | 70 |
These meanings are my interpretation of the labels – verify against your operator's rules. Game draw times/cut-offs are placeholders.

## Entities, services, events
Sensors: `Lottery sales today`, `Lottery tickets today`, `Lottery unpaid prizes`.
Services: `lottery_pos.set_results`, `cancel_ticket`, `redeem_ticket`, `add_retailer`, `add_game`.
Events (use for ticket messaging/automations): `lottery_pos_ticket_sold`, `lottery_pos_ticket_cancelled`, `lottery_pos_results`, `lottery_pos_winner` (ticket_id, retailer_id, prize).

```yaml
automation:
  - alias: Notify winner
    trigger: {platform: event, event_type: lottery_pos_winner}
    action:
      - service: notify.notify
        data: {message: "Winner {{ trigger.event.data.ticket_id }} pays {{ trigger.event.data.prize }}"}
```

## Promotions (v0.7.2+)

- **Schedule:** optional start/end (`datetime-local`) — leave empty for always-on.
- **Prize:** amount shown when a player checks their promo code on the website.
- **Triggers:** min plays, min distinct games, or min purchase amount; optional game scope.

Enable a promotion in **Back office → Promotions**.

1. **Games** – leave all unchecked to count the whole ticket, or tick specific games so only those lines count.
2. **Trigger**
   - **Min. plays** – e.g. 3 lines of the selected games
   - **Min. distinct games** – e.g. play at least 2 different selected games
   - **Min. purchase amount** – e.g. stake of selected games ≥ 10.00
3. **Code** – 4–10 digit unique number printed on the ticket with your label and instruction (e.g. visit www.shocolottery.com).

On **Send & Print**, qualifying tickets get the promo block under the plays. Codes are unique per ticket and stored on the ticket record. A bad promotion definition never blocks a sale.

## Play Whe & multi-session draws (v0.9.3)

- **Play Whe** format: pick one mark **1–36**. The sell screen shows a grid of traditional marks (Centipede, Tiger, Queen, …). Payout uses the `play_whe` bet type (default **24×**).
- **Sessions**: a single game can have several same-day draws (Morning / Midday / Afternoon / Evening, or AM / PM). Retailers pick the session on the sell screen instead of switching between separate games.
- Default **Phillipsburg** is one game with AM + PM sessions (legacy `philb_am` / `philb_pm` are auto-hidden on upgrade).
- Default **Play Whe** includes four daily sessions. Configure sessions under **Back office → Games**.

## Known limits (v0.7.2)
Cut-off uses HA local time. A ticket becomes payable once all its draws are settled. Receipts print via the browser print dialog (use kiosk-printing for thermal printers). Data stored in `.storage/lottery_pos.data`; back it up. Promotion win checking is external (your website); this POS only issues the code on the ticket.
