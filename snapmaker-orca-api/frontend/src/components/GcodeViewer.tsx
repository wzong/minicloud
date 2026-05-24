import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { Slider, Switch, Space, Tag } from 'antd';
import type { GcodePreview } from '../types';

const FEATURE_COLORS: Record<string, number> = {
  outer_wall: 0xff6b35,
  inner_wall: 0x2ec4b6,
  solid_infill: 0xe9c46a,
  infill: 0xf4a261,
  top_surface: 0xe76f51,
  bottom_surface: 0x9b5de5,
  support: 0x8d99ae,
  support_interface: 0x6c757d,
  bridge: 0x00bbf9,
  overhang: 0xfb5607,
  skirt: 0xadb5bd,
  brim: 0xced4da,
  gap_fill: 0xffd60a,
  wipe_tower: 0x7209b7,
  custom: 0xffffff,
  unknown: 0xa1a1aa,
};

interface Props {
  preview: GcodePreview;
}

class OrbitController {
  yaw = -Math.PI / 4;
  pitch = Math.PI / 6;
  distance = 300;
  target = new THREE.Vector3();
  private dragging = false;
  private lastX = 0;
  private lastY = 0;
  private panning = false;

  attach(canvas: HTMLCanvasElement) {
    canvas.addEventListener('pointerdown', this.onDown);
    canvas.addEventListener('pointerup', this.onUp);
    canvas.addEventListener('pointermove', this.onMove);
    canvas.addEventListener('wheel', this.onWheel, { passive: false });
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  detach(canvas: HTMLCanvasElement) {
    canvas.removeEventListener('pointerdown', this.onDown);
    canvas.removeEventListener('pointerup', this.onUp);
    canvas.removeEventListener('pointermove', this.onMove);
    canvas.removeEventListener('wheel', this.onWheel);
  }

  private onDown = (e: PointerEvent) => {
    this.dragging = true;
    this.panning = e.button === 2 || e.shiftKey;
    this.lastX = e.clientX;
    this.lastY = e.clientY;
    (e.target as HTMLCanvasElement).setPointerCapture(e.pointerId);
  };
  private onUp = (e: PointerEvent) => {
    this.dragging = false;
    (e.target as HTMLCanvasElement).releasePointerCapture(e.pointerId);
  };
  private onMove = (e: PointerEvent) => {
    if (!this.dragging) return;
    const dx = e.clientX - this.lastX;
    const dy = e.clientY - this.lastY;
    this.lastX = e.clientX;
    this.lastY = e.clientY;
    if (this.panning) {
      const f = this.distance * 0.002;
      const right = new THREE.Vector3(Math.cos(this.yaw), -Math.sin(this.yaw), 0);
      const up = new THREE.Vector3(0, 0, 1);
      this.target.addScaledVector(right, -dx * f);
      this.target.addScaledVector(up, dy * f);
    } else {
      this.yaw -= dx * 0.005;
      this.pitch = Math.min(Math.PI / 2 - 0.05, Math.max(-Math.PI / 2 + 0.05, this.pitch + dy * 0.005));
    }
  };
  private onWheel = (e: WheelEvent) => {
    e.preventDefault();
    this.distance *= e.deltaY > 0 ? 1.1 : 0.9;
    this.distance = Math.max(10, Math.min(5000, this.distance));
  };

  apply(camera: THREE.PerspectiveCamera) {
    const cp = Math.cos(this.pitch);
    const sp = Math.sin(this.pitch);
    const cy = Math.cos(this.yaw);
    const sy = Math.sin(this.yaw);
    const pos = new THREE.Vector3(
      this.target.x + this.distance * cp * cy,
      this.target.y + this.distance * cp * sy,
      this.target.z + this.distance * sp,
    );
    camera.position.copy(pos);
    camera.up.set(0, 0, 1);
    camera.lookAt(this.target);
  }
}

export function GcodeViewer({ preview }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [topLayer, setTopLayer] = useState(preview.layer_count - 1);
  const [showTravel, setShowTravel] = useState(false);

  // Build geometry per-feature for the currently visible layers
  const sceneRefs = useRef<{
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    renderer: THREE.WebGLRenderer;
    controller: OrbitController;
    layerGroups: THREE.Group[];
    travelGroups: THREE.Group[];
  } | null>(null);

  // Reverse feature_legend: id -> name
  const idToFeature = useMemo(() => {
    const m: Record<number, string> = {};
    for (const [name, id] of Object.entries(preview.feature_legend)) m[id] = name;
    return m;
  }, [preview.feature_legend]);

  // Build scene once per preview
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x141414);

    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 10000);
    const controller = new OrbitController();

    const [minX, minY, minZ, maxX, maxY, maxZ] = preview.bbox;
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const cz = (minZ + maxZ) / 2;
    const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 50);
    controller.target.set(cx, cy, cz);
    controller.distance = size * 2.5;
    controller.attach(canvas);

    // Bed grid
    const gridHelper = new THREE.GridHelper(Math.ceil(size * 1.6 / 10) * 10, Math.ceil(size / 5));
    gridHelper.rotateX(Math.PI / 2);
    gridHelper.position.set(cx, cy, minZ);
    (gridHelper.material as THREE.Material).opacity = 0.25;
    (gridHelper.material as THREE.Material).transparent = true;
    scene.add(gridHelper);
    // Axes
    const axes = new THREE.AxesHelper(size * 0.4);
    axes.position.set(minX, minY, minZ);
    scene.add(axes);

    // Build a Group per layer; each layer contains one LineSegments per feature.
    const layerGroups: THREE.Group[] = [];
    const travelGroups: THREE.Group[] = [];

    for (const layer of preview.layers) {
      const lg = new THREE.Group();
      const tg = new THREE.Group();

      // Bucket extrude segments by feature id
      const byFeature = new Map<number, number[]>();
      for (let i = 0; i < layer.feature_ids.length; i++) {
        const fid = layer.feature_ids[i];
        const off = i * 6;
        let arr = byFeature.get(fid);
        if (!arr) { arr = []; byFeature.set(fid, arr); }
        arr.push(
          layer.extrude_segments[off], layer.extrude_segments[off + 1], layer.extrude_segments[off + 2],
          layer.extrude_segments[off + 3], layer.extrude_segments[off + 4], layer.extrude_segments[off + 5],
        );
      }

      for (const [fid, arr] of byFeature) {
        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3));
        const name = idToFeature[fid] ?? 'unknown';
        const color = FEATURE_COLORS[name] ?? 0xffffff;
        const mat = new THREE.LineBasicMaterial({ color });
        lg.add(new THREE.LineSegments(geo, mat));
      }

      if (layer.travel_segments.length) {
        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.Float32BufferAttribute(layer.travel_segments, 3));
        const mat = new THREE.LineDashedMaterial({ color: 0x666666, dashSize: 1, gapSize: 1 });
        const seg = new THREE.LineSegments(geo, mat);
        seg.computeLineDistances();
        tg.add(seg);
      }

      scene.add(lg);
      scene.add(tg);
      layerGroups.push(lg);
      travelGroups.push(tg);
    }

    sceneRefs.current = { scene, camera, renderer, controller, layerGroups, travelGroups };

    let raf = 0;
    const resize = () => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / Math.max(1, h);
      camera.updateProjectionMatrix();
    };
    const tick = () => {
      controller.apply(camera);
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();
    tick();

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      controller.detach(canvas);
      for (const g of layerGroups) {
        g.traverse((o) => {
          if (o instanceof THREE.Line || o instanceof THREE.LineSegments) {
            o.geometry.dispose();
            (o.material as THREE.Material).dispose();
          }
        });
      }
      renderer.dispose();
      sceneRefs.current = null;
    };
  }, [preview, idToFeature]);

  // Apply visibility when top layer / travel toggle changes
  useEffect(() => {
    const s = sceneRefs.current;
    if (!s) return;
    for (let i = 0; i < s.layerGroups.length; i++) {
      s.layerGroups[i].visible = i <= topLayer;
      s.travelGroups[i].visible = showTravel && i <= topLayer;
    }
  }, [topLayer, showTravel, preview.layer_count]);

  const usedFeatures = useMemo(() => {
    const set = new Set<number>();
    for (const l of preview.layers) for (const id of l.feature_ids) set.add(id);
    return Array.from(set).map((id) => idToFeature[id] ?? 'unknown');
  }, [preview, idToFeature]);

  return (
    <>
      <canvas ref={canvasRef} className="viewer-canvas" />
      <div className="viewer-overlay">
        <div style={{ fontSize: 13, marginBottom: 8 }}>
          <strong>{preview.layer_count}</strong> layers ·
          {' '}<strong>{Math.round(preview.total_extruded_mm)}</strong> mm extruded ·
          {' '}<strong>{Math.round(preview.total_travel_mm)}</strong> mm travel
        </div>
        <Space wrap size={2}>
          {usedFeatures.map((name) => (
            <span key={name} className="legend-chip">
              <span className="legend-swatch" style={{
                background: `#${(FEATURE_COLORS[name] ?? 0xffffff).toString(16).padStart(6, '0')}`,
              }} />
              {name}
            </span>
          ))}
        </Space>
        <div style={{ marginTop: 8 }}>
          <Switch size="small" checked={showTravel} onChange={setShowTravel} /> {' '}
          <Tag>Show travel</Tag>
        </div>
      </div>
      <div className="viewer-controls">
        <div style={{ fontSize: 11, color: '#aaa' }}>L{topLayer + 1}</div>
        <Slider
          vertical
          min={0}
          max={Math.max(0, preview.layer_count - 1)}
          value={topLayer}
          onChange={(v) => setTopLayer(v as number)}
          tooltip={{ formatter: (v) => `Layer ${(v ?? 0) + 1} · Z=${preview.layers[v ?? 0]?.z.toFixed(2)}` }}
          style={{ height: '100%' }}
        />
      </div>
    </>
  );
}
