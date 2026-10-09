import { Newspaper, Radar, TrendingUp, Youtube } from 'lucide-react'
import { motion, useInView, useMotionValue, useReducedMotion, useSpring, useTransform } from 'motion/react'
import { useRef } from 'react'
import type { PointerEvent, ReactNode } from 'react'

const followSpring = { stiffness: 110, damping: 22, mass: 0.7 }
const hoverSpring = { type: 'spring', stiffness: 260, damping: 22, mass: 0.6 } as const

function OrbitCard({ children, className, reducedMotion }: { children: ReactNode; className: string; reducedMotion: boolean | null }) {
  return <div className={`orbit-node ${className} orbit-motion`}>
    <motion.span className="orbit-card" style={{ z: reducedMotion ? 0 : 22 }}
      whileHover={reducedMotion ? undefined : { scale: 1.1, y: -5, z: 38 }} transition={hoverSpring}>
      {children}
    </motion.span>
  </div>
}

export function SignalOrbit() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { amount: 0.15 })
  const reducedMotion = useReducedMotion()
  const pointerX = useMotionValue(0)
  const pointerY = useMotionValue(0)
  const x = useSpring(useTransform(pointerX, [-1, 1], [-14, 14]), followSpring)
  const y = useSpring(useTransform(pointerY, [-1, 1], [-12, 12]), followSpring)
  const rotateX = useSpring(useTransform(pointerY, [-1, 1], [7, -7]), followSpring)
  const rotateY = useSpring(useTransform(pointerX, [-1, 1], [-9, 9]), followSpring)
  const glowX = useSpring(160, followSpring)
  const glowY = useSpring(160, followSpring)
  const glowOpacity = useSpring(0, { stiffness: 140, damping: 24 })

  function followPointer(event: PointerEvent<HTMLDivElement>) {
    if (reducedMotion || event.pointerType !== 'mouse' || !ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const localX = event.clientX - rect.left
    const localY = event.clientY - rect.top
    pointerX.set(Math.max(-1, Math.min(1, localX / rect.width * 2 - 1)))
    pointerY.set(Math.max(-1, Math.min(1, localY / rect.height * 2 - 1)))
    glowX.set(localX); glowY.set(localY); glowOpacity.set(1)
  }

  function resetPointer() {
    pointerX.set(0); pointerY.set(0); glowOpacity.set(0)
  }

  return <div ref={ref} className="signal-orbit" data-running={inView && !reducedMotion} aria-hidden="true"
    onPointerMove={followPointer} onPointerLeave={resetPointer}>
    <motion.div className="orbit-scene" style={reducedMotion ? undefined : { x, y, rotateX, rotateY, transformPerspective: 900 }}>
      <div className="orbit-field">
        <motion.div className="orbit-cursor-glow" style={{ x: glowX, y: glowY, opacity: glowOpacity }} />
        <div className="orbit-ring orbit-outer" />
        <div className="orbit-ring orbit-middle orbit-motion" />
        <div className="orbit-ring orbit-inner" />
        <div className="orbit-sweep orbit-motion" />
        <div className="orbit-pulse orbit-motion" />
        <div className="orbit-pulse pulse-delayed orbit-motion" />
        <div className="orbit-cross cross-horizontal" />
        <div className="orbit-cross cross-vertical" />
        <div className="orbit-track track-inner orbit-motion"><span className="orbit-dot dot-one orbit-motion" /></div>
        <div className="orbit-track track-outer orbit-motion"><span className="orbit-dot dot-two orbit-motion" /></div>
        <div className="orbit-core"><span className="orbit-core-halo orbit-motion" /><Radar className="orbit-motion" size={34} strokeWidth={1.2} /></div>
      </div>
      <OrbitCard className="node-one" reducedMotion={reducedMotion}><Youtube size={16} /> Video velocity</OrbitCard>
      <OrbitCard className="node-two" reducedMotion={reducedMotion}><TrendingUp size={16} /> Search interest</OrbitCard>
      <OrbitCard className="node-three" reducedMotion={reducedMotion}><Newspaper size={16} /> News coverage</OrbitCard>
    </motion.div>
    <span className="orbit-label mono">LESS NOISE. MORE SIGNAL.</span>
  </div>
}
