# 配置校验和回滚机制

## 📋 概述

实现完善的配置校验和回滚机制,确保配置的正确性和可恢复性。

**版本**: v1.0
**创建日期**: 2025-10-16
**相关文档**: claude-code-proxy-development-plan.md

---

## 🎯 核心功能

### 1. 配置校验 (Config Validation)

**目标**: 在应用配置前验证其正确性和完整性

#### 校验维度

```python
class ConfigValidator:
    """配置校验器"""

    def validate_all(self, config):
        """完整校验"""
        checks = [
            self.validate_structure(),      # 结构完整性
            self.validate_endpoints(),       # Endpoint 有效性
            self.validate_priorities(),      # 优先级一致性
            self.validate_policies(),        # 策略合理性
            self.validate_connectivity(),    # 连通性测试
        ]
        return all(checks)

    def validate_structure(self):
        """验证配置文件结构"""
        required_fields = ['version', 'profiles', 'proxy', 'health']
        # 检查必需字段是否存在

    def validate_endpoints(self):
        """验证所有 endpoint"""
        for profile in config['profiles']:
            for endpoint in profile['endpoints']:
                # 检查 URL 格式
                # 检查 API Key 格式
                # 检查参数范围

    def validate_connectivity(self):
        """连通性测试"""
        # 测试每个 endpoint 是否可��
        # 测试 API Key 是否有效
```

#### CLI 命令

```bash
# 验证当前配置
qcc config validate
# 输出:
#   ✅ 配置结构: 通过
#   ✅ Endpoint 有效性: 通过 (3/3)
#   ✅ 优先级一致性: 通过
#   ⚠️  连通性测试: 部分通过 (2/3)
#      - endpoint-3: 连接超时
#
#   建议: 检查 endpoint-3 的网络连接

# 验证特定配置
qcc config validate production

# 诊断配置问题
qcc config doctor
# 自动检测并给出修复建议
```

---

### 2. 配置版本管理

**目标**: 追踪配置变更历史,支持回滚

#### 数据结构

```json
{
  "config_version": "0.4.0",
  "current_snapshot_id": "snapshot-20251016-143000",
  "snapshots": [
    {
      "id": "snapshot-20251016-143000",
      "timestamp": "2025-10-16T14:30:00Z",
      "description": "添加 backup endpoint",
      "config_data": {...},
      "hash": "sha256:abc123...",
      "created_by": "user_action"
    },
    {
      "id": "snapshot-20251016-120000",
      "timestamp": "2025-10-16T12:00:00Z",
      "description": "初始配置",
      "config_data": {...},
      "hash": "sha256:def456..."
    }
  ],
  "max_snapshots": 50  // 最多保留 50 ��快照
}
```

#### 实现

```python
class ConfigSnapshotManager:
    """配置快照管理器"""

    def create_snapshot(self, description=""):
        """创建配置快照"""
        snapshot = {
            'id': f"snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'description': description,
            'config_data': self.get_current_config(),
            'hash': self.calculate_hash(),
            'created_by': 'user_action'
        }

        self.snapshots.append(snapshot)
        self.cleanup_old_snapshots()
        self.save()

        return snapshot['id']

    def rollback_to(self, snapshot_id):
        """回滚到指定快照"""
        snapshot = self.find_snapshot(snapshot_id)
        if not snapshot:
            raise ValueError(f"快照 {snapshot_id} 不存在")

        # 创建回滚前快照
        self.create_snapshot(f"回滚前快照 (回滚到 {snapshot_id})")

        # 验证快照配置
        if not self.validator.validate_all(snapshot['config_data']):
            raise ValidationError("快照配置验证失败")

        # 应用快照配置
        self.apply_config(snapshot['config_data'])
        self.current_snapshot_id = snapshot_id

    def compare_snapshots(self, id1, id2):
        """比较两个快照的差异"""
        snapshot1 = self.find_snapshot(id1)
        snapshot2 = self.find_snapshot(id2)

        return self.diff_configs(
            snapshot1['config_data'],
            snapshot2['config_data']
        )
```

---

### 3. 自动快照策略

**触发时机**:

1. **手动触发**: 用户执行 `qcc config snapshot`
2. **配置变更前**: 任何配置修改操作前自动创建
3. **故障转移前**: 执行故障转移前自动创建
4. **定时快照**: 每天自动创建 (可配置)

#### CLI 命令

```bash
# 创建快照
qcc config snapshot "升级到 v0.4.0 前的配置"
# ✅ 快照已创建: snapshot-20251016-143000

# 查看快照列表
qcc config snapshots
# 输出:
#   ID                           时间                  描述
#   snapshot-20251016-143000    2025-10-16 14:30:00   升级到 v0.4.0 前的配置
#   snapshot-20251016-120000    2025-10-16 12:00:00   故障转移前快照
#   snapshot-20251016-100000    2025-10-16 10:00:00   添加 backup endpoint

# 查看快照详情
qcc config snapshot-info snapshot-20251016-143000

# 比较快照
qcc config diff snapshot-20251016-120000 snapshot-20251016-143000
# 输出差异

# 回滚到指定快照
qcc config rollback snapshot-20251016-120000
# 确认: 是否回滚到 2025-10-16 12:00:00 的配置? (y/N): y
# ✅ 已回滚到快照 snapshot-20251016-120000
# ✅ 配置已恢复

# 回滚到上一个快照
qcc config rollback --last
```

---

### 4. 配置变更审计

**目标**: 记录所有配置变更,便于追踪和审计

#### 审计日志格式

```json
{
  "audit_logs": [
    {
      "id": "audit-20251016-143000",
      "timestamp": "2025-10-16T14:30:00Z",
      "action": "endpoint_add",
      "target": "production.endpoints",
      "details": {
        "added": {
          "id": "endpoint-3",
          "base_url": "https://backup.api.com"
        }
      },
      "user": "cli_user",
      "snapshot_before": "snapshot-20251016-120000",
      "snapshot_after": "snapshot-20251016-143000"
    }
  ]
}
```

#### CLI 命令

```bash
# 查看审计日志
qcc config audit
# 最近 20 条配置变更

qcc config audit --limit 100
# 最近 100 条

qcc config audit --action endpoint_add
# 筛选特定操作

qcc config audit --export audit.json
# 导出审计日志
```

---

## 🧪 测试用例

### 校验测试

```bash
# 测试无效配置被拒绝
uvx --from . qcc config validate tests/fixtures/invalid-config.json
# 预期: 返回错误并列出问题

# 测试有效配置通过
uvx --from . qcc config validate tests/fixtures/valid-config.json
# 预期: 所有检查通过
```

### 回滚测试

```bash
# 测试回滚功能
# 1. 创建初始快照
uvx --from . qcc config snapshot "初始状态"

# 2. 修改配置
uvx --from . qcc endpoint add production

# 3. 验证修改生效
uvx --from . qcc endpoint list production

# 4. 回滚
uvx --from . qcc config rollback --last

# 5. 验证已恢复
uvx --from . qcc endpoint list production
```

---

## 🎯 使用场景

### 场景 1: 配置升级前验证

```bash
# 1. 创建升级前快照
qcc config snapshot "升级到 v0.4.0 前"

# 2. 导入新配置
qcc config import new-config.json

# 3. 验证新配置
qcc config validate

# 4. 如果验证失败,回滚
qcc config rollback --last
```

### 场景 2: 故障恢复

```bash
# 当配置错误导致代理无法启动

# 1. 查看最近的工作快照
qcc config snapshots

# 2. 回滚到最后一个工作状态
qcc config rollback snapshot-20251016-120000

# 3. 验证配置
qcc config validate

# 4. 重启代理
qcc proxy restart
```

### 场景 3: 配置���计

```bash
# 追踪谁在什么时候修改了什么

# 查看审计日志
qcc config audit --limit 50

# 查看特定时间段
qcc config audit --from "2025-10-15" --to "2025-10-16"

# 导出审计报告
qcc config audit --export report.json
```

---

## 📊 监控告警

### 关键事件

1. **配置验证失败** - 立即通知
2. **配置回滚** - 记录日志
3. **快照数量超限** - 清理旧快照
4. **连通性测试失败** - 告警

---

## 🎯 最佳实践

1. **重要操作前快照** - 任何重大配置变更前手动创建快照
2. **定期验证** - 每天运行一次 `qcc config validate`
3. **保留关键快照** - 标记重要快照防止被自动清理
4. **审计日志归档** - 定期导出审计日志用于合规
5. **测试环境验证** - 在测试环境先验证新配置

---

**文档版本**: v1.0
**最后更新**: 2025-10-16
**作者**: QCC Development Team
