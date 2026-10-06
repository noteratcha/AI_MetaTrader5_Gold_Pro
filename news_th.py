"""
แปลชื่อข่าวเศรษฐกิจ (Economic Calendar) เป็นภาษาไทย — พจนานุกรมในเครื่อง ไม่ต้องใช้บริการแปลภายนอก
ลำดับการแปล: ชื่อเต็มที่รู้จัก → รูปแบบ "<ตำแหน่ง> <ชื่อ> Speaks" → แปลทีละวลี (คำนำหน้าประเทศ/ตัวชี้วัด/ช่วงเวลา)
"""
import re

# ชื่อข่าวที่พบบ่อย (แปลทั้งประโยค)
_EXACT = {
    "Non-Farm Employment Change": "การจ้างงานนอกภาคเกษตร (NFP)",
    "ADP Non-Farm Employment Change": "การจ้างงานภาคเอกชน ADP",
    "ADP Weekly Employment Change": "การจ้างงานรายสัปดาห์ ADP",
    "Unemployment Claims": "ผู้ขอรับสวัสดิการว่างงานรายสัปดาห์",
    "Continuing Jobless Claims": "ผู้ขอรับสวัสดิการว่างงานต่อเนื่อง",
    "Unemployment Rate": "อัตราการว่างงาน",
    "Average Hourly Earnings m/m": "ค่าจ้างรายชั่วโมงเฉลี่ย (เทียบเดือนก่อน)",
    "JOLTS Job Openings": "ตำแหน่งงานว่าง JOLTS",
    "Challenger Job Cuts y/y": "การเลิกจ้าง Challenger (เทียบปีก่อน)",
    "CPI m/m": "ดัชนีราคาผู้บริโภค CPI (เทียบเดือนก่อน)",
    "CPI y/y": "ดัชนีราคาผู้บริโภค CPI (เทียบปีก่อน)",
    "Core CPI m/m": "CPI พื้นฐาน (เทียบเดือนก่อน)",
    "PPI m/m": "ดัชนีราคาผู้ผลิต PPI (เทียบเดือนก่อน)",
    "Core PPI m/m": "PPI พื้นฐาน (เทียบเดือนก่อน)",
    "Core PCE Price Index m/m": "ดัชนีราคา PCE พื้นฐาน (เงินเฟ้อที่ Fed ใช้)",
    "Advance GDP q/q": "GDP ประมาณการเบื้องต้น (เทียบไตรมาสก่อน)",
    "Prelim GDP q/q": "GDP ฉบับปรับปรุง (เทียบไตรมาสก่อน)",
    "Final GDP q/q": "GDP ฉบับสุดท้าย (เทียบไตรมาสก่อน)",
    "Retail Sales m/m": "ยอดค้าปลีก (เทียบเดือนก่อน)",
    "Core Retail Sales m/m": "ยอดค้าปลีกพื้นฐาน (เทียบเดือนก่อน)",
    "ISM Services PMI": "ดัชนีภาคบริการ ISM",
    "ISM Manufacturing PMI": "ดัชนีภาคการผลิต ISM",
    "Final Services PMI": "ดัชนีภาคบริการ PMI ฉบับสุดท้าย",
    "Final Manufacturing PMI": "ดัชนีภาคการผลิต PMI ฉบับสุดท้าย",
    "Flash Services PMI": "ดัชนีภาคบริการ PMI เบื้องต้น",
    "Flash Manufacturing PMI": "ดัชนีภาคการผลิต PMI เบื้องต้น",
    "Prelim UoM Consumer Sentiment": "ความเชื่อมั่นผู้บริโภค UoM เบื้องต้น",
    "Revised UoM Consumer Sentiment": "ความเชื่อมั่นผู้บริโภค UoM ฉบับปรับปรุง",
    "Prelim UoM Inflation Expectations": "การคาดการณ์เงินเฟ้อ UoM เบื้องต้น",
    "Revised UoM Inflation Expectations": "การคาดการณ์เงินเฟ้อ UoM ฉบับปรับปรุง",
    "CB Consumer Confidence": "ความเชื่อมั่นผู้บริโภค Conference Board",
    "RCM/TIPP Economic Optimism": "ดัชนีความเชื่อมั่นเศรษฐกิจ RCM/TIPP",
    "Trade Balance": "ดุลการค้า",
    "Current Account": "ดุลบัญชีเดินสะพัด",
    "Consumer Credit m/m": "สินเชื่อผู้บริโภค (เทียบเดือนก่อน)",
    "Final Wholesale Inventories m/m": "สินค้าคงคลังค้าส่งฉบับสุดท้าย (เทียบเดือนก่อน)",
    "Crude Oil Inventories": "สต็อกน้ำมันดิบสหรัฐ",
    "Natural Gas Storage": "สต็อกก๊าซธรรมชาติ",
    "API Weekly Statistical Bulletin": "รายงานสต็อกน้ำมัน API รายสัปดาห์",
    "FOMC Meeting Minutes": "บันทึกการประชุม FOMC (Fed)",
    "FOMC Statement": "แถลงการณ์ FOMC (Fed)",
    "Federal Funds Rate": "อัตราดอกเบี้ยนโยบาย Fed",
    "FOMC Press Conference": "แถลงข่าวหลังประชุม FOMC",
    "Beige Book": "รายงาน Beige Book ของ Fed",
    "10-y Bond Auction": "ประมูลพันธบัตรอายุ 10 ปี",
    "30-y Bond Auction": "ประมูลพันธบัตรอายุ 30 ปี",
    "Bank Holiday": "วันหยุดธนาคาร",
    "Building Permits": "ใบอนุญาตก่อสร้าง",
    "Housing Starts": "การเริ่มสร้างบ้าน",
    "Existing Home Sales": "ยอดขายบ้านมือสอง",
    "New Home Sales": "ยอดขายบ้านใหม่",
    "Pending Home Sales m/m": "ยอดทำสัญญาขายบ้าน (เทียบเดือนก่อน)",
    "Durable Goods Orders m/m": "คำสั่งซื้อสินค้าคงทน (เทียบเดือนก่อน)",
    "Core Durable Goods Orders m/m": "คำสั่งซื้อสินค้าคงทนพื้นฐาน (เทียบเดือนก่อน)",
    "Industrial Production m/m": "ผลผลิตภาคอุตสาหกรรม (เทียบเดือนก่อน)",
    "Empire State Manufacturing Index": "ดัชนีภาคการผลิตนิวยอร์ก (Empire State)",
    "Philly Fed Manufacturing Index": "ดัชนีภาคการผลิตฟิลาเดลเฟีย",
    "Personal Spending m/m": "การใช้จ่ายส่วนบุคคล (เทียบเดือนก่อน)",
    "Personal Income m/m": "รายได้ส่วนบุคคล (เทียบเดือนก่อน)",
    "Employment Change": "การเปลี่ยนแปลงการจ้างงาน",
    "Consumer Confidence": "ความเชื่อมั่นผู้บริโภค",
    "Leading Indicators": "ดัชนีชี้นำเศรษฐกิจ",
    "Foreign Currency Reserves": "ทุนสำรองเงินตราต่างประเทศ",
    "Economy Watchers Sentiment": "ดัชนีความเชื่อมั่น Economy Watchers",
    "Household Spending y/y": "การใช้จ่ายครัวเรือน (เทียบปีก่อน)",
    "Average Cash Earnings y/y": "รายได้เงินสดเฉลี่ย (เทียบปีก่อน)",
    "ECB Monetary Policy Meeting Accounts": "บันทึกการประชุมนโยบายการเงิน ECB",
    "BOE Credit Conditions Survey": "ผลสำรวจภาวะสินเชื่อ BOE",
    "ECOFIN Meetings": "ประชุมรัฐมนตรีคลังสหภาพยุโรป (ECOFIN)",
    "Eurogroup Meetings": "ประชุมรัฐมนตรีคลังยูโรโซน (Eurogroup)",
    "OPEC-JMMC Meetings": "ประชุมคณะกรรมการ OPEC-JMMC",
    "GDT Price Index": "ดัชนีราคาผลิตภัณฑ์นม GDT",
    "Ivey PMI": "ดัชนี Ivey PMI (แคนาดา)",
    "Sentix Investor Confidence": "ความเชื่อมั่นนักลงทุน Sentix",
    "SECO Consumer Climate": "ความเชื่อมั่นผู้บริโภค SECO (สวิส)",
    "Westpac Consumer Sentiment": "ความเชื่อมั่นผู้บริโภค Westpac",
    "NZIER Business Confidence": "ความเชื่อมั่นภาคธุรกิจ NZIER",
    "RICS House Price Balance": "ดัชนีราคาบ้าน RICS",
    "MI Inflation Expectations": "การคาดการณ์เงินเฟ้อ MI",
    "MI Inflation Gauge m/m": "มาตรวัดเงินเฟ้อ MI (เทียบเดือนก่อน)",
    "Housing Equity Withdrawal q/q": "การถอนส่วนทุนบ้าน (เทียบไตรมาสก่อน)",
    "Prelim Machine Tool Orders y/y": "คำสั่งซื้อเครื่องจักรเบื้องต้น (เทียบปีก่อน)",
    "ANZ Commodity Prices m/m": "ราคาสินค้าโภคภัณฑ์ ANZ (เทียบเดือนก่อน)",
    "ANZ Job Advertisements m/m": "ประกาศรับสมัครงาน ANZ (เทียบเดือนก่อน)",
    "Lloyds HPI m/m": "ดัชนีราคาบ้าน Lloyds (เทียบเดือนก่อน)",
    "Construction PMI": "ดัชนีภาคก่อสร้าง PMI",
    "Services PMI": "ดัชนีภาคบริการ PMI",
    "Manufacturing PMI": "ดัชนีภาคการผลิต PMI",
}

_SPEAKERS = [
    (r"^FOMC Member (.+) Speaks$", "สมาชิก FOMC ({}) กล่าวสุนทรพจน์ — ท่าทีต่อดอกเบี้ยมีผลต่อดอลลาร์/ทอง"),
    (r"^Fed Chair (.+) (Speaks|Testifies)$", "ประธาน Fed ({}) แถลง — ผลกระทบสูงต่อทอง"),
    (r"^BOE Gov (.+) Speaks$", "ผู้ว่าการธนาคารกลางอังกฤษ ({}) กล่าวสุนทรพจน์"),
    (r"^BOJ Gov (.+) Speaks$", "ผู้ว่าการธนาคารกลางญี่ปุ่น ({}) กล่าวสุนทรพจน์"),
    (r"^ECB President (.+) Speaks$", "ประธาน ECB ({}) กล่าวสุนทรพจน์"),
    (r"^MPC Member (.+) Speaks$", "กรรมการนโยบายการเงิน BOE ({}) กล่าวสุนทรพจน์"),
    (r"^German Buba President (.+) Speaks$", "ประธานธนาคารกลางเยอรมนี ({}) กล่าวสุนทรพจน์"),
    (r"^Gov Board Member (.+) Speaks$", "กรรมการธนาคารกลาง ({}) กล่าวสุนทรพจน์"),
    (r"^(.+) Speaks$", "{} กล่าวสุนทรพจน์"),
]

_PREFIX = {
    "German": "เยอรมนี", "French": "ฝรั่งเศส", "Italian": "อิตาลี", "Spanish": "สเปน", "Swiss": "สวิส",
    "Chinese": "จีน", "Japanese": "ญี่ปุ่น", "Prelim": "เบื้องต้น", "Final": "ฉบับสุดท้าย", "Flash": "เบื้องต้น",
    "Revised": "ฉบับปรับปรุง", "Core": "พื้นฐาน",
}
_WORDS = [
    ("Gov Budget Balance", "ดุลงบประมาณรัฐบาล"), ("Industrial Production", "ผลผลิตภาคอุตสาหกรรม"),
    ("Factory Orders", "คำสั่งซื้อภาคโรงงาน"), ("Trade Balance", "ดุลการค้า"), ("Services PMI", "ดัชนีภาคบริการ PMI"),
    ("Manufacturing PMI", "ดัชนีภาคการผลิต PMI"), ("Retail Sales", "ยอดค้าปลีก"), ("Unemployment", "การว่างงาน"),
    ("Employment", "การจ้างงาน"), ("Inflation", "เงินเฟ้อ"), ("Consumer", "ผู้บริโภค"), ("Business", "ภาคธุรกิจ"),
    ("Confidence", "ความเชื่อมั่น"), ("Sentiment", "ความเชื่อมั่น"), ("Expectations", "การคาดการณ์"),
    ("Interest Rate", "อัตราดอกเบี้ย"), ("Rate Decision", "การตัดสินใจอัตราดอกเบี้ย"), ("Bond Auction", "ประมูลพันธบัตร"),
    ("Housing", "ที่อยู่อาศัย"), ("House Price", "ราคาบ้าน"), ("Minutes", "บันทึกการประชุม"), ("Meetings", "การประชุม"),
    ("Statement", "แถลงการณ์"), ("Press Conference", "แถลงข่าว"),
]
_PERIOD = {"m/m": "(เทียบเดือนก่อน)", "y/y": "(เทียบปีก่อน)", "q/q": "(เทียบไตรมาสก่อน)"}


def translate(title: str) -> str:
    """ชื่อข่าวภาษาไทย (ถ้าแปลไม่ได้คืนค่าว่าง)"""
    t = str(title or "").strip()
    if not t:
        return ""
    if t in _EXACT:
        return _EXACT[t]
    for pattern, tmpl in _SPEAKERS:
        m = re.match(pattern, t)
        if m:
            return tmpl.format(m.group(1))
    # แปลทีละส่วน: ช่วงเวลา (m/m) · คำนำหน้าประเทศ/ฉบับ · ตัวชี้วัด
    period = ""
    for k, v in _PERIOD.items():
        if t.endswith(" " + k):
            period, t = v, t[: -len(k) - 1]
    words = t.split(" ")
    pre = []
    while words and words[0] in _PREFIX:
        pre.append(_PREFIX[words.pop(0)])
    rest = " ".join(words)
    if rest in _EXACT:
        body = _EXACT[rest]
    else:
        body, hit = rest, False
        for en, th in _WORDS:
            if en in body:
                body, hit = body.replace(en, th), True
        if not hit and not pre:
            return ""
    country = [p for p in pre if p in ("เยอรมนี", "ฝรั่งเศส", "อิตาลี", "สเปน", "สวิส", "จีน", "ญี่ปุ่น")]
    other = [p for p in pre if p not in country]
    parts = [body] + other + ([f"({country[0]})"] if country else []) + ([period] if period else [])
    return " ".join(parts).strip()
