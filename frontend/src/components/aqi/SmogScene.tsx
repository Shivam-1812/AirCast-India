import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { naqi } from '@/utils/aqi'

const BOX = { x: 14, y: 6, z: 8 }

function Particles({ pm25, windSpeed, windDeg }: { pm25: number; windSpeed: number; windDeg: number }) {
  // particle count scales with pollution
  const count = Math.round(THREE.MathUtils.clamp(300 + pm25 * 12, 300, 4500))
  const ref = useRef<THREE.Points>(null)
  const positions = useMemo(() => {
    const a = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      a[i * 3] = (Math.random() - 0.5) * BOX.x
      a[i * 3 + 1] = Math.random() * BOX.y
      a[i * 3 + 2] = (Math.random() - 0.5) * BOX.z
    }
    return a
  }, [count])
  const color = naqi(pm25).color
  const dir = useMemo(() => {
    const r = THREE.MathUtils.degToRad(windDeg)
    // wind direction is where wind comes FROM
    return new THREE.Vector2(-Math.sin(r), Math.cos(r))
  }, [windDeg])

  useFrame((_, dt) => {
    const p = ref.current?.geometry.attributes.position as THREE.BufferAttribute | undefined
    if (!p) return
    const v = 0.15 + Math.min(windSpeed, 40) * 0.05
    for (let i = 0; i < count; i++) {
      let x = p.getX(i) + dir.x * v * dt
      let z = p.getZ(i) + dir.y * v * dt * 0.6
      let y = p.getY(i) + Math.sin(performance.now() / 2000 + i) * 0.002
      if (x > BOX.x / 2) x -= BOX.x
      if (x < -BOX.x / 2) x += BOX.x
      if (z > BOX.z / 2) z -= BOX.z
      if (z < -BOX.z / 2) z += BOX.z
      p.setXYZ(i, x, y, z)
    }
    p.needsUpdate = true
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.09} color={color} transparent opacity={0.35 + Math.min(pm25, 250) / 500} depthWrite={false} sizeAttenuation />
    </points>
  )
}

function Skyline({ color }: { color: string }) {
  const blocks = useMemo(() => {
    const rng = (s: number) => { const x = Math.sin(s * 999) * 10000; return x - Math.floor(x) }
    return Array.from({ length: 26 }, (_, i) => ({
      x: -6 + (i % 13) * 1 + rng(i) * 0.3, z: -2.5 - Math.floor(i / 13) * 1.6 - rng(i + 3) * 0.6,
      h: 0.6 + rng(i + 7) * 2.6, w: 0.5 + rng(i + 11) * 0.4,
    }))
  }, [])
  return (
    <group position={[0, 0, 0]}>
      {blocks.map((b, i) => (
        <mesh key={i} position={[b.x, b.h / 2, b.z]}>
          <boxGeometry args={[b.w, b.h, b.w]} />
          <meshStandardMaterial color={color} roughness={0.8} emissive={color} emissiveIntensity={0.05} />
        </mesh>
      ))}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
        <planeGeometry args={[BOX.x, BOX.z]} />
        <meshStandardMaterial color="#0d1b30" transparent opacity={0.55} />
      </mesh>
      <gridHelper args={[BOX.x, 28, '#4a78b8', '#2a4570']} position={[0, 0.01, 0]} />
    </group>
  )
}

export default function SmogScene({ pm25, windSpeed = 8, windDeg = 270, className = '' }: {
  pm25: number; windSpeed?: number; windDeg?: number; className?: string
}) {
  const c = naqi(pm25)
  return (
    <div className={className} role="img" aria-label={`3D visualisation of airborne particles. PM2.5 is ${Math.round(pm25)} micrograms per cubic metre, category ${c.name}. Drag to rotate.`}>
      <Canvas camera={{ position: [0, 3.2, 8.5], fov: 50 }} dpr={[1, 1.75]}>
        <color attach="background" args={['#081426']} />
        <fog attach="fog" args={[c.sky[0] === '#6fc2ff' ? '#0b2247' : c.sky[1], 6, 18 - c.haze * 8]} />
        <ambientLight intensity={0.8} />
        <directionalLight position={[4, 6, 3]} intensity={1.1} />
        <Skyline color="#5f7fa8" />
        <Particles pm25={pm25} windSpeed={windSpeed} windDeg={windDeg} />
        <OrbitControls enablePan={false} enableZoom={false} autoRotate autoRotateSpeed={0.5} maxPolarAngle={Math.PI / 2.1} minPolarAngle={Math.PI / 4} />
      </Canvas>
    </div>
  )
}
