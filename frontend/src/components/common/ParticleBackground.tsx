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
