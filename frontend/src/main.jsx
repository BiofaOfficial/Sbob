import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import '@fontsource/atkinson-hyperlegible-next/400.css'
import '@fontsource/atkinson-hyperlegible-next/500.css'
import '@fontsource/atkinson-hyperlegible-next/700.css'
import '@fontsource-variable/literata'
import './styles.css'

createRoot(document.getElementById('root')).render(<App />)
