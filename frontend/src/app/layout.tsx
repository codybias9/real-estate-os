import type { Metadata } from 'next'
import './globals.css'
import { AuthHydration } from '@/components/AuthHydration'

export const metadata: Metadata = {
  title: 'Real Estate OS - Deal Pipeline Management',
  description: '10x better decision speed, not just data',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <AuthHydration />
        {children}
      </body>
    </html>
  )
}
