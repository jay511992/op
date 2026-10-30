# 图像与颜色

`op::Op` 的这一组接口共 **23** 个。返回索引：[doc/api.md](../api.md)

> 通用约定（`long *ret` 的含义、坐标语义、线程安全、C API 命名映射）见 [索引页](../api.md#通用约定)。

## image and color（23）

- **`void Capture(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _In_ const wchar_t *file_name, _Out_ long *ret)`** → `void`
  抓取指定区域(x1, y1, x2, y2)的图像, 保存为file。 x2/y2 是右下角开区间: 实际宽 = x2-x1、高 = y2-y1, 所以 Capture(0, 0, 319, 239) 存下来的是 319x239 的图。

- **`void CmpColor(_In_ long x, _In_ long y, _In_ const wchar_t *color, _In_ double sim, _Out_ long *ret)`** → `void`
  比较指定坐标点(x,y)的颜色

- **`void FindColor(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _In_ const wchar_t *color, _In_ double sim, _In_ long dir, _Out_ long *x, _Out_ long *y, _Out_ long *ret)`** → `void`
  查找指定区域内的颜色

- **`void FindColorEx(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _In_ const wchar_t *color, _In_ double sim, _In_ long dir, _Out_ std::wstring &retstr)`** → `void`
  查找指定区域内的所有颜色

- **`void GetColorNum(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _In_ const wchar_t *color, _In_ double sim, _Out_ long *ret)`** → `void`
  查找指定区域内的所有颜色数量

- **`void FindMultiColor(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _In_ const wchar_t *first_color, _In_ const wchar_t *offset_color, _In_ double sim, _In_ long dir, _Out_ long *x, _Out_ long *y, _Out_ long *ret)`** → `void`
  根据指定的多点查找颜色坐标

- **`void FindMultiColorEx(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _In_ const wchar_t *first_color, _In_ const wchar_t *offset_color, _In_ double sim, _In_ long dir, _Out_ std::wstring &retstr)`** → `void`
  根据指定的多点查找所有颜色坐标

- **`void FindPic(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _In_ const wchar_t *files, _In_ const wchar_t *delta_color, _In_ double sim, _In_ long dir, _Out_ long *x, _Out_ long *y, _Out_ long *ret)`** → `void`
  在 `x1,y1,x2,y2` 区域内按 `files` 里的图片（`|` 分隔）逐个找，命中返回图片序号。**默认是灰度比较**：搜索图与模板都先转成灰度再按像素差累加，亮度相同、色相不同的目标分不开，同亮度不同色会误命中；要按颜色区分就先调 `SetFindPicColor(1)`。`sim` 是要求匹配上的比例（内部压缩成 `0.5 + sim/2`），`delta_color` 形如 `RRGGBB`，只有彩色模式和透明图模板才当逐通道容差用。

- **`void FindPicEx(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _In_ const wchar_t *files, _In_ const wchar_t *delta_color, _In_ double sim, _In_ long dir, _Out_ std::wstring &retstr)`** → `void`
  对 `files` 里的每张图都找一遍全部命中位置，出参形如 `"图片名,x,y|图片名,x,y"`，命中不到任何图时字符串里不含该项。比较方式同 `FindPic`，默认灰度，彩色要先 `SetFindPicColor(1)`。

- **`void FindPicExS(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _In_ const wchar_t *files, _In_ const wchar_t *delta_color, _In_ double sim, _In_ long dir, _Out_ std::wstring &retstr)`** → `void`
  同 `FindPicEx`，只是文件名用 `|` 分隔且出参不带图片名，形如 `"文件,x,y|文件,x,y"`。比较方式同 `FindPic`，默认灰度，彩色要先 `SetFindPicColor(1)`。

- **`void SetFindPicColor(_In_ long enable, _Out_ long *ret)`** → `void`
  设置 `FindPic` 系列的比较方式。默认 `0`：搜索图与模板都转成灰度后按像素差累加比较（旧行为）。传 `1` 改为彩色逐通道比较，`delta_color` 表示每通道允许偏差、`sim` 表示要求匹配上的像素比例（内部压缩成 `0.5 + sim/2`）；透明图模板无论这个开关如何都走彩色逐通道比较。彩色能分辨灰度相同但颜色不同的目标，代价是同一条 `sim` 在两种模式下尺度不同，切换后要重新标定。

- **`void FindColorBlock(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _In_ const wchar_t *color, _In_ double sim, _In_ long count, _In_ long height, _In_ long width, _Out_ long *x, _Out_ long *y, _Out_ long *ret)`** → `void`
  查找指定区域内的颜色块,颜色格式"RRGGBB-DRDGDB",注意,和按键的颜色格式相反

- **`void FindColorBlockEx(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _In_ const wchar_t *color, _In_ double sim, _In_ long count, _In_ long height, _In_ long width, _Out_ std::wstring &retstr)`** → `void`
  查找指定区域内的所有颜色块, 颜色格式"RRGGBB-DRDGDB", 注意, 和按键的颜色格式相反

- **`void GetColor(_In_ long x, _In_ long y, _Out_ std::wstring &ret)`** → `void`
  获取(x,y)的颜色

- **`void SetDisplayInput(_In_ const wchar_t *mode, _Out_ long *ret)`** → `void`
  设置图像输入方式，默认窗口截图

- **`void LoadPic(_In_ const wchar_t *file_name, _Out_ long *ret)`** → `void`
  把图片文件预加载进插件内部图片缓存，后续 `FindPic` 按名字命中缓存、不再读盘。

- **`void FreePic(_In_ const wchar_t *file_name, _Out_ long *ret)`** → `void`
  释放 `LoadPic` 预加载的缓存项。不调用也不影响正确性，只是占内存。

- **`void LoadMemPic(_In_ const wchar_t *file_name, _In_ void *data, _In_ long size, _Out_ long *ret)`** → `void`
  从内存加载要查找的图片

- **`void GetPicSize(_In_ const wchar_t *pic_name, _Out_ long *width, _Out_ long *height, _Out_ long *ret)`** → `void`
  获取指定图片的尺寸，如果指定的图片已经被加入缓存，则从缓存中获取信息.此接口也会把此图片加入缓存

- **`void GetScreenData(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _Out_ size_t *data, _Out_ long *ret)`** → `void`
  取指定区域的**原始像素**（BGRA 紧凑排列），不是 BMP。出参 `data` 指向内部复用缓冲，**下一次调用同一函数就会被覆盖**。

- **`void GetScreenDataBmp(_In_ long x1, _In_ long y1, _In_ long x2, _In_ long y2, _Out_ size_t *data, _Out_ long *size, _Out_ long *ret)`** → `void`
  取指定区域的画面并编码成 24 位 BMP 字节流。出参 `data` 同样指向内部复用缓冲。

- **`void GetScreenFrameInfo(_Out_ long *frame_id, _Out_ long *time)`** → `void`
  取当前帧的序号与时间戳（毫秒）。用于判断“画面有没有变”，比逐像素比较便宜。

- **`void MatchPicName(_In_ const wchar_t *pic_name, _Out_ std::wstring &retstr)`** → `void`
  按 BMP 命名规则补全图片名（相对 `SetPath` 设置的目录），返回实际要打开的文件名。

