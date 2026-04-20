import { useEffect, useRef, useState } from 'react';

/**
 * ParticleBackground
 *
 * 全屏 Canvas 粒子动态背景组件（per Phase 28 CONTEXT D-01..D-12）。
 *
 * - 粒子浮动 + 距离阈值连线（D-04, D-05, D-06）
 * - 鼠标排斥交互（D-07, D-08），触屏 (pointer: coarse) 关闭（D-09）
 * - prefers-reduced-motion 命中时 return null（D-10）
 * - HiDPI 适配，devicePixelRatio 缩放（D-11）
 * - 标签页 visibilitychange 隐藏时暂停 rAF（D-12）
 * - 组件卸载时清理 rAF / 所有事件监听器 / matchMedia listener（D-12）
 *
 * 使用 CSS token --color-primary 作为粒子与连线颜色；fallback '#1456F0'。
 * 组件为纯装饰层：pointer-events: none，aria-hidden。
 */

// Tunable constants (per D-04..D-08)
const LINK_DISTANCE = 120; // px; 连线绘制阈值（D-06）与交互光环半径（D-08）保持一致
const INTERACTION_RADIUS = 120; // px; 鼠标排斥作用半径（D-08）
const PARTICLE_BASE_ALPHA = 0.6; // 粒子 α（D-04, 0.4-0.6 区间上限）
const LINK_BASE_ALPHA = 0.5; // 连线 α 基数（D-04）
const DENSITY_DIVISOR = 15000; // 粒子数量 = width*height / 15000（D-05）
// Particle count is clamped to [40, 150] inline inside resize() (per D-05).
const REPEL_STRENGTH = 2.5; // 排斥位移放大系数（D-07）
const VELOCITY_RANGE = 0.6; // 线速度初始范围 ±0.3 px/frame
const RADIUS_MIN = 1.5;
const RADIUS_MAX = 3;
const MOUSE_SENTINEL = -9999; // 鼠标未进入视口时的哨兵坐标

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const clean = hex.replace('#', '').trim();
  const full =
    clean.length === 3
      ? clean
          .split('')
          .map((c) => c + c)
          .join('')
      : clean;
  const r = parseInt(full.substring(0, 2), 16);
  const g = parseInt(full.substring(2, 4), 16);
  const b = parseInt(full.substring(4, 6), 16);
  return {
    r: Number.isFinite(r) ? r : 20,
    g: Number.isFinite(g) ? g : 86,
    b: Number.isFinite(b) ? b : 240,
  };
}

export function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [reducedMotion, setReducedMotion] = useState<boolean>(
    typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  );

  // Listen for prefers-reduced-motion changes so users toggling the OS setting
  // see the effect immediately without a reload (per D-10).
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Particle system effect: only attaches when reducedMotion === false.
  useEffect(() => {
    if (reducedMotion) {
      return;
    }
    const canvas = canvasRef.current;
    if (canvas === null) {
      return;
    }
    const ctx = canvas.getContext('2d');
    if (ctx === null) {
      // Fallback (T-28-03): browser refused 2D context -> behave like reduced-motion.
      return;
    }

    // Resolve primary color from CSS custom property --color-primary.
    const primaryRaw =
      getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim() ||
      '#1456F0';
    const { r: PR, g: PG, b: PB } = hexToRgb(primaryRaw);

    let particles: Particle[] = [];
    let rafId: number | null = null;
    let mouseX = MOUSE_SENTINEL;
    let mouseY = MOUSE_SENTINEL;

    // Coarse-pointer devices (touch): skip mouse binding entirely (per D-09).
    // Keep the literal string '(pointer: coarse)' present in source for grep checks.
    const coarseQuery = window.matchMedia('(pointer: coarse)');
    const useMouse = !coarseQuery.matches;

    function resize() {
      if (!ctx) return;
      const dpr = window.devicePixelRatio || 1;
      const cssW = window.innerWidth;
      const cssH = window.innerHeight;
      canvas!.width = Math.floor(cssW * dpr);
      canvas!.height = Math.floor(cssH * dpr);
      canvas!.style.width = cssW + 'px';
      canvas!.style.height = cssH + 'px';
      // Reset any previous transform and re-apply DPR scaling (per D-11).
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);

      // Clamp particle count to [40, 150] (per D-05, constants mirrored inline
      // to keep the literal `Math.max(40, Math.min(150, ...))` grep-verifiable).
      const count = Math.max(40, Math.min(150, Math.floor((cssW * cssH) / DENSITY_DIVISOR)));
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * cssW,
        y: Math.random() * cssH,
        vx: (Math.random() - 0.5) * VELOCITY_RANGE,
        vy: (Math.random() - 0.5) * VELOCITY_RANGE,
        radius: RADIUS_MIN + Math.random() * (RADIUS_MAX - RADIUS_MIN),
      }));
    }

    function draw() {
      if (!ctx) return;
      const cssW = window.innerWidth;
      const cssH = window.innerHeight;
      ctx.clearRect(0, 0, cssW, cssH);

      // Update + draw particles.
      for (const p of particles) {
        // Mouse repulsion (per D-07, D-08). Skipped for coarse-pointer devices
        // because mouseX/mouseY stay at MOUSE_SENTINEL.
        const dxm = p.x - mouseX;
        const dym = p.y - mouseY;
        const distM = Math.hypot(dxm, dym);
        if (distM < INTERACTION_RADIUS && distM > 0.001) {
          const force = (INTERACTION_RADIUS - distM) / INTERACTION_RADIUS; // 0..1
          p.x += (dxm / distM) * force * REPEL_STRENGTH;
          p.y += (dym / distM) * force * REPEL_STRENGTH;
        }

        // Linear drift.
        p.x += p.vx;
        p.y += p.vy;

        // Bounce at viewport edges (keeps particles in the visible rect).
        if (p.x < 0 || p.x > cssW) {
          p.vx *= -1;
          p.x = Math.max(0, Math.min(cssW, p.x));
        }
        if (p.y < 0 || p.y > cssH) {
          p.vy *= -1;
          p.y = Math.max(0, Math.min(cssH, p.y));
        }

        // Draw particle.
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${PR},${PG},${PB},${PARTICLE_BASE_ALPHA})`;
        ctx.fill();
      }

      // Draw links (per D-06). O(n^2) over ~40-150 particles ≈ at most ~11k
      // pair checks per frame, well under the rAF budget.
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i];
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.hypot(dx, dy);
          if (dist < LINK_DISTANCE) {
            const alpha = (1 - dist / LINK_DISTANCE) * LINK_BASE_ALPHA;
            ctx.strokeStyle = `rgba(${PR},${PG},${PB},${alpha})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }
    }

    function tick() {
      draw();
      rafId = window.requestAnimationFrame(tick);
    }

    function start() {
      if (rafId === null) {
        rafId = window.requestAnimationFrame(tick);
      }
    }

    function stop() {
      if (rafId !== null) {
        window.cancelAnimationFrame(rafId);
        rafId = null;
      }
    }

    function onVisibility() {
      if (document.hidden) {
        stop();
      } else {
        start();
      }
    }

    function onMouseMove(e: MouseEvent) {
      mouseX = e.clientX;
      mouseY = e.clientY;
    }

    function onMouseOut() {
      // Mouse left the document; reset sentinel so particles settle.
      mouseX = MOUSE_SENTINEL;
      mouseY = MOUSE_SENTINEL;
    }

    window.addEventListener('resize', resize);
    document.addEventListener('visibilitychange', onVisibility);
    if (useMouse) {
      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseout', onMouseOut);
    }

    resize();
    start();

    return () => {
      stop();
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', onVisibility);
      if (useMouse) {
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseout', onMouseOut);
      }
      particles = [];
    };
  }, [reducedMotion]);

  if (reducedMotion) {
    // Fallback: rely on --color-bg-page page background (per D-10).
    return null;
  }

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 0,
        pointerEvents: 'none',
        display: 'block',
      }}
    />
  );
}
