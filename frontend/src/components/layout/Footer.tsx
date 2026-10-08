export default function Footer() {
  return (
    <footer className="mx-auto mt-16 w-full max-w-6xl px-4 pb-10 text-center text-xs text-muted">
      <p>
        Data:{' '}
        <a className="underline" href="https://open-meteo.com" target="_blank" rel="noreferrer">Open-Meteo</a>, Copernicus CAMS, ERA5 (CC BY 4.0).
        Categories follow the CPCB National AQI.
      </p>
      <p className="mt-1">Educational project. Not an official AQI source and not medical advice.</p>
    </footer>
  )
}
