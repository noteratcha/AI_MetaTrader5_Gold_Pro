# Unlimited Dynamic TP & Profit Lock
This rule outlines the standard for creating or modifying trading bots (like MT5 bots) with the "Unlimited Dynamic TP" feature, tailored for highly trending assets like BTC.

## Concept
Instead of placing a fixed Take Profit (TP) and forgetting it, we actively monitor the trade and dynamically extend the TP whenever the price approaches the target and AI confidence remains high. Concurrently, we pull the Stop Loss (SL) forward to lock in profit.

## Execution Rules
1. **Target Check:** Check if the price has moved $\ge$ 70% of the target distance.
   - For BUY: `target_dist = tp - price_open`. `current_gain = tick.bid - price_open`
   - For SELL: `target_dist = price_open - tp`. `current_gain = price_open - tick.ask`
2. **Confidence Check:** Confirm AI probability for the trend continuation is still strong (e.g. $\ge 0.55$).
3. **Extend TP:** Push the TP further away by `1.0 * ATR` (Average True Range).
4. **Lock SL:** Move SL slightly past the original entry or right behind the current price (e.g. `price - 1.0 * ATR` for BUY) to lock in profit in case of sudden reversal.
5. **No Limits:** Do not limit the number of extensions per trade. Recalculate target distance based on the **newly extended TP** every tick.
6. **Pairs:** This strategy is highly optimized for **BTCUSD** and should be the default approach when trading BTC.

## Code Example
```python
# BUY Example
target_dist = pos.tp - pos.price_open
current_gain = tick.bid - pos.price_open

if target_dist > 0 and current_gain >= (0.70 * target_dist) and prob[1] >= CONFIDENCE:
    new_tp = pos.tp + (atr_val * 1.0)
    lock_sl = max(pos.price_open + (atr_val * 0.2), tick.bid - (atr_val * 1.0))
    new_sl = max(pos.sl, lock_sl)
    if new_sl >= tick.bid:
        new_sl = tick.bid - (atr_val * 0.2)
    modify_position(pos, new_sl, new_tp)
```
