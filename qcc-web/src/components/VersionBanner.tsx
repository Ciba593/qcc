import { useQuery } from '@tanstack/react-query';
import { Typography } from 'antd';
import { api } from '../api/client';
import './VersionBanner.css';

const { Text } = Typography;

export default function VersionBanner() {
  const { data: versionData } = useQuery({
    queryKey: ['system-version'],
    queryFn: api.system.version,
    refetchInterval: 60000, // 60秒刷新一次
  });

  if (!versionData || !(versionData as any).data) {
    return null;
  }

  const { version, features } = (versionData as any).data;

  // 构建滚动文本
  const scrollText = `QCC v${version} | ${features.join(' | ')}`;

  return (
    <div className="version-banner">
      <div className="version-banner-content">
        <Text className="version-banner-text">
          {scrollText}
        </Text>
        {/* 重复一次以实现无缝循环 */}
        <Text className="version-banner-text" aria-hidden="true">
          {scrollText}
        </Text>
      </div>
    </div>
  );
}
