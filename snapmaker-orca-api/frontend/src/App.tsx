import { useEffect, useMemo, useState } from 'react';
import { Button, Card, Divider, Empty, Space, Spin, Typography, message } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { slicerApi } from './api/slicer';
import { ModelUpload } from './components/ModelUpload';
import { PresetPicker } from './components/PresetPicker';
import { SettingsTabs } from './components/SettingsTabs';
import { GcodeViewer } from './components/GcodeViewer';
import { JobStatusPanel } from './components/JobStatusPanel';
import type { Upload } from './types';

export default function App() {
  const [upload, setUpload] = useState<Upload | undefined>();
  const [printer, setPrinter] = useState<string | undefined>();
  const [filament, setFilament] = useState<string | undefined>();
  const [process, setProcess] = useState<string | undefined>();
  const [overrides, setOverrides] = useState<Record<string, unknown>>({});
  const [jobId, setJobId] = useState<string | undefined>();
  const [starting, setStarting] = useState(false);

  const health = useQuery({ queryKey: ['health'], queryFn: slicerApi.health });
  const catalog = useQuery({ queryKey: ['catalog'], queryFn: slicerApi.catalog });

  const printerVals = useQuery({
    queryKey: ['preset-values', 'printer', printer],
    queryFn: () => slicerApi.presetValues('printer', printer!),
    enabled: !!printer,
  });
  const filamentVals = useQuery({
    queryKey: ['preset-values', 'filament', filament],
    queryFn: () => slicerApi.presetValues('filament', filament!),
    enabled: !!filament,
  });
  const processVals = useQuery({
    queryKey: ['preset-values', 'process', process],
    queryFn: () => slicerApi.presetValues('process', process!),
    enabled: !!process,
  });

  const mergedPresetValues = useMemo(() => ({
    ...(printerVals.data?.values ?? {}),
    ...(filamentVals.data?.values ?? {}),
    ...(processVals.data?.values ?? {}),
  }), [printerVals.data, filamentVals.data, processVals.data]);

  const job = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => slicerApi.getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === 'pending' || s === 'running' ? 1500 : false;
    },
  });

  const preview = useQuery({
    queryKey: ['preview', jobId],
    queryFn: () => slicerApi.getPreview(jobId!),
    enabled: !!jobId && job.data?.status === 'succeeded',
  });

  // Reset preview when starting a new job
  useEffect(() => {
    if (job.data?.status === 'failed') {
      message.error(job.data.error ?? 'Slice failed');
    }
  }, [job.data?.status, job.data?.error]);

  async function startSlice() {
    if (!upload) {
      message.warning('Upload a model first.');
      return;
    }
    setStarting(true);
    try {
      const j = await slicerApi.startSlice({
        upload_id: upload.id,
        printer_preset: printer,
        filament_preset: filament,
        process_preset: process,
        overrides,
      });
      setJobId(j.id);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      message.error(`Slice failed to start: ${msg}`);
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <Typography.Title level={4} style={{ marginTop: 0 }}>
          Snapmaker Orca
        </Typography.Title>
        {!health.isLoading && health.data && !health.data.slicer_present && (
          <div style={{ marginBottom: 12, color: '#ff7875', fontSize: 12 }}>
            Slicer not found at <code>{health.data.slicer_bin}</code>. Set <code>SO_SLICER_BIN</code>.
          </div>
        )}
        {health.data?.slicer_version && (
          <div style={{ fontSize: 11, color: '#888', marginBottom: 8 }}>
            {health.data.slicer_version}
          </div>
        )}

        <Card size="small" title="1. Model" style={{ marginBottom: 12 }}>
          <ModelUpload onUploaded={setUpload} current={upload} />
        </Card>

        <Card size="small" title="2. Presets" style={{ marginBottom: 12 }}>
          <div className="preset-row"><span>Printer</span>
            <PresetPicker kind="printer" value={printer} onChange={setPrinter} /></div>
          <div className="preset-row"><span>Filament</span>
            <PresetPicker kind="filament" value={filament} onChange={setFilament} /></div>
          <div className="preset-row"><span>Process</span>
            <PresetPicker kind="process" value={process} onChange={setProcess} /></div>
        </Card>

        <Card
          size="small"
          title="3. Settings (overrides on top of preset)"
          extra={
            Object.keys(overrides).length > 0 && (
              <Button size="small" type="link" onClick={() => setOverrides({})}>
                Reset all
              </Button>
            )
          }
          style={{ marginBottom: 12 }}
        >
          {catalog.isLoading || !catalog.data ? <Spin /> : (
            <SettingsTabs
              catalog={catalog.data}
              overrides={overrides}
              presetValues={mergedPresetValues}
              onOverrideChange={(k, v) =>
                setOverrides((prev) => ({ ...prev, [k]: v }))}
              onOverrideClear={(k) =>
                setOverrides((prev) => {
                  const next = { ...prev };
                  delete next[k];
                  return next;
                })}
            />
          )}
        </Card>

        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button
            type="primary"
            block
            loading={starting || job.data?.status === 'running' || job.data?.status === 'pending'}
            disabled={!upload}
            onClick={startSlice}
          >
            Slice
          </Button>
        </Space>

        {jobId && job.data && (
          <>
            <Divider />
            <Card size="small" title="Job">
              <JobStatusPanel job={job.data} />
              {job.data.status === 'succeeded' && (
                <Space style={{ marginTop: 8 }}>
                  <Button size="small" href={slicerApi.gcodeUrl(jobId)}>Download G-code</Button>
                </Space>
              )}
            </Card>
          </>
        )}
      </aside>

      <main className="app-main">
        {preview.data ? (
          <GcodeViewer preview={preview.data} />
        ) : (
          <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}>
            <Empty
              description={
                job.data?.status === 'running' ? 'Slicing…' :
                  job.data?.status === 'failed' ? 'Slicing failed; see job details.' :
                    upload ? 'Press Slice to generate G-code and preview.' :
                      'Upload a model to begin.'
              }
            />
          </div>
        )}
      </main>
    </div>
  );
}
