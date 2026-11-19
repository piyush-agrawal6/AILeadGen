'use client';

import React, { useEffect, useRef } from 'react';

interface CubeConfig {
  id: number;
  size: number;
  depth: number;
  parallaxSpeed: number;
  animIndex: number;
  pos: { top?: string; bottom?: string; left?: string; right?: string };
  opacity?: number;
  hideOnMobile?: boolean;
}

// Well-placed, subtle floating 3D geometric elements for clean, minimal SaaS aesthetic
const AUTH_CUBES: CubeConfig[] = [
  { id: 1, size: 70, depth: 0.7, parallaxSpeed: -0.1, animIndex: 1, pos: { top: '16%', left: '4%' }, opacity: 0.85, hideOnMobile: true },
  { id: 2, size: 85, depth: 0.8, parallaxSpeed: -0.12, animIndex: 2, pos: { top: '20%', right: '5%' }, opacity: 0.9, hideOnMobile: true },
  { id: 3, size: 48, depth: 0.4, parallaxSpeed: 0.06, animIndex: 3, pos: { top: '56%', left: '5%' }, opacity: 0.65, hideOnMobile: true },
  { id: 4, size: 64, depth: 0.55, parallaxSpeed: 0.08, animIndex: 4, pos: { bottom: '16%', right: '5%' }, opacity: 0.75, hideOnMobile: false },
  { id: 5, size: 52, depth: 0.45, parallaxSpeed: -0.06, animIndex: 5, pos: { bottom: '12%', left: '6%' }, opacity: 0.7, hideOnMobile: true },
];

const LEGAL_CUBES: CubeConfig[] = [
  { id: 1, size: 65, depth: 0.55, parallaxSpeed: -0.08, animIndex: 1, pos: { top: '180px', left: '3%' }, opacity: 0.8, hideOnMobile: true },
  { id: 2, size: 80, depth: 0.7, parallaxSpeed: -0.1, animIndex: 2, pos: { top: '260px', right: '3.5%' }, opacity: 0.85, hideOnMobile: true },
  { id: 3, size: 50, depth: 0.4, parallaxSpeed: 0.06, animIndex: 3, pos: { top: '740px', right: '3%' }, opacity: 0.6, hideOnMobile: true },
  { id: 4, size: 60, depth: 0.5, parallaxSpeed: -0.07, animIndex: 4, pos: { top: '1060px', left: '3%' }, opacity: 0.65, hideOnMobile: true },
];

export function AuthBackgroundScene({
  variant = 'auth',
}: {
  variant?: 'auth' | 'legal';
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cubes = variant === 'auth' ? AUTH_CUBES : LEGAL_CUBES;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    // Check prefers-reduced-motion
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    let mouseX = 0;
    let mouseY = 0;
    let curMouseX = 0;
    let curMouseY = 0;
    let scrollY = window.scrollY;
    let curScrollY = window.scrollY;
    let isTicking = false;
    let isMounted = true;

    const onMouseMove = (e: MouseEvent) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      mouseX = (e.clientX - cx) / cx;
      mouseY = (e.clientY - cy) / cy;
      if (!isTicking) {
        isTicking = true;
        requestAnimationFrame(tick);
      }
    };

    const onScroll = () => {
      scrollY = window.scrollY;
      if (!isTicking) {
        isTicking = true;
        requestAnimationFrame(tick);
      }
    };

    function tick() {
      if (!isMounted || !el) {
        isTicking = false;
        return;
      }

      curMouseX += (mouseX - curMouseX) * 0.08;
      curMouseY += (mouseY - curMouseY) * 0.08;
      curScrollY += (scrollY - curScrollY) * 0.12;

      el.style.setProperty('--mouse-px', curMouseX.toFixed(4));
      el.style.setProperty('--mouse-py', curMouseY.toFixed(4));
      el.style.setProperty('--scroll-y', `${curScrollY.toFixed(1)}px`);

      const hasDelta =
        Math.abs(mouseX - curMouseX) > 0.0005 ||
        Math.abs(mouseY - curMouseY) > 0.0005 ||
        Math.abs(scrollY - curScrollY) > 0.5;

      if (hasDelta) {
        requestAnimationFrame(tick);
      } else {
        isTicking = false;
      }
    }

    window.addEventListener('mousemove', onMouseMove, { passive: true });
    window.addEventListener('scroll', onScroll, { passive: true });

    return () => {
      isMounted = false;
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('scroll', onScroll);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`pb-auth-scene ${variant === 'legal' ? 'pb-auth-scene-legal' : ''}`}
      aria-hidden="true"
    >
      {/* Floating 3D Geometric Cubes - clean, intentional, balanced */}
      {cubes.map((c) => {
        const style: React.CSSProperties = {
          ...c.pos,
          ['--cube-size' as string]: `${c.size}px`,
          ['--depth-factor' as string]: c.depth,
          ['--p-speed' as string]: c.parallaxSpeed,
          opacity: c.opacity ?? 1,
        };

        return (
          <div
            key={c.id}
            className={`pb-cube-anchor cube-id-${c.id} ${c.hideOnMobile ? 'hidden md:block' : 'block'}`}
            style={style}
          >
            <div className="hero-cube-3d">
              <div className={`hero-cube-inner cube-anim-${c.animIndex}`}>
                <div className="hero-cube-face face-top" />
                <div className="hero-cube-face face-front" />
                <div className="hero-cube-face face-right" />
                <div className="hero-cube-face face-left" />
                <div className="hero-cube-face face-back" />
                <div className="hero-cube-face face-bottom" />
              </div>
              <div className="hero-cube-shadow" />
            </div>
          </div>
        );
      })}
    </div>
  );
}
