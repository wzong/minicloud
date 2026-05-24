import { Progress, Tag, Statistic, Row, Col, Alert } from 'antd';
import type { Job } from '../types';

const STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  succeeded: 'success',
  failed: 'error',
  cancelled: 'warning',
};

function fmtTime(sec?: number | null) {
  if (sec == null) return '–';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return [h && `${h}h`, m && `${m}m`, `${s}s`].filter(Boolean).join(' ');
}

export function JobStatusPanel({ job }: { job: Job }) {
  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <Tag color={STATUS_COLORS[job.status]}>{job.status.toUpperCase()}</Tag>
        {job.stage && <Tag>{job.stage}</Tag>}
      </div>
      <Progress percent={job.progress} size="small" status={job.status === 'failed' ? 'exception' : undefined} />
      {job.error && <Alert type="error" message={job.error} style={{ marginTop: 8 }} />}
      {job.stats && (
        <Row gutter={8} style={{ marginTop: 12 }}>
          <Col span={12}><Statistic title="Print time" value={fmtTime(job.stats.estimated_print_time_sec)} valueStyle={{ fontSize: 14 }} /></Col>
          <Col span={12}><Statistic title="Filament" value={job.stats.filament_used_mm ? `${(job.stats.filament_used_mm / 1000).toFixed(2)} m` : '–'} valueStyle={{ fontSize: 14 }} /></Col>
          <Col span={12}><Statistic title="Filament wt." value={job.stats.filament_used_g ? `${job.stats.filament_used_g.toFixed(1)} g` : '–'} valueStyle={{ fontSize: 14 }} /></Col>
          <Col span={12}><Statistic title="Layers" value={job.stats.layer_count ?? '–'} valueStyle={{ fontSize: 14 }} /></Col>
        </Row>
      )}
    </div>
  );
}
