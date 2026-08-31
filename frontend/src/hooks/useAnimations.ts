import { useEffect, useRef, useCallback } from 'react'
import { animate, stagger } from 'animejs'

/**
 * Hook: animate children matching `selector` with a staggered fade-in-up
 * when the component mounts or when `deps` change.
 * Durations are intentionally slow (3x) so animations are clearly visible.
 */
export function useStaggerReveal(selector: string, deps: unknown[] = []) {
  const hasRun = useRef(false)

  useEffect(() => {
    // Skip the first render if there's no data yet
    if (!hasRun.current) {
      hasRun.current = true
      return
    }
    const els = document.querySelectorAll(selector)
    if (!els.length) return
    const ctrl = animate(els, {
      opacity: [0, 1],
      translateY: [40, 0],
      duration: 1500,
      delay: stagger(180, { start: 100 }),
      ease: 'outQuad',
    })
    return () => { try { ctrl.revert() } catch { /* noop */ } }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

/**
 * Hook: animate a single element's entrance (slide up + fade in).
 * Returns a ref to attach to the element.
 */
export function useSlideIn(deps: unknown[] = []) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const ctrl = animate(ref.current, {
      opacity: [0, 1],
      translateY: [40, 0],
      duration: 1200,
      ease: 'outQuad',
    })
    return () => { try { ctrl.revert() } catch { /* noop */ } }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return ref
}

/**
 * Hook: animate a scale-in entrance (for modals / overlays).
 * Returns a ref to attach to the element.
 */
export function useScaleIn(deps: unknown[] = []) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const ctrl = animate(ref.current, {
      opacity: [0, 1],
      scale: [0.85, 1],
      duration: 900,
      ease: 'outBack(1.4)',
    })
    return () => { try { ctrl.revert() } catch { /* noop */ } }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return ref
}

/**
 * Hook: count-up animation for a number element.
 * Returns a ref + the current animated value.
 * Duration is intentionally slow so the roll-up is clearly visible.
 */
export function useCountUp(target: number, opts?: {
  prefix?: string
  suffix?: string
  decimals?: number | 'auto'
  duration?: number
}, deps: unknown[] = []) {
  const ref = useRef<HTMLSpanElement>(null)
  const objRef = useRef({ val: 0 })

  useEffect(() => {
    if (!ref.current) return
    const el = ref.current
    const prefix = opts?.prefix ?? ''
    const suffix = opts?.suffix ?? ''
    const dec = opts?.decimals === 'auto'
      ? (String(target).split('.')[1]?.length ?? 0)
      : (opts?.decimals ?? 0)

    objRef.current.val = 0
    const ctrl = animate(objRef.current, {
      val: target,
      duration: opts?.duration ?? 2700,
      ease: 'outQuad',
      render: () => {
        el.textContent = prefix + objRef.current.val.toFixed(dec) + suffix
      },
    })
    return () => { try { ctrl.revert() } catch { /* noop */ } }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, ...deps])

  return ref
}

/**
 * Hook: returns a callback ref that triggers a nav bounce animation
 * when the element mounts (e.g. when a NavLink becomes active).
 */
export function useNavBounce() {
  const hasRun = useRef(false)
  const ref = useCallback((el: HTMLDivElement | null) => {
    if (!el || hasRun.current) return
    hasRun.current = true
    animate(el, {
      scale: [1, 1.2, 1],
      duration: 1050,
      ease: 'outQuad',
    })
  }, [])
  return ref
}
