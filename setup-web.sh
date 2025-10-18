#!/bin/bash
# QCC Web UI 快速安装脚本

set -e

echo "========================================="
echo "🚀 QCC Web UI 安装脚本"
echo "========================================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请先安装 Python 3.9 或更高版本"
    exit 1
fi

echo "✅ Python 版本: $(python3 --version)"
echo ""

# 检查是否在项目目录
if [ ! -f "pyproject.toml" ]; then
    echo "❌ 错误: 请在 qcc 项目根目录运行此脚本"
    exit 1
fi

echo "📦 安装 QCC 及 Web 依赖..."
echo ""

# 安装包
python3 -m pip install -e '.[web]'

echo ""
echo "========================================="
echo "✅ 安装完成！"
echo "========================================="
echo ""
echo "现在可以使用以下命令启动 Web UI:"
echo ""
echo "  qcc web start"
echo ""
echo "或者:"
echo ""
echo "  python3 -m fastcc.cli web start"
echo ""
echo "访问地址: http://127.0.0.1:8080"
echo "API 文档: http://127.0.0.1:8080/api/docs"
echo ""
