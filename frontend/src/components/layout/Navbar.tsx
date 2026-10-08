import { NavLink, Link } from 'react-router-dom'
import { Wind } from 'lucide-react'
import { AnimatedThemeToggler } from '@/components/ui/animated-theme-toggler'
import { cn } from '@/lib/utils'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/compare', label: 'Compare' },
  { to: '/model', label: 'Model' },
  { to: '/about', label: 'About' },
]

export default function Navbar() {
  return (
    <header className="sticky top-3 z-40 mx-auto mt-3 w-[calc(100%-2rem)] max-w-6xl">
      <nav aria-label="Main" className="glass flex items-center justify-between gap-2 px-4 py-2.5">
        <Link to="/" className="flex items-center gap-2 font-display text-lg font-bold">
          <span className="grid size-8 place-items-center rounded-xl bg-gradient-to-br from-sky-400 to-blue-700 text-white">
            <Wind size={18} />
          </span>
          AirCast <span className="text-accent">India</span>
        </Link>
        <ul className="flex items-center gap-0.5 text-sm font-medium">
          {links.map((l) => (
            <li key={l.to}>
              <NavLink
                to={l.to}
                end={l.to === '/'}
                className={({ isActive }) =>
                  cn('rounded-lg px-3 py-1.5 transition-colors hover:bg-white/30 dark:hover:bg-white/10', isActive && 'bg-white/50 dark:bg-white/10 text-accent')
                }
              >
                {l.label}
              </NavLink>
            </li>
          ))}
          <li className="ml-1">
            <AnimatedThemeToggler aria-label="Toggle dark mode" className="grid size-9 place-items-center rounded-lg hover:bg-white/30 dark:hover:bg-white/10" />
          </li>
        </ul>
      </nav>
    </header>
  )
}
