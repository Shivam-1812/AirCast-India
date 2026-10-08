import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import type { OverviewItem } from '@/api/endpoints'

const R = 2

function toVec(lat: number, lon: number, r = R) {
  const phi = THREE.MathUtils.degToRad(90 - lat)
  const theta = THREE.MathUtils.degToRad(lon + 180)
  return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta))
}

function Graticule() {
  const geo = useMemo(() => {
    const pts: number[] = []
    for (let lat = -60; lat <= 60; lat += 20) {
      for (let lon = -180; lon < 180; lon += 4) {
        const a = toVec(lat, lon, R * 1.003), b = toVec(lat, lon + 4, R * 1.003)
        pts.push(a.x, a.y, a.z, b.x, b.y, b.z)
      }
    }
    for (let lon = -180; lon < 180; lon += 20) {
      for (let lat = -88; lat < 88; lat += 4) {
        const a = toVec(lat, lon, R * 1.003), b = toVec(lat + 4, lon, R * 1.003)
        pts.push(a.x, a.y, a.z, b.x, b.y, b.z)
      }
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3))
    return g
  }, [])
  return <lineSegments geometry={geo}><lineBasicMaterial color="#5aa2ff" transparent opacity={0.28} /></lineSegments>
}

/** Soft atmosphere using a back-facing, additive fresnel shell. */
function Atmosphere() {
  const mat = useMemo(() => new THREE.ShaderMaterial({
    transparent: true, side: THREE.BackSide, blending: THREE.AdditiveBlending, depthWrite: false,
    vertexShader: 'varying vec3 n; void main(){ n = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    fragmentShader: 'varying vec3 n; void main(){ float i = pow(0.72 - dot(n, vec3(0.0,0.0,1.0)), 3.0); gl_FragColor = vec4(0.35,0.62,1.0,1.0) * i; }',
  }), [])
  return <mesh scale={1.22}><sphereGeometry args={[R, 48, 48]} /><primitive object={mat} attach="material" /></mesh>
}

function Pin({ c }: { c: OverviewItem }) {
  const ring = useRef<THREE.Mesh>(null)
  const pos = useMemo(() => toVec(c.lat, c.lon, R * 1.01), [c.lat, c.lon])
  const quat = useMemo(() => new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), pos.clone().normalize()), [pos])
  const size = 0.04 + Math.min(c.pm25, 250) / 2200
  useFrame(({ clock }) => {
    if (!ring.current) return
    const t = (clock.elapsedTime * 0.7 + c.lat) % 1
    ring.current.scale.setScalar(1 + t * 1.4)
    ;(ring.current.material as THREE.MeshBasicMaterial).opacity = 0.5 * (1 - t)
  })
  return (
    <group position={pos} quaternion={quat}>
      <mesh><sphereGeometry args={[size, 16, 16]} /><meshBasicMaterial color={c.color} /></mesh>
      <mesh ref={ring}><ringGeometry args={[size * 1.2, size * 1.6, 32]} /><meshBasicMaterial color={c.color} transparent side={THREE.DoubleSide} depthWrite={false} /></mesh>
    </group>
  )
}

function Spinner({ children }: { children: React.ReactNode }) {
  const g = useRef<THREE.Group>(null)
  useFrame((_, dt) => { if (g.current) g.current.rotation.y += dt * 0.08 })
  // initial rotation brings India (≈79°E) to face the camera
  return <group ref={g} rotation={[0.35, THREE.MathUtils.degToRad(-(90 + 79)), 0]}>{children}</group>
}

export default function Globe3D({ cities }: { cities: OverviewItem[] }) {
  return (
    <Canvas camera={{ position: [0, 0, 8], fov: 42 }} dpr={[1, 1.75]} gl={{ alpha: true }}>
      <ambientLight intensity={0.9} />
      <directionalLight position={[3, 2, 4]} intensity={1.4} />
      <Atmosphere />
      <Spinner>
        <mesh>
          <sphereGeometry args={[R, 64, 64]} />
          <meshStandardMaterial color="#0e2a55" roughness={0.9} metalness={0.1} emissive="#0a2350" emissiveIntensity={0.55} />
        </mesh>
        <Graticule />
        {cities.map((c) => <Pin key={c.city} c={c} />)}
      </Spinner>
      <OrbitControls enablePan={false} enableZoom={false} rotateSpeed={0.6} />
    </Canvas>
  )
}
