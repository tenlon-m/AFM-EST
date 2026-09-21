# AFM-EST 银河麒麟系统部署指南

## 目录

1. [系统要求](#系统要求)
2. [部署准备](#部署准备)
3. [安装步骤](#安装步骤)
4. [配置说明](#配置说明)
5. [运行程序](#运行程序)
6. [常见问题](#常见问题)

---

## 系统要求

### 操作系统
- **银河麒麟系统 V10 SP1**（版本号2403）
- 或其他基于Linux的操作系统

### 硬件要求
- **CPU**: 双核及以上
- **内存**: 4GB及以上
- **磁盘**: 至少1GB可用空间（用于索引文件）

### 软件要求
- **Python**: 3.7及以上版本
- **pip**: Python包管理器

---

## 部署准备

### 步骤1：在外网机器上准备离线安装包

**1.1 下载依赖包**

在有网络连接的机器上执行：

```bash
# 克隆或下载AFM-EST源码
git clone [项目地址]
cd wjssdb-qt6

# 下载所有依赖包（针对银河麒麟系统）
python3 download_offline_packages.py
```

这将创建 `offline_packages` 目录，包含所有需要的依赖包。

**1.2 打包文件**

```bash
# 打包源码和依赖包
tar -czf afm-est-kylin.tar.gz \
    src/ \
    config/ \
    resources/ \
    requirements-kylin.txt \
    offline_packages/ \
    check_environment.py \
    install_offline.sh \
    AFM-EST.py
```

### 步骤2：传输文件到内网银河麒麟系统

使用U盘、内网文件共享或其他方式，将 `afm-est-kylin.tar.gz` 传输到银河麒麟系统。

---

## 安装步骤

### 步骤1：解压文件

```bash
# 解压安装包
tar -xzf afm-est-kylin.tar.gz

# 进入目录
cd wjssdb-qt6
```

### 步骤2：检查环境

```bash
# 运行环境检查脚本
python3 check_environment.py
```

检查结果应显示：
- ✓ Python版本符合要求
- ✓ pip已安装
- 其他检查项...

### 步骤3：安装依赖

**方式一：使用自动安装脚本**

```bash
# 添加执行权限
chmod +x install_offline.sh

# 运行安装脚本
./install_offline.sh
```

**方式二：手动安装**

```bash
# 安装依赖包
pip3 install --no-index \
    --find-links=./offline_packages \
    -r requirements-kylin.txt
```

### 步骤4：验证安装

```bash
# 再次运行环境检查
python3 check_environment.py
```

所有检查项应显示 ✓ 通过。

---

## 配置说明

### 配置文件位置

银河麒麟系统上，配置文件位于：
- **配置目录**: `~/.config/AFM-EST/`
- **数据目录**: `~/.local/share/AFM-EST/`
- **缓存目录**: `~/.cache/AFM-EST/`
- **索引目录**: `~/.local/share/AFM-EST/index/`

### 首次运行配置

首次运行时，程序会自动：
1. 创建必要的目录
2. 生成默认配置文件
3. 提示构建搜索索引

### 自定义配置

编辑配置文件：

```bash
# 编辑主配置文件
nano ~/.config/AFM-EST/config.yaml
```

---

## 运行程序

### 方式一：直接运行

```bash
# 进入程序目录
cd wjssdb-qt6

# 运行程序
python3 src/AFM-EST.py
```

### 方式二：创建桌面快捷方式

```bash
# 创建桌面文件
cat > ~/.local/share/applications/afm-est.desktop << EOF
[Desktop Entry]
Version=1.0
Name=AFM-EST 文件管理器
Comment=高级文件管理器
Exec=python3 /path/to/wjssdb-qt6/src/AFM-EST.py
Icon=/path/to/wjssdb-qt6/resources/icon.png
Terminal=false
Type=Application
Categories=Utility;FileManager;
EOF

# 添加执行权限
chmod +x ~/.local/share/applications/afm-est.desktop
```

### 方式三：创建命令行别名

```bash
# 添加到 ~/.bashrc
echo 'alias afm-est="python3 /path/to/wjssdb-qt6/src/AFM-EST.py"' >> ~/.bashrc

# 使配置生效
source ~/.bashrc

# 运行
afm-est
```

---

## 常见问题

### Q1: 提示"Python版本不符合要求"

**A**: 安装Python 3.7及以上版本：

```bash
# 银河麒麟系统通常使用apt或yum
sudo apt-get install python3.9
# 或
sudo yum install python39
```

### Q2: 提示"依赖包安装失败"

**A**: 检查以下几点：
1. 确认 `offline_packages` 目录存在且不为空
2. 确认有足够的磁盘空间
3. 确认有写入权限

```bash
# 检查目录
ls -la offline_packages/

# 检查磁盘空间
df -h

# 使用sudo安装（如需要）
sudo pip3 install --no-index --find-links=./offline_packages -r requirements-kylin.txt
```

### Q3: 提示"无法连接到X服务器"

**A**: 设置DISPLAY环境变量：

```bash
# 本地运行
export DISPLAY=:0

# 远程运行（需要X11转发）
ssh -X user@host
```

### Q4: 程序启动但界面不显示

**A**: 检查图形环境：

```bash
# 检查Qt平台插件
echo $QT_QPA_PLATFORM

# 如果为空，设置默认值
export QT_QPA_PLATFORM=xcb
```

### Q5: 搜索索引构建失败

**A**: 检查磁盘权限和空间：

```bash
# 检查索引目录权限
ls -la ~/.local/share/AFM-EST/index/

# 检查磁盘空间
df -h ~/.local/share/
```

### Q6: 文件预览功能不可用

**A**: 安装文档处理依赖：

```bash
# 确认依赖已安装
python3 -c "import docx; print('python-docx OK')"
python3 -c "import openpyxl; print('openpyxl OK')"
python3 -c "import pptx; print('python-pptx OK')"
```

### Q7: 如何更新程序

**A**: 重新下载并解压新版本：

```bash
# 备份配置
cp -r ~/.config/AFM-EST ~/afm-est-config-backup

# 解压新版本
tar -xzf afm-est-kylin-new.tar.gz

# 恢复配置（如需要）
cp -r ~/afm-est-config-backup/* ~/.config/AFM-EST/
```

### Q8: 如何完全卸载

**A**: 删除程序和配置：

```bash
# 删除程序目录
rm -rf /path/to/wjssdb-qt6

# 删除配置和数据
rm -rf ~/.config/AFM-EST
rm -rf ~/.local/share/AFM-EST
rm -rf ~/.cache/AFM-EST

# 卸载Python依赖（可选）
pip3 uninstall -y -r requirements-kylin.txt
```

---

## 技术支持

如遇到其他问题，请：

1. 查看日志文件：`~/.local/share/AFM-EST/logs/`
2. 运行环境检查：`python3 check_environment.py`
3. 联系技术支持团队

---

**版本**: v1.0  
**更新日期**: 2026-06-17  
**适用系统**: 银河麒麟V10 SP1 (2403)