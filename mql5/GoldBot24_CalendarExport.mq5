//+------------------------------------------------------------------+
//| GoldBot24_CalendarExport.mq5                                     |
//| ส่งออกปฏิทินเศรษฐกิจ USD (MetaQuotes) ย้อนหลัง → MQL5\Files       |
//| ใช้ Backtest แผนเข้าไม้ตามข่าว (คาด / ก่อน / จริง)                  |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input datetime InpFrom = D'2023.01.01 00:00';

string Num(const bool has, const double v)
  {
   return has ? DoubleToString(v, 6) : "";
  }

void OnStart()
  {
   MqlCalendarValue vals[];
   datetime to = TimeTradeServer() + 14 * 86400;
   if(!CalendarValueHistory(vals, InpFrom, to, NULL, "USD"))
     {
      PrintFormat("GoldBot24: CalendarValueHistory ล้มเหลว error %d", GetLastError());
      return;
     }
   int h = FileOpen("goldbot24_calendar_usd.csv", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
     {
      PrintFormat("GoldBot24: เปิดไฟล์ไม่ได้ error %d", GetLastError());
      return;
     }
   FileWriteString(h, "time_server\tevent_id\tcode\tname\timportance\tunit\tmultiplier\tdigits\tactual\tforecast\tprev\trevised_prev\n");
   int n = 0;
   for(int i = 0; i < ArraySize(vals); i++)
     {
      MqlCalendarEvent ev;
      if(!CalendarEventById(vals[i].event_id, ev))
         continue;
      if(ev.importance < CALENDAR_IMPORTANCE_MODERATE)
         continue;
      string name = ev.name;
      StringReplace(name, "\t", " ");
      FileWriteString(h, StringFormat("%s\t%I64u\t%s\t%s\t%d\t%d\t%d\t%d\t%s\t%s\t%s\t%s\n",
                      TimeToString(vals[i].time, TIME_DATE | TIME_SECONDS), ev.id, ev.event_code, name,
                      (int)ev.importance, (int)ev.unit, (int)ev.multiplier, (int)ev.digits,
                      Num(vals[i].HasActualValue(), vals[i].GetActualValue()),
                      Num(vals[i].HasForecastValue(), vals[i].GetForecastValue()),
                      Num(vals[i].HasPreviousValue(), vals[i].GetPreviousValue()),
                      Num(vals[i].HasRevisedValue(), vals[i].GetRevisedValue())));
      n++;
     }
   FileClose(h);
   PrintFormat("GoldBot24: ส่งออกข่าว USD %d รายการ → MQL5\Files\goldbot24_calendar_usd.csv", n);
   Alert(StringFormat("GoldBot24: ส่งออกปฏิทินข่าว USD เรียบร้อย %d รายการ", n));
  }
//+------------------------------------------------------------------+
