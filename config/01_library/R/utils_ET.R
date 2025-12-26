

# B) 共通ヘルパー関数 ----
## B-1. 欠損値対策(最大)：全て欠損値の場合にはmaxでNAを返す ----
max_na <- function(x) if (all(is.na(x))) NA_real_ else max(x, na.rm = TRUE)



