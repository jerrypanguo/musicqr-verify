# 字体文件说明

## 📝 字体用途

本目录包含PDF生成所需的字体文件，用于创建优雅的乐谱验证二维码。

### 字体配置

#### 主标题字体（优先级顺序）
1. **Bodoni 72** (`fonts/Bodoni 72.ttc`) - 优雅的衬线字体
2. **Brush Script** (系统字体) - 手写风格字体
3. **Baskerville** (系统字体) - 经典衬线字体
4. **Times-Roman** (默认) - 系统默认字体

#### 验证码字体（优先级顺序）
1. **PT Serif** (系统字体) - 清晰的衬线字体
2. **Monaco** (系统字体) - 等宽字体
3. **Courier-Bold** (默认) - 系统默认等宽字体

## 🎨 字体效果

- **标题文字**: "SCAN TO VERIFY AUTHENTICITY."
- **验证码**: 12位大写字母数字组合

## 📁 文件列表

- `Bodoni 72.ttc` - 主要标题字体文件

## 🔧 字体安装

### 自动回退机制

代码中已实现字体自动回退机制：

```python
# 尝试注册Bodoni 72字体
try:
    pdfmetrics.registerFont(TTFont('Bodoni72', 'fonts/Bodoni 72.ttc'))
    title_font = 'Bodoni72'
except:
    # 回退到系统字体
    title_font = 'Times-Roman'
```

### 手动安装字体（可选）

如果需要在系统中安装字体：

#### macOS
```bash
# 复制到系统字体目录
cp "Bodoni 72.ttc" ~/Library/Fonts/
```

#### Windows
```bash
# 复制到系统字体目录
copy "Bodoni 72.ttc" C:\Windows\Fonts\
```

#### Linux
```bash
# 复制到用户字体目录
mkdir -p ~/.fonts
cp "Bodoni 72.ttc" ~/.fonts/
fc-cache -fv
```

## ⚠️ 注意事项

1. **字体版权**: 请确保字体文件的使用符合版权要求
2. **文件路径**: 代码中使用相对路径 `fonts/Bodoni 72.ttc`
3. **自动回退**: 即使字体文件缺失，程序也会自动使用系统默认字体
4. **跨平台**: 代码已考虑不同操作系统的字体差异

## 🚀 部署说明

### 本地开发
- 字体文件已包含在项目中，无需额外配置

### VPS部署
- 字体文件会随代码一起上传到VPS
- 如果VPS上缺少系统字体，会自动回退到默认字体

### 测试字体效果
```bash
# 运行生成器测试字体
cd client/
python generate_codes.py
```

生成的PDF会显示实际使用的字体：
```
🎨 标题字体：Bodoni72，验证码字体：PTSerif
```

## 📊 字体优先级说明

系统会按以下优先级选择字体：

### 标题字体选择逻辑
1. 尝试加载 `fonts/Bodoni 72.ttc`
2. 尝试加载系统的 Brush Script 字体
3. 尝试加载系统的 Baskerville 字体
4. 最终回退到 Times-Roman

### 验证码字体选择逻辑
1. 尝试加载系统的 PT Serif 字体
2. 尝试加载系统的 Monaco 字体
3. 最终回退到 Courier-Bold

这样的设计确保了：
- ✅ 最佳情况下使用优雅的自定义字体
- ✅ 在任何环境下都能正常生成PDF
- ✅ 跨平台兼容性良好
