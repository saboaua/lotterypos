# Lottery POS for Home Assistant (HACS)

Retailer-facing lottery terminal + back office for number games:
games bar, draw date, bet types, keypad, ticket list, send/print, replay, cancel, redeem, results and reports.

## Install
1. HACS → Custom repositories → add this repo (type **Integration**), or copy `custom_components/lottery_pos` into `/config/custom_components/`.
2. Restart Home Assistant → Settings → Devices & services → Add integration → **Lottery POS** (set currency, default `AWG`).
3. A **Lottery** item appears in the sidebar (open it on the retailer tablet).
Optional: put a logo at `/config/www/lottery_logo.png` (shown top-left) and game logos at `/config/www/lottery/<game>.png`, then reference them as `/local/lottery/<game>.png` with the `add_game` service.

## Selling
Pick game(s) (several can be selected at once) → draw date → bet type → type the number → amount (keypad or preset .25/.50/…) → **Add to ticket**. Tap a line to edit it, ✕ to delete. **Send & Print** saves the ticket and opens a receipt with a Code 39 barcode.
Physical keyboard works too (digits, Backspace, Tab = switch field, Enter = add).
Scanner: the scan box accepts the barcode. Winning ticket → asks to pay; otherwise its lines are loaded for replay. Buttons: Replay last, Último ticket, Copia number, Cancel, Redeem, Print resultado, Print report, Quick pick.

## Back office (admin users)
Open **Back office** in the panel menu (Home Assistant admin users only - retailers on a normal user only see Sell). It has six tabs:

| Tab | What you can do |
|---|---|
| **Games & schedule** | Per game: name, color, logo, when sales open, cut-off, draw time, draw weekdays, allowed bet types, show/hide on the sell screen. Edit bet type labels, payouts and on/off. Add games. |
| **Branding & message** | Lottery name + logo; the LED-style scrolling message (text, speed, color, on/off). |
| **Ticket design** | Font, size, paper width (48/58/72/80 mm), alignment, header/footer text, show/hide logo, name, retailer, date, bold total, **barcode** and **QR code** (size + optional prefix). Live preview and *Print test ticket*. |
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

## Known limits (v0.6)
Cut-off uses HA local time. A ticket becomes payable once all its draws are settled. Receipts print via the browser print dialog (use kiosk-printing for thermal printers). Data stored in `.storage/lottery_pos.data`; back it up.
