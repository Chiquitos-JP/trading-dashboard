## B-3. plot.helpers ----
### 基本パッケージ
### 共通オプション
### B-3-1. 文字列と数値の取扱い ----
# stringsAsFactors = FALSE → データフレームに文字列を入れたとき、自動で factor に変換しない。
# scipen = 999 → 科学的記法 (1e+06) を避けて、普通の数字 (1000000) で表示する。
# options(stringsAsFactors = FALSE, scipen = 999)
options(stringsAsFactors = FALSE, scipen = 999)

### B-3-2. Google Fonts ----
showtext::showtext_auto(enable = TRUE)
try(showtext::font_add_google("Roboto", "roboto"), silent = TRUE)
try(showtext::font_add_google("Noto Sans JP", "notojp"), silent = TRUE)

## B-4. 相対パスの設定_.Renvironで指定済みのデータを変数代入----
# root <- Sys.getenv("PROJECT_ROOT") # .Renvironで設定済み。



# donwload済みのフォントの確認
# names(grDevices::windowsFonts())
# install.packages("showtext")
# library(showtext)

# 方針 ----
# base themeを決定した後、個別プロジェクトの設定を上書き

# 現在 showtext に登録されているフォント一覧
# sysfonts::font_families()
# # 具体的にどのフォントが登録されているか
# sysfonts::font_files()

# A) Helper for plotting ----
# Brand Colorをきめてから
## A-1. Color ----
# col_profit <- "#1B9E77"
# col_loss   <- "#D95F02"
# col_gray   <- "gray50"
# 
# # ▼ テーマ
# theme_trade <- function() {
#   theme_minimal(base_family = "roboto") +
#     theme(
#       plot.title = element_text(face = "bold", size = 14),
#       plot.caption = element_text(size = 9, color = "gray40", hjust = 1)
#     )
# }
# （プロジェクト全体で使うなら）初期化時に
# ggplot2::theme_set(theme_trade())

## A-2. Title ---- 
## One-pager タイトル用（HTML書式対応） -----------------------------
### タイトル/サブタイトルのHTML文字列を作る（色・サイズ・太さを個別指定可）
# ===== Title helpers
library(rlang) # %||% 演算子を使うため
# デフォルトの書式（Roboto 前提。未登録なら自動で sans にフォールバック）
.title_defaults <- list(
  family_title    = "roboto",
  family_subtitle = "roboto",
  color_title     = "#222222",
  color_subtitle  = "gray35",
  size_title_pt   = 20,
  size_subtitle_pt= 9,
  weight_title    = 700,
  weight_subtitle = 400,
  line_height     = 1.05
)

# HTMLつきタイトル/サブタイトルを作る（素材作り）
make_title <- function(
    title,
    subtitle = NULL,
    family_title    = .title_defaults$family_title,
    family_subtitle = .title_defaults$family_subtitle,
    color_title     = .title_defaults$color_title,
    color_subtitle  = .title_defaults$color_subtitle,
    size_title_pt   = .title_defaults$size_title_pt,
    size_subtitle_pt= .title_defaults$size_subtitle_pt,
    weight_title    = .title_defaults$weight_title,
    weight_subtitle = .title_defaults$weight_subtitle,
    line_height     = .title_defaults$line_height
) {
  stopifnot(!missing(title))
  
  style_t <- sprintf(
    "font-family:%s; color:%s; font-size:%spt; font-weight:%s; line-height:%s;",
    family_title, color_title, size_title_pt, weight_title, line_height
  )
  style_s <- sprintf(
    "font-family:%s; color:%s; font-size:%spt; font-weight:%s; line-height:%s;",
    family_subtitle, color_subtitle, size_subtitle_pt, weight_subtitle, line_height
  )
  
  list(
    title    = paste0("<span style='", style_t, "'>", title, "</span>"),
    subtitle = if (!is.null(subtitle))
      paste0("<span style='", style_s, "'>", subtitle, "</span>")
    else NULL
  )
}

# タイトルを ggplot / patchwork に載せる（実装）
# - `hdr` には make_title() の戻り値（list）を渡すのが最短
# - もしくは title/subtitle を生文字で渡してもOK（内部で make_title を呼ぶ）
add_title <- function(
    p,
    hdr = NULL,
    title = NULL, subtitle = NULL,   # 生文字を受けてもOK
    hjust = 0,                       # 左寄せ
    margin_top = 8, margin_right = 8, margin_bottom = 6, margin_left = 8
) {
  has_ggtext <- requireNamespace("ggtext", quietly = TRUE)
  
  # hdr が無ければここで組み立て
  if (is.null(hdr)) {
    hdr <- make_title(
      title    = title %||% "",
      subtitle = subtitle
    )
  }
  
  # ggtext が無い環境では素の文字に落とす
  ttl <- if (has_ggtext) hdr$title else gsub("<[^>]+>", "", hdr$title)
  sub <- if (has_ggtext && !is.null(hdr$subtitle)) hdr$subtitle
  else if (!is.null(hdr$subtitle)) gsub("<[^>]+>", "", hdr$subtitle)
  else NULL
  
  title_el <- if (has_ggtext) ggtext::element_markdown(hjust = hjust, lineheight = 1.05)
  else ggplot2::element_text(hjust = hjust)
  subtitle_el <- if (has_ggtext) ggtext::element_markdown(hjust = hjust, lineheight = 1.05)
  else ggplot2::element_text(hjust = hjust)
  
  if (inherits(p, "patchwork")) {
    p + patchwork::plot_annotation(
      title = ttl,
      subtitle = sub,
      theme = ggplot2::theme(
        plot.title    = title_el,
        plot.subtitle = subtitle_el,
        plot.margin   = ggplot2::margin(margin_top, margin_right, margin_bottom, margin_left)
      )
    )
  } else {
    p +
      ggplot2::labs(title = ttl, subtitle = sub) +
      ggplot2::theme(
        plot.title    = title_el,
        plot.subtitle = subtitle_el,
        plot.margin   = ggplot2::margin(margin_top, margin_right, margin_bottom, margin_left)
      )
  }
}

## A-3. Key Insights Panel ----
# --- コメント追加用ブロック関数 ---
make_text_block <- function(text,
                            family = "roboto",
                            color = "gray20",
                            size_pt = 9,
                            hjust = 0,
                            vjust = 1,
                            lineheight = 1.2,
                            margin = NULL) {
  if (is.null(margin)) {
    margin <- ggplot2::margin(5, 12, 5, 12)
  }
  
  ggplot() +
    ggtext::geom_richtext(
      data = tibble::tibble(x = 0, y = 1, label = text),
      aes(x, y, label = label),
      hjust = hjust, vjust = vjust,
      label.colour = NA, fill = NA,
      family = family,
      size = size_pt / ggplot2::.pt,
      colour = color,
      lineheight = lineheight
    ) +
    coord_cartesian(xlim = c(0,1), ylim = c(0,1), expand = FALSE) +
    theme_void() +
    theme(plot.margin = margin)
}

## build_kv_lines(): key-value の一覧を HTML文字列にする
build_kv_lines <- function(kpis, label_bold = TRUE, between = "<br>") {
  lines <- purrr::map_chr(names(kpis), function(name) {
    value <- kpis[[name]]
    if (label_bold) {
      sprintf("<span style='font-weight:700'>%s:</span> %s", name, value)
    } else {
      sprintf("%s: %s", name, value)
    }
  })
  paste(lines, collapse = between)
}

# plot_helpers.R
make_key_insights_panel <- function(body_html,
                                    title = "Key Insights",
                                    family = "roboto",
                                    bg_fill = "#f3f3f3",
                                    title_color = "#222222",
                                    text_color  = "#222222") {
  title_html <- if (!is.null(title) && nzchar(title))
    sprintf("<span style='font-weight:700; color:%s'>%s</span><br>", title_color, title) else ""
  
  full_html <- paste0(title_html, body_html)
  
  ggplot() +
    annotate("rect", xmin = 0, xmax = 1, ymin = 0, ymax = 1,
             fill = bg_fill, colour = NA) +
    ggtext::geom_richtext(
      data = tibble::tibble(x = 0.02, y = 0.9, label = full_html),
      aes(x, y, label = label),
      hjust = 0, vjust = 1,
      label.colour = NA, fill = NA,
      family = family,
      size = 10 / .pt,
      color = text_color,
      lineheight = 1.15
    ) +
    coord_cartesian(xlim = c(0, 1), ylim = c(0, 1), expand = FALSE) +
    theme_void() +
    theme(plot.margin = margin(10, 12, 8, 12))
}

## A-4. Caption ---- 
.current_year <- function() format(Sys.Date(), "%Y")
.default_author <- function() paste0("Casual-Investment©", .current_year())
.default_source <- function() "Source: SBI, Rakuten"

# HTMLでスタイル込みのキャプション文字列を作成
make_caption <- function(
    author  = .default_author(),
    src     = .default_source(),
    color   = "gray40",  # 色
    size    = 10,        # pt
    italic  = TRUE,      # 斜体
    weight  = 400,       # 400: normal, 700: bold
    opacity = 0.9,       # 0〜1（透明度）
    family  = "roboto, 'Noto Sans JP', 'Noto Sans', sans-serif",  # ★ フォントを明示
    lineheight = 1
) {
  style <- sprintf(
    "color:%s; font-size:%spt; font-style:%s; font-weight:%s; opacity:%s;",
    color, size, if (italic) "italic" else "normal", weight, opacity
  )
  paste0("<span style='", style, "'>", author, " | ", src, "</span>")
}


# ggplot/patchwork の両方に "書式付きキャプション" を適用
add_caption <- function(
    p,
    author  = .default_author(),
    src     = .default_source(),
    color   = "gray40",
    size    = 10,
    italic  = TRUE,
    weight  = 400,
    opacity = 0.9,
    family  = "Arial",     # ★ フォールバック時にも使う
    hjust   = 1,     # 右寄せ
    vjust   = -0.2,  # 下方向の微調整
    margin_bottom = 8
) {
  cap_html   <- make_caption(author, src, color, size, italic, weight, opacity)
  has_ggtext <- requireNamespace("ggtext", quietly = TRUE)
  
  if (inherits(p, "patchwork")) {
    # ★ patchwork は plot_annotation(theme=...) に直接テーマを渡す
    if (has_ggtext) {
      p + patchwork::plot_annotation(
        caption = cap_html,
        theme = ggplot2::theme(
          plot.caption          = ggtext::element_markdown(hjust = hjust, vjust = vjust, lineheight = 1),
          plot.caption.position = "plot",
          plot.margin           = ggplot2::margin(t = 5, r = 5, b = margin_bottom, l = 5)
        )
      )
    } else {
      cap_plain <- gsub("<[^>]+>", "", cap_html)
      p + patchwork::plot_annotation(
        caption = cap_plain,
        theme = ggplot2::theme(
          plot.caption          = ggplot2::element_text(hjust = hjust, colour = color,
                                                        face = if (italic) "italic" else "plain",
                                                        size = size),
          plot.caption.position = "plot",
          plot.margin           = ggplot2::margin(t = 5, r = 5, b = margin_bottom, l = 5)
        )
      )
    }
  } else {
    # 単体 ggplot はこれでOK
    if (has_ggtext) {
      p + ggplot2::labs(caption = cap_html) +
        ggplot2::theme(
          plot.caption          = ggtext::element_markdown(hjust = hjust, vjust = vjust, lineheight = 1),
          plot.caption.position = "plot",
          plot.margin           = ggplot2::margin(t = 5, r = 5, b = margin_bottom, l = 5)
        )
    } else {
      cap_plain <- gsub("<[^>]+>", "", cap_html)
      p + ggplot2::labs(caption = cap_plain) +
        ggplot2::theme(
          plot.caption          = ggplot2::element_text(hjust = hjust, colour = color,
                                                        face = if (italic) "italic" else "plain",
                                                        size = size),
          plot.caption.position = "plot",
          plot.margin           = ggplot2::margin(t = 5, r = 5, b = margin_bottom, l = 5)
        )
    }
  }
}

# End) Loading Confirmation ----
# message("[No.4 plot_helpers.R loaded]")



