#!/bin/bash
# 测试 Web UI 停止时的清理功能

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "测试 Web UI 停止清理功能"
echo "========================================"
echo ""

# 1. 检查停止命令的帮助信息
echo "1. 检查停止命令帮助信息..."
if uvx --from . qcc web stop --help 2>&1 | grep -q "keep-proxy"; then
    echo -e "${GREEN}✓${NC} --keep-proxy 选项存在"
else
    echo "✗ --keep-proxy 选项不存在"
    exit 1
fi

if uvx --from . qcc web stop --help 2>&1 | grep -q "keep-config"; then
    echo -e "${GREEN}✓${NC} --keep-config 选项存在"
else
    echo "✗ --keep-config 选项不存在"
    exit 1
fi

echo ""
echo "2. 检查 claude_config_manager 导入..."
python3 -c "
try:
    from fastcc.web.routers.claude_config import claude_config_manager
    print('${GREEN}✓${NC} claude_config_manager 导入成功')
except Exception as e:
    print(f'✗ 导入失败: {e}')
    exit(1)
"

echo ""
echo "3. 检查 ProxyServer 导入..."
python3 -c "
try:
    from fastcc.proxy.server import ProxyServer
    print('${GREEN}✓${NC} ProxyServer 导入成功')
except Exception as e:
    print(f'✗ 导入失败: {e}')
    exit(1)
"

echo ""
echo "========================================"
echo -e "${GREEN}所有检查通过！${NC}"
echo "========================================"
echo ""
echo "功能说明："
echo ""
echo "默认行为（uvx qcc web stop）："
echo "  1. 停止 Web UI 服务"
echo "  2. 停止代理服务（如果在运行）"
echo "  3. 还原 Claude Code 配置（如果已应用）"
echo ""
echo "保持代理运行："
echo "  uvx qcc web stop --keep-proxy"
echo ""
echo "保持配置不还原："
echo "  uvx qcc web stop --keep-config"
echo ""
echo "保持所有："
echo "  uvx qcc web stop --keep-proxy --keep-config"
echo ""
