
# A) ロケール設定 ----
## A-1. 月略称の解釈を英語に（失敗しても無視）----
## Sys.setlocale("LC_TIME", "C")
## → R の「日付/時間のロケール」を C（英語環境、POSIX デフォルト） に切り替えます。
## これにより、as.Date() や lubridate::parse_date_time() が "Jan", "Feb", "Mar" といった英語の略月を正しく解釈できるようになります。
try(Sys.setlocale("LC_TIME", "C"), silent = TRUE)



