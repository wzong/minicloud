import { Upload, message, Tag } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { slicerApi } from '../api/slicer';
import type { Upload as UploadInfo } from '../types';

interface Props {
  onUploaded: (u: UploadInfo) => void;
  current?: UploadInfo;
}

export function ModelUpload({ onUploaded, current }: Props) {
  const [uploading, setUploading] = useState(false);

  return (
    <Upload.Dragger
      multiple={false}
      showUploadList={false}
      disabled={uploading}
      beforeUpload={async (file) => {
        setUploading(true);
        try {
          const u = await slicerApi.uploadModel(file as File);
          onUploaded(u);
          message.success(`Uploaded ${u.filename}`);
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : String(e);
          message.error(`Upload failed: ${msg}`);
        } finally {
          setUploading(false);
        }
        return false; // prevent AntD from doing its own POST
      }}
      style={{ padding: 12 }}
    >
      <p style={{ margin: 0 }}>
        <InboxOutlined style={{ fontSize: 24 }} />
      </p>
      <p style={{ margin: '4px 0', fontSize: 13 }}>
        {current ? <>Loaded: <Tag color="blue">{current.filename}</Tag></>
          : 'Drop .stl / .3mf / .obj here, or click to browse'}
      </p>
    </Upload.Dragger>
  );
}
