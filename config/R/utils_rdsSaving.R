
## B-5. 保存_data_checkpoint ----
save_checkpoint <- function(data, stage, prefix) {
  # ステージごとの保存ディレクトリ
  dir_path <- file.path(root, "03_data_checkpoint", stage)
  if (!dir.exists(dir_path)) dir.create(dir_path, recursive = TRUE)
  
  # 日付スタンプ（例: 2025-09-14 → 20250914）
  stamp <- format(Sys.Date(), "%Y%m%d")
  
  # ファイル名
  file_name <- paste0(prefix, "_", stamp, ".rds")
  file_path <- file.path(dir_path, file_name)
  
  # 保存
  saveRDS(data, file_path)
  message("Saved checkpoint: ", file_path)
}

## B-6. 保存_visualization_checkpoint ----
save_viz_checkpoint <- function(plot_obj, name, root = Sys.getenv("PROJECT_ROOT")) {
  dir_path <- file.path(root, "03_data_checkpoint/visualization")
  if (!dir.exists(dir_path)) dir.create(dir_path, recursive = TRUE)
  
  file_name <- paste0(name, "_", format(Sys.Date(), "%Y%m%d"), ".rds")
  file_path <- file.path(dir_path, file_name)
  
  saveRDS(plot_obj, file_path)
  message("Saved visualization checkpoint: ", file_path)
}

## B-7. 保存_picture_checkpoint ----
# 保存：PNG（outputs/figures/[subdir] 配下）
save_output_png <- function(
    plot_obj,
    name,
    subdir    = NULL,   # ★ サブフォルダ名を指定できるように
    root      = Sys.getenv("PROJECT_ROOT"),
    base_dir  = file.path("outputs", "figures"),
    width     = 12,     # inch
    height    = 14,     # inch
    dpi       = 300,
    units     = "in",
    bg        = "white",
    timestamp = TRUE,   # 日付(と時刻)をファイル名に付ける
    with_time = TRUE    # 日付に加えて時刻も付ける
) {
  stopifnot(!missing(plot_obj), !missing(name))
  
  # 出力先ディレクトリ
  out_dir <- if (!is.null(subdir)) {
    file.path(root, base_dir, subdir)
  } else {
    file.path(root, base_dir)
  }
  if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)
  
  # ファイル名
  safe_name <- gsub("[^A-Za-z0-9_-]+", "_", name)
  tag <- if (timestamp) {
    fmt <- if (with_time) "%Y%m%d_%H%M%S" else "%Y%m%d"
    paste0("_", format(Sys.time(), fmt))
  } else {
    ""
  }
  png_path <- file.path(out_dir, paste0(safe_name, tag, ".png"))
  
  # デバイスは ragg があれば優先
  dev <- if (requireNamespace("ragg", quietly = TRUE)) {
    ragg::agg_png                # 関数
  } else if (capabilities("cairo")) {
    grDevices::png               # 文字列の代わりに関数で統一
  } else {
    grDevices::png
  }
  
  
  ggplot2::ggsave(
    filename = png_path,
    plot     = plot_obj,
    width    = width,
    height   = height,
    dpi      = dpi,
    units    = units,
    bg       = bg,
    device   = dev
  )
  message("Saved PNG: ", png_path)
  return(png_path)
}

