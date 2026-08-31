import { animate, stagger } from 'animejs'

/**
 * Reusable animation presets for the VOL Analytics dashboard.
 * All functions operate on DOM elements via anime.js v4.
 * Durations are intentionally slow (3x) so animations are clearly visible.
 */

// ─── Staggered Fade-In Up ────────────────────────────────────────────
// Elements start invisible and slightly below, then slide up and fade in
// with a stagger delay between each element.
export function staggerFadeInUp(
  selector: string,
  opts?: { delay?: number; duration?: number; staggerMs?: number },
) {
  const els = document.querySelectorAll(selector)
  if (!els.length) return null
  return animate(els, {
    opacity: [0, 1],
    translateX: [0, 0],
    translateY: [40, 0],
    duration: opts?.duration ?? 1500,
    delay: stagger(opts?.staggerMs ?? 180, { start: opts?.delay ?? 0 }),
    ease: 'outQuad',
  })
}

// ─── Single Element Slide-In Up ──────────────────────────────────────
export function slideInUp(
  el: HTMLElement | null,
  opts?: { duration?: number; delay?: number },
) {
  if (!el) return null
  return animate(el, {
    opacity: [0, 1],
    translateY: [40, 0],
    duration: opts?.duration ?? 1200,
    delay: opts?.delay ?? 0,
    ease: 'outQuad',
  })
}

// ─── Scale-In (for modals / overlays) ────────────────────────────────
export function scaleIn(
  el: HTMLElement | null,
  opts?: { duration?: number; delay?: number },
) {
  if (!el) return null
  return animate(el, {
    opacity: [0, 1],
    scale: [0.85, 1],
    duration: opts?.duration ?? 900,
    delay: opts?.delay ?? 0,
    ease: 'outBack(1.4)',
  })
}

// ─── Bar Grow (for pass-rate bars, progress bars) ─────────────────────
export function barGrow(
  selector: string,
  opts?: { duration?: number; staggerMs?: number },
) {
  const els = document.querySelectorAll(selector)
  if (!els.length) return null
  return animate(els, {
    width: ['0%', (el: HTMLElement) => el.dataset.barWidth ?? '0%'],
    duration: opts?.duration ?? 2400,
    delay: stagger(opts?.staggerMs ?? 300, { start: 200 }),
    ease: 'outQuad',
  })
}

// ─── Number Count-Up ─────────────────────────────────────────────────
// Animates a DOM element's textContent from 0 to a target number.
export function countUpElement(el: HTMLElement) {
  const target = parseFloat(el.dataset.countTo ?? '0')
  if (isNaN(target)) return null
  const prefix = el.dataset.countPrefix ?? ''
  const suffix = el.dataset.countSuffix ?? ''
  const decimals = (el.dataset.countDecimals ?? '0') === 'auto'
    ? (String(target).split('.')[1]?.length ?? 0)
    : parseInt(el.dataset.countDecimals ?? '0', 10)

  const obj = { val: 0 }
  return animate(obj, {
    val: target,
    duration: 2700,
    ease: 'outQuad',
    render: () => {
      el.textContent = prefix + obj.val.toFixed(decimals) + suffix
    },
  })
}

// ─── Nav Icon Bounce ─────────────────────────────────────────────────
export function navBounce(el: HTMLElement | null) {
  if (!el) return null
  return animate(el, {
    scale: [1, 1.25, 1],
    duration: 900,
    ease: 'outQuad',
  })
}

// ─── Ripple Pulse (for entry/exit markers) ────────────────────────────
export function pulseOnce(el: HTMLElement | null) {
  if (!el) return null
  return animate(el, {
    scale: [1, 1.1, 1],
    opacity: [1, 0.6, 1],
    duration: 1800,
    ease: 'inOutSine',
  })
}

// ─── Highlight Flash ─────────────────────────────────────────────────
export function flashHighlight(el: HTMLElement | null) {
  if (!el) return null
  return animate(el, {
    backgroundColor: ['rgba(68,216,241,0.2)', 'rgba(68,216,241,0)'],
    duration: 1800,
    ease: 'outQuad',
  })
}
