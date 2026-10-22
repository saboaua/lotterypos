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

## Sidebar menu & back office
The panel has an icon menu on the left: **Sell**, and (for Home Assistant admin users only) **Results**, **Reports** and **Setup**. Retailers using a non-admin HA user only see Sell.
**Setup → Branding**: set your lottery name and upload your logo (resized automatically); both show in the menu, top bar and on receipts. Setup also adds retailers and games (with optional game logo upload).

**Setup → Games & draw schedule**: for every game set the name, color, logo, when sales open, the cut-off, the draw time, **which weekdays it draws** (untick days with no draw; the sell screen then greys the game out on those dates), which bet types it accepts, and whether it is shown on the sell screen (hide a game without deleting it). **Bet types & payouts**: rename, change the payout multiplier or switch a bet type off. **Scrolling message**: the LED-style ticker above the sell screen - set the text, speed, color and on/off.

Results tab: enter results (1st/2nd/3rd, 4 digits) → tickets settle automatically. Settlement report per retailer (sales, commission, prizes, net). Add retailers (commission %) and games.

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

## Known limits (v0.5)
Cut-off uses HA local time. A ticket becomes payable once all its draws are settled. Receipts print via the browser print dialog (use kiosk-printing for thermal printers). Data stored in `.storage/lottery_pos.data`; back it up.
