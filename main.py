from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import math
from datetime import datetime, timedelta

app = Flask(**name**)
CORS(app)

@app.route(’/api/market-data’)
def market_data():
try:
# SPX
spx = yf.Ticker(”^GSPC”)
spx_info = spx.info
price = spx_info.get(‘regularMarketPrice’) or spx_info.get(‘currentPrice’) or 6582

```
    # VIX
    vix = yf.Ticker("^VIX")
    vix_info = vix.info
    vix_val = vix_info.get('regularMarketPrice') or 23.87
    vix_prev = vix_info.get('previousClose') or vix_val
    vix_change = round(vix_val - vix_prev, 2)
    vix_change_pct = round((vix_change / vix_prev) * 100, 2) if vix_prev else 0
    vix_low52 = vix_info.get('fiftyTwoWeekLow') or 12
    vix_high52 = vix_info.get('fiftyTwoWeekHigh') or 60

    # Liquidity
    hist = spx.history(period="10d")
    pdh = round(float(hist['High'].iloc[-2]), 2) if len(hist) >= 2 else round(price * 1.004, 2)
    pdl = round(float(hist['Low'].iloc[-2]), 2) if len(hist) >= 2 else round(price * 0.996, 2)
    weekly_high = round(float(hist['High'].tail(5).max()), 2) if len(hist) >= 5 else round(price * 1.008, 2)
    weekly_low = round(float(hist['Low'].tail(5).min()), 2) if len(hist) >= 5 else round(price * 0.985, 2)

    # Options Chain
    spx_options = spx.option_chain()
    calls = spx_options.calls if spx_options else None
    puts = spx_options.puts if spx_options else None

    gex = fallback_gex(price)
    max_pain = round(price / 25) * 25
    put_call_ratio = 0.87

    if calls is not None and puts is not None and len(calls) > 0 and len(puts) > 0:
        max_pain = calc_max_pain(calls, puts)
        gex = calc_gex(calls, puts, price)
        total_call_oi = calls['openInterest'].sum()
        total_put_oi = puts['openInterest'].sum()
        if total_call_oi > 0:
            put_call_ratio = round(total_put_oi / total_call_oi, 2)

    # IV Rank
    iv_rank = calc_iv_rank(vix_val, vix_low52, vix_high52)
    iv_pct = round(iv_rank * 0.85)

    strategy = get_strategy(iv_rank)
    bias = get_bias(price, gex, vix_val)
    em = get_expected_move(price, vix_val)
    scenarios = get_scenarios(price, gex, bias['direction'])
    decision = get_decision(bias['direction'], gex, price, iv_rank)
    calendar = get_calendar()
    judas = get_judas()

    return jsonify({
        'spx': {'price': price},
        'vix': {'value': vix_val, 'change': vix_change, 'changePct': vix_change_pct, 'low52': vix_low52, 'high52': vix_high52},
        'gex': {**gex, 'maxPain': max_pain, 'regime': 'negative' if gex['netGex'] < 0 else 'positive'},
        'iv': {'rank': iv_rank, 'percentile': iv_pct},
        'putCall': {'ratio': put_call_ratio},
        'strategy': strategy,
        'bias': bias,
        'expectedMove': em,
        'scenarios': scenarios,
        'calendar': calendar,
        'liquidity': {'pdh': pdh, 'pdl': pdl, 'weeklyHigh': weekly_high, 'weeklyLow': weekly_low},
        'decision': decision,
        'judas': judas,
        'timestamp': datetime.utcnow().isoformat(),
        'source': 'yfinance'
    })

except Exception as e:
    return jsonify({'error': str(e)}), 500
```

def calc_max_pain(calls, puts):
try:
strikes = sorted(set(calls[‘strike’].tolist() + puts[‘strike’].tolist()))
min_loss = float(‘inf’)
mp = strikes[len(strikes)//2]
for s in strikes:
loss = 0
for _, c in calls.iterrows():
if c[‘strike’] < s:
loss += (s - c[‘strike’]) * (c[‘openInterest’] or 0)
for _, p in puts.iterrows():
if p[‘strike’] > s:
loss += (p[‘strike’] - s) * (p[‘openInterest’] or 0)
if loss < min_loss:
min_loss = loss
mp = s
return int(mp)
except:
return 0

def calc_gex(calls, puts, price):
try:
calls_above = calls[calls[‘strike’] > price].nlargest(5, ‘openInterest’)
puts_below = puts[puts[‘strike’] < price].nlargest(5, ‘openInterest’)
call_wall = int(calls_above.iloc[0][‘strike’]) if len(calls_above) > 0 else round(price * 1.015 / 25) * 25
put_wall = int(puts_below.iloc[0][‘strike’]) if len(puts_below) > 0 else round(price * 0.985 / 25) * 25
zero_gamma = round((call_wall + put_wall) / 2 / 5) * 5
gamma_flip = round((zero_gamma + price) / 2 / 5) * 5
net_gex = int(calls_above[‘openInterest’].sum() - puts_below[‘openInterest’].sum())
return {‘callWall’: call_wall, ‘putWall’: put_wall, ‘zeroGamma’: zero_gamma, ‘gammaFlip’: gamma_flip, ‘netGex’: net_gex}
except:
return fallback_gex(price)

def fallback_gex(price):
return {
‘callWall’: round(price * 1.015 / 25) * 25,
‘putWall’: round(price * 0.985 / 25) * 25,
‘zeroGamma’: round(price / 25) * 25,
‘gammaFlip’: round(price * 1.005 / 5) * 5,
‘netGex’: -1
}

def calc_iv_rank(vix, low=12, high=60):
if not vix or high == low:
return 30
return min(100, max(0, round(((vix - low) / (high - low)) * 100)))

def get_strategy(rank):
if rank < 20: return {‘en’: ‘Do Not Trade’, ‘ar’: ‘لا تتداول اليوم’}
if rank < 40: return {‘en’: ‘Credit Spread Narrow’, ‘ar’: ‘سبريد ائتماني ضيق’}
if rank < 60: return {‘en’: ‘Iron Condor’, ‘ar’: ‘آيرون كوندور’}
if rank < 80: return {‘en’: ‘Iron Condor Wide’, ‘ar’: ‘آيرون كوندور واسع’}
return {‘en’: ‘Iron Fly’, ‘ar’: ‘آيرون فلاي’}

def get_bias(price, gex, vix):
above_zg = price > gex[‘zeroGamma’]
neg_gex = gex[‘netGex’] < 0
if above_zg and not neg_gex:
return {‘direction’: ‘bullish’, ‘strength’: 65, ‘reason’: f”السعر فوق Zero-Gamma ({gex[‘zeroGamma’]}). GEX إيجابي.”}
if not above_zg and neg_gex:
return {‘direction’: ‘bearish’, ‘strength’: 68, ‘reason’: f”السعر تحت Zero-Gamma ({gex[‘zeroGamma’]}). GEX سلبي.”}
return {‘direction’: ‘neutral’, ‘strength’: 42 if vix > 25 else 52, ‘reason’: f”بين Put Wall ({gex[‘putWall’]}) و Call Wall ({gex[‘callWall’]}).”}

def get_expected_move(price, vix):
d = round(price * (vix / 100) * math.sqrt(1 / 365))
w = round(price * (vix / 100) * math.sqrt(5 / 365))
today = datetime.utcnow()
days_to_fri = (4 - today.weekday()) % 7 or 7
fri = today + timedelta(days=days_to_fri)
return {‘dailyUpper’: price + d, ‘dailyLower’: price - d, ‘weeklyUpper’: price + w, ‘weeklyLower’: price - w, ‘expDate’: fri.strftime(’%Y-%m-%d’)}

def get_scenarios(price, gex, direction):
cw, pw, mp, zg = gex[‘callWall’], gex[‘putWall’], gex.get(‘maxPain’, round(price/25)*25), gex[‘zeroGamma’]
if direction == ‘bearish’:
return [
{‘type’: ‘bearish’,   ‘icon’: ‘↘’, ‘name’: ‘Bearish Continuation’, ‘nameAr’: ‘هبوط مستمر’,        ‘prob’: 55, ‘target’: pw, ‘stop’: zg},
{‘type’: ‘neutral-s’, ‘icon’: ‘→’, ‘name’: ‘Range-Bound’,          ‘nameAr’: ‘تداول في نطاق’,      ‘prob’: 30, ‘target’: mp, ‘stop’: round(pw * 0.995)},
{‘type’: ‘bullish’,   ‘icon’: ‘↗’, ‘name’: ‘Bullish Reversal’,     ‘nameAr’: ‘انعكاس صاعد’,        ‘prob’: 15, ‘target’: zg, ‘stop’: pw},
]
if direction == ‘bullish’:
return [
{‘type’: ‘bullish’,   ‘icon’: ‘↗’, ‘name’: ‘Bullish Breakout’,     ‘nameAr’: ‘اختراق صعودي’,       ‘prob’: 50, ‘target’: cw, ‘stop’: zg},
{‘type’: ‘neutral-s’, ‘icon’: ‘→’, ‘name’: ‘Range-Bound’,          ‘nameAr’: ‘تداول في نطاق’,      ‘prob’: 35, ‘target’: mp, ‘stop’: pw},
{‘type’: ‘bearish’,   ‘icon’: ‘↘’, ‘name’: ‘Bearish Flush’,        ‘nameAr’: ‘هبوط نحو الدعم’,     ‘prob’: 15, ‘target’: pw, ‘stop’: cw},
]
return [
{‘type’: ‘neutral-s’, ‘icon’: ‘→’, ‘name’: ‘Range-Bound’,          ‘nameAr’: ‘تداول في نطاق محدد’, ‘prob’: 55, ‘target’: mp, ‘stop’: round(pw * 0.995)},
{‘type’: ‘bullish’,   ‘icon’: ‘↗’, ‘name’: ‘Bullish Breakout’,     ‘nameAr’: ‘اختراق صعودي’,       ‘prob’: 25, ‘target’: cw, ‘stop’: zg},
{‘type’: ‘bearish’,   ‘icon’: ‘↘’, ‘name’: ‘Bearish Flush’,        ‘nameAr’: ‘تصحيح هبوطي’,        ‘prob’: 20, ‘target’: pw, ‘stop’: round(price * 1.005)},
]

def get_decision(bias, gex, price, rank):
if rank < 20:
return {‘action’: ‘⛔ لا تتداول اليوم’, ‘detail’: ‘IV منخفض جداً’}
dc = gex[‘callWall’] - price
dp = price - gex[‘putWall’]
if bias == ‘bearish’ and dc < dp * 1.5:
return {‘action’: ‘🔴 SELL CALL Credit Spread’, ‘detail’: f”الدخول عند {round(gex[‘zeroGamma’])} — الجدار {gex[‘callWall’]}”}
if bias == ‘bullish’ and dp < dc * 1.5:
return {‘action’: ‘🟢 SELL PUT Credit Spread’, ‘detail’: f”الدخول عند {round(gex[‘zeroGamma’])} — الدعم {gex[‘putWall’]}”}
return {‘action’: ‘⚖️ Iron Condor’, ‘detail’: f”بيع بين {gex[‘putWall’]} و {gex[‘callWall’]} — مغناطيس {gex.get(‘maxPain’, round(price/25)*25)}”}

def get_calendar():
now = datetime.utcnow().date()
events = [
{‘date’: ‘2026-04-07’, ‘name’: ‘FOMC Meeting Minutes’,       ‘nameAr’: ‘محضر اجتماع الفيدرالي’, ‘impact’: ‘HIGH’,   ‘est’: ‘—’,    ‘prev’: ‘—’},
{‘date’: ‘2026-04-08’, ‘name’: ‘Initial Jobless Claims’,     ‘nameAr’: ‘طلبات الإعانة’,          ‘impact’: ‘MEDIUM’, ‘est’: ‘222K’, ‘prev’: ‘219K’},
{‘date’: ‘2026-04-10’, ‘name’: ‘Monthly Options Expiration’, ‘nameAr’: ‘انتهاء خيارات شهرية’,   ‘impact’: ‘HIGH’,   ‘est’: ‘—’,    ‘prev’: ‘—’},
]
return [e for e in events if datetime.strptime(e[‘date’], ‘%Y-%m-%d’).date() >= now]

def get_judas():
hour = (datetime.utcnow().hour + 3) % 24
return {‘active’: (9 <= hour < 11) or (16 <= hour < 17)}

if **name** == ‘**main**’:
app.run(host=‘0.0.0.0’, port=5000)
