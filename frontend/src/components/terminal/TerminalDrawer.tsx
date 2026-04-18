import React, { useEffect, useRef } from 'react';
import { Drawer, Grid } from 'antd';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

const { useBreakpoint } = Grid;

interface TerminalDrawerProps {
  open: boolean;
  onClose: () => void;
  wsPath: string | null;
  title: string;
}

const TerminalDrawer: React.FC<TerminalDrawerProps> = ({ open, onClose, wsPath, title }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const resizeObsRef = useRef<ResizeObserver | null>(null);
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  useEffect(() => {
    if (!open || !wsPath || !containerRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      fontSize: 13,
      theme: { background: '#1e1e1e' },
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(containerRef.current);
    requestAnimationFrame(() => {
      try {
        fit.fit();
      } catch {
        /* ignore */
      }
    });
    termRef.current = term;
    fitRef.current = fit;

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${window.location.host}${wsPath}`);
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    const encoder = new TextEncoder();

    ws.onopen = () => {
      try {
        ws.send(
          JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }),
        );
      } catch {
        /* ignore */
      }
    };

    ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        term.write(new Uint8Array(event.data));
      } else if (typeof event.data === 'string') {
        term.write(event.data);
      }
    };

    ws.onclose = () => {
      term.write('\r\n\x1b[31m[connection closed]\x1b[0m\r\n');
    };

    ws.onerror = () => {
      term.write('\r\n\x1b[31m[connection error]\x1b[0m\r\n');
    };

    const dataDisposable = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(encoder.encode(data));
      }
    });

    const resizeDisposable = term.onResize(({ cols, rows }) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols, rows }));
      }
    });

    const observer = new ResizeObserver(() => {
      try {
        fit.fit();
      } catch {
        /* ignore */
      }
    });
    observer.observe(containerRef.current);
    resizeObsRef.current = observer;

    return () => {
      dataDisposable.dispose();
      resizeDisposable.dispose();
      observer.disconnect();
      resizeObsRef.current = null;
      try {
        ws.close();
      } catch {
        /* ignore */
      }
      wsRef.current = null;
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
  }, [open, wsPath]);

  return (
    <Drawer
      title={title}
      placement="right"
      open={open}
      onClose={onClose}
      width={isMobile ? '100%' : 900}
      destroyOnClose
      styles={{ body: { padding: 0, background: '#1e1e1e' } }}
    >
      <div
        ref={containerRef}
        style={{ width: '100%', height: '100%', minHeight: 400, padding: 8 }}
      />
    </Drawer>
  );
};

export default TerminalDrawer;
