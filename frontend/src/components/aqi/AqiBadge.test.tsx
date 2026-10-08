import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import AqiBadge from './AqiBadge'

describe('AqiBadge', () => {
  it.each([
    [25, 'Good'],
    [75, 'Moderate'],
    [130, 'Very Poor'],
    [300, 'Severe'],
  ])('shows the right NAQI category for %i ug/m3', (v, name) => {
    render(<AqiBadge pm25={v} />)
    expect(screen.getByTestId('aqi-badge')).toHaveTextContent(name)
  })
})
