'use client';

import React, { useEffect, useRef } from 'react';
import { PixelWord, type PixelWordType } from './pixel-word-svg';

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

interface PixelWordConfig {
  word: PixelWordType;
  pos: { top?: string; bottom?: string; left?: string; right?: string };
  width?: number;
  rotate?: number;
  opacity?: number;
  hideOnMobile?: boolean;
  animClass?: string;
}

const AUTH_CUBES: CubeConfig[] = [
  { id: 1, size: 85, depth: 0.8, parallaxSpeed: -0.12, animIndex: 1, pos: { top: '15%', left: '3.5%' }, hideOnMobile: true },
  { id: 2, size: 100, depth: 0.85, parallaxSpeed: -0.15, animIndex: 2, pos: { top: '17%', right: '4%' }, hideOnMobile: true },
  { id: 3, size: 55, depth: 0.45, parallaxSpeed: 0.08, animIndex: 3, pos: { top: '52%', left: '5%' }, opacity: 0.7, hideOnMobile: true },
  { id: 4, size: 75, depth: 0.6, parallaxSpeed: 0.1, animIndex: 4, pos: { bottom: '14%', right: '4.5%' }, hideOnMobile: false },
  { id: 5, size: 65, depth: 0.55, parallaxSpeed: -0.07, animIndex: 5, pos: { bottom: '11%', left: '5.5%' }, opacity: 0.75, hideOnMobile: true },
];

const AUTH_WORDS: PixelWordConfig[] = [
  { word: 'DEMAND', pos: { top: '21%', left: '16%' }, width: 130, rotate: -2, opacity: 0.35, hideOnMobile: true, animClass: 'pb-float-gentle-2' },
  { word: 'INSIGHT', pos: { top: '21%', right: '16%' }, width: 130, rotate: 2, opacity: 0.35, hideOnMobile: true, animClass: 'pb-float-gentle-3' },
  { word: 'INTENT', pos: { top: '42%', left: '4.5%' }, width: 140, rotate: -3, opacity: 0.42, hideOnMobile: true, animClass: 'pb-float-gentle-1' },
  { word: 'SIGNAL', pos: { top: '44%', right: '4.5%' }, width: 135, rotate: 3, opacity: 0.4, hideOnMobile: true, animClass: 'pb-float-gentle-2' },
  { word: 'GROWTH', pos: { bottom: '26%', left: '5%' }, width: 150, rotate: 1.5, opacity: 0.42, hideOnMobile: true, animClass: 'pb-float-gentle-3' },
  { word: 'RADAR', pos: { bottom: '28%', right: '5%' }, width: 125, rotate: -2, opacity: 0.38, hideOnMobile: true, animClass: 'pb-float-gentle-1' },
];

const LEGAL_CUBES: CubeConfig[] = [
  { id: 1, size: 75, depth: 0.6, parallaxSpeed: -0.09, animIndex: 1, pos: { top: '200px', left: '2.5%' }, hideOnMobile: true },
  { id: 2, size: 90, depth: 0.75, parallaxSpeed: -0.12, animIndex: 2, pos: { top: '280px', right: '3%' }, hideOnMobile: true },
  { id: 3, size: 60, depth: 0.45, parallaxSpeed: 0.08, animIndex: 3, pos: { top: '760px', right: '3.5%' }, opacity: 0.65, hideOnMobile: true },
  { id: 4, size: 70, depth: 0.55, parallaxSpeed: -0.08, animIndex: 4, pos: { top: '1080px', left: '2.5%' }, opacity: 0.7, hideOnMobile: true },
];

const LEGAL_WORDS: PixelWordConfig[] = [
  { word: 'INTENT', pos: { top: '480px', left: '2%' }, width: 135, rotate: -2, opacity: 0.38, hideOnMobile: true, animClass: 'pb-float-gentle-1' },
  { word: 'RESEARCH', pos: { top: '530px', right: '2%' }, width: 165, rotate: 2, opacity: 0.35, hideOnMobile: true, animClass: 'pb-float-gentle-2' },
  { word: 'DEMAND', pos: { top: '920px', left: '2%' }, width: 140, rotate: 1, opacity: 0.38, hideOnMobile: true, animClass: 'pb-float-gentle-3' },
  { word: 'RADAR', pos: { top: '1240px', right: '2%' }, width: 130, rotate: -1.5, opacity: 0.38, hideOnMobile: true, animClass: 'pb-float-gentle-1' },
];

export function AuthBackgroundScene({
  variant = 'auth',
}: {
  variant?: 'auth' | 'legal';
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cubes = variant === 'auth' ? AUTH_CUBES : LEGAL_CUBES;
  const words = variant === 'auth' ? AUTH_WORDS : LEGAL_WORDS;

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
      {/* 1. Floating 3D Geometric Cubes */}
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

      {/* 2. Scattered Pixel-Text Word Accents */}
      {words.map((w, idx) => {
        const style: React.CSSProperties = {
          ...w.pos,
          transform: `rotate(${w.rotate ?? 0}deg)`,
        };

        return (
          <div
            key={idx}
            className={`pb-pixel-word-wrapper ${w.hideOnMobile ? 'hidden lg:block' : 'block'} ${w.animClass || ''}`}
            style={style}
          >
            <PixelWord
              word={w.word}
              opacity={w.opacity ?? 0.2}
              style={{ width: `${w.width || 140}px`, height: 'auto' }}
            />
          </div>
        );
      })}
    </div>
  );
}
