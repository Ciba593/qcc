#!/bin/bash
# Web UI 一键启动功能测试脚本

set -e

echo "================================================"
echo "QCC Web UI 一键启动功能测试"
echo "================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数
PASSED=0
FAILED=0

# 测试函数
test_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    PASSED=$((PASSED + 1))
}

test_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    FAILED=$((FAILED + 1))
}

test_info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

echo "测试 1: 检查 CLI 文件是否存在"
if [ -f "fastcc/cli.py" ]; then
    test_pass "CLI 文件存在"
else
    test_fail "CLI 文件不存在"
    exit 1
fi

echo ""
echo "测试 2: 检查前端目录结构"
if [ -d "qcc-web" ]; then
    test_pass "前端目录存在"
else
    test_fail "前端目录不存在"
    exit 1
fi

if [ -f "qcc-web/vite.config.ts" ]; then
    test_pass "Vite 配置文件存在"
else
    test_fail "Vite 配置文件不存在"
fi

if [ -f "qcc-web/package.json" ]; then
    test_pass "package.json 存在"
else
    test_fail "package.json 不存在"
fi

echo ""
echo "测试 3: 检查 Vite 配置"
if grep -q "proxy" qcc-web/vite.config.ts; then
    test_pass "Vite 代理配置已添加"
else
    test_fail "Vite 代理配置缺失"
fi

if grep -q "target: 'http://127.0.0.1:8080'" qcc-web/vite.config.ts; then
    test_pass "代理目标地址正确"
else
    test_fail "代理目标地址不正确"
fi

echo ""
echo "测试 4: 检查 CLI 命令实现"
if grep -q "def start(host, port, dev, no_browser):" fastcc/cli.py; then
    test_pass "web start 命令存在"
else
    test_fail "web start 命令不存在"
fi

if grep -q "if dev:" fastcc/cli.py; then
    test_pass "开发模式分支存在"
else
    test_fail "开发模式分支不存在"
fi

if grep -q "vite_process = subprocess.Popen" fastcc/cli.py; then
    test_pass "Vite 进程启动代码存在"
else
    test_fail "Vite 进程启动代码不存在"
fi

if grep -q "'vite_pid':" fastcc/cli.py; then
    test_pass "Vite PID 记录代码存在"
else
    test_fail "Vite PID 记录代码不存在"
fi

echo ""
echo "测试 5: 检查文档"
if [ -f "docs/tasks/web-ui-dev-mode.md" ]; then
    test_pass "开发模式文档存在"
else
    test_fail "开发模式文档不存在"
fi

if [ -f "docs/tasks/web-ui-one-command-start.md" ]; then
    test_pass "功能实现文档存在"
else
    test_fail "功能实现文档不存在"
fi

if [ -f "docs/tasks/web-ui/快速开始.md" ]; then
    test_pass "快速开始文档存在"

    if grep -q "uvx qcc web start --dev" "docs/tasks/web-ui/快速开始.md"; then
        test_pass "文档包含开发模式命令"
    else
        test_fail "文档缺少开发模式命令"
    fi
else
    test_fail "快速开始文档不存在"
fi

echo ""
echo "测试 6: 检查前端依赖"
if [ -d "qcc-web/node_modules" ]; then
    test_pass "前端依赖已安装"
else
    test_info "前端依赖未安装（首次运行时会自动安装）"
fi

echo ""
echo "测试 7: 检查前端构建"
if [ -d "qcc-web/dist" ] && [ -f "qcc-web/dist/index.html" ]; then
    test_pass "前端已构建"
else
    test_info "前端未构建（首次运行生产模式时会自动构建）"
fi

echo ""
echo "测试 8: 语法检查"
test_info "检查 Python 语法..."
if python3 -m py_compile fastcc/cli.py 2>/dev/null; then
    test_pass "CLI Python 语法正确"
else
    test_fail "CLI Python 语法错误"
fi

echo ""
echo "================================================"
echo "测试总结"
echo "================================================"
echo -e "通过: ${GREEN}${PASSED}${NC}"
echo -e "失败: ${RED}${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}所有测试通过！✓${NC}"
    echo ""
    echo "可以使用以下命令测试实际运行："
    echo ""
    echo "  # 测试生产模式（需要较长时间首次构建）"
    echo "  uvx --from . qcc web start --no-browser"
    echo ""
    echo "  # 测试开发模式"
    echo "  uvx --from . qcc web start --dev"
    echo ""
    echo "  # 查看状态"
    echo "  uvx --from . qcc web status"
    echo ""
    echo "  # 停止服务"
    echo "  uvx --from . qcc web stop"
    echo ""
    exit 0
else
    echo -e "${RED}有 ${FAILED} 个测试失败！✗${NC}"
    exit 1
fi
