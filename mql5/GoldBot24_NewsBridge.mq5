//+------------------------------------------------------------------+
//| GoldBot24_NewsBridge.mq5                                         |
//| สะพานข่าวสำหรับแผน P11 · News (โปรแกรม Gold Bot 24)               |
//| - อ่านปฏิทินเศรษฐกิจ MetaQuotes ข่าว USD (ย้อนหลัง 1 วัน · ล่วงหน้า 2 วัน) |
//| - ตรวจค่าที่เปลี่ยนทุก 0.5 วินาที (CalendarValueLast) → เขียนไฟล์ทันที  |
//| - เขียน Common\Files\goldbot24_news_live.json (ใช้ร่วมทุก MT5)       |
//| - ไม่ส่งออเดอร์ · ไม่แก้ค่าใด ๆ ใน MT5                              |
//+------------------------------------------------------------------+
#property strict
#property description "Gold Bot 24 · News Bridge (P11) — อ่านปฏิทินข่าว USD ส่งให้โปรแกรม ไม่ส่งออเดอร์"

#define OUT_FILE "goldbot24_news_live.json"
#define TMP_FILE "goldbot24_news_live.tmp"

ulong    g_change = 0;
datetime g_last_write = 0;

string Num(const bool has, const double v)
  {
   return has ? DoubleToString(v, 6) : "null";
  }

void Dump()
  {
   MqlCalendarValue vals[];
   datetime now = TimeTradeServer();
   if(!CalendarValueHistory(vals, now - 2 * 86400, now + 3 * 86400, NULL, "USD"))
      return;
   int h = FileOpen(TMP_FILE, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE)
      return;
   FileWriteString(h, StringFormat("{\"v\":1,\"gmt\":%I64d,\"server\":%I64d,\"events\":[", (long)TimeGMT(), (long)TimeTradeServer()));
   bool first = true;
   for(int i = 0; i < ArraySize(vals); i++)
     {
      MqlCalendarEvent ev;
      if(!CalendarEventById(vals[i].event_id, ev) || ev.importance < CALENDAR_IMPORTANCE_MODERATE)
         continue;
      FileWriteString(h, StringFormat("%s{\"t\":\"%s\",\"code\":\"%s\",\"imp\":%d,\"a\":%s,\"f\":%s,\"p\":%s}",
                      first ? "" : ",", TimeToString(vals[i].time, TIME_DATE | TIME_SECONDS), ev.event_code, (int)ev.importance,
                      Num(vals[i].HasActualValue(), vals[i].GetActualValue()),
                      Num(vals[i].HasForecastValue(), vals[i].GetForecastValue()),
                      Num(vals[i].HasPreviousValue(), vals[i].GetPreviousValue())));
      first = false;
     }
   FileWriteString(h, "]}");
   FileClose(h);
   // เขียนไฟล์ชั่วคราวแล้วค่อยแทนที่ — โปรแกรมจะไม่อ่านเจอไฟล์ครึ่ง ๆ กลาง ๆ
   FileMove(TMP_FILE, FILE_COMMON, OUT_FILE, FILE_COMMON | FILE_REWRITE);
   g_last_write = TimeLocal();
  }

int OnInit()
  {
   MqlCalendarValue tmp[];
   CalendarValueLast(g_change, tmp, NULL, "USD");   // รับเลขการเปลี่ยนแปลงล่าสุด
   Dump();
   EventSetMillisecondTimer(500);
   Comment("Gold Bot 24 · News Bridge (P11) ทำงานอยู่ — ไม่ส่งออเดอร์");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
  }

void OnTimer()
  {
   MqlCalendarValue ch[];
   ulong id = g_change;
   bool changed = CalendarValueLast(id, ch, NULL, "USD") > 0;
   if(id != 0)
      g_change = id;
   if(changed || TimeLocal() - g_last_write >= 5)   // มีค่าใหม่ = เขียนทันที · ไม่งั้นเขียนทุก 5 วิ (สัญญาณว่า EA ยังทำงาน)
      Dump();
  }
//+------------------------------------------------------------------+
