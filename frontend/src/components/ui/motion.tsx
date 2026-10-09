// AnimatedNumber, TiltCard and spring tokens adapted from beUI (MIT).
// Copyright (c) 2026 Saurabh Chauhan. See LICENSE.beui in this directory.
import { animate, motion, useInView, useMotionTemplate, useMotionValue, useReducedMotion, useSpring } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { HTMLMotionProps } from 'motion/react'

export const springPress = { type: 'spring', stiffness: 500, damping: 30, mass: 0.6 } as const
export const springLayout = { type: 'spring', stiffness: 360, damping: 32, mass: 0.6 } as const

export function Button({ className = '', ...props }: HTMLMotionProps<'button'>) {
  const reduce = useReducedMotion()
  return <motion.button className={`button ${className}`} whileTap={reduce ? undefined : { scale: 0.97 }} transition={springPress} {...props} />
}

export function AnimatedNumber({ value, className = '' }: { value: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, amount: 0.6 })
  const reduce = useReducedMotion()
  const [display, setDisplay] = useState(value)
  const current = useRef(0)
  useEffect(() => {
    if (!inView || reduce) return
    const controls = animate(current.current, value, {
      duration: 0.9, ease: [0.16, 1, 0.3, 1],
      onUpdate: next => { current.current = next; setDisplay(next) },
    })
    return () => controls.stop()
  }, [value, inView, reduce])
  return <span ref={ref} className={`tabular-nums ${className}`} aria-label={String(Math.round(value))}>
    <span aria-hidden="true">{Math.round(reduce ? value : display)}</span>
  </span>
}

export function TiltCard({ children, className = '' }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion()
  const rx = useMotionValue(0)
  const ry = useMotionValue(0)
  const gx = useMotionValue(50)
  const gy = useMotionValue(50)
  const srx = useSpring(rx, { stiffness: 200, damping: 15, mass: 0.3 })
  const sry = useSpring(ry, { stiffness: 200, damping: 15, mass: 0.3 })
  const transform = useMotionTemplate`perspective(1000px) rotateX(${srx}deg) rotateY(${sry}deg)`
  const background = useMotionTemplate`radial-gradient(circle at ${gx}% ${gy}%, rgba(185,255,218,.09), transparent 60%)`
  return <motion.div ref={ref} className={`tilt-card ${className}`} style={{ transform: reduce ? 'none' : transform }}
    onPointerMove={event => {
      if (reduce || event.pointerType !== 'mouse' || !ref.current) return
      const rect = ref.current.getBoundingClientRect()
      const px = (event.clientX - rect.left) / rect.width
      const py = (event.clientY - rect.top) / rect.height
      ry.set((px - 0.5) * 3); rx.set((0.5 - py) * 3); gx.set(px * 100); gy.set(py * 100)
    }} onPointerLeave={() => { rx.set(0); ry.set(0) }}>
    {children}
    {!reduce && <motion.div aria-hidden="true" className="card-glare" style={{ background }} />}
  </motion.div>
}

export function Reveal({ children, className = '', delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
  const reduce = useReducedMotion()
  return <motion.div className={className} initial={reduce ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay, ease: [0.16, 1, 0.3, 1] }}>{children}</motion.div>
}
