# 打包说明

## 方式一：使用 .spec 文件（推荐）

```bash
pyinstaller zhanlong.spec
```

产物在 `dist/斩龙/` 目录下，双击 `斩龙.exe` 运行。

### .spec 的优势
- 自动排除未使用的 epoch-99 和 int8 模型文件（节省约 22MB）
- 自动排除 torch、mediapipe 等未使用的大包
- EXE 名称直接叫"斩龙"
- 启用 UPX 压缩

## 方式二：命令行一行打包

```bash
pyinstaller --windowed --add-data "images;images" --add-data "model;model" --add-data "utils;utils" --icon "app_icon.ico" --name "斩龙" main.py
```

> ⚠️ 这种方式会把 model/ 下所有文件都打进去（包括未使用的模型），体积较大。

## 注意事项

- **必须在 Windows 上打包**（`--add-data` 分隔符为 `;`，且依赖 pywin32 等 Windows 包）
- 打包前确保已安装所有依赖：`pip install -r requirements.txt`
- 如需 UPX 压缩，请先安装 [UPX](https://upx.github.io/) 并确保在 PATH 中
