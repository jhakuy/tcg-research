import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'TCG Research - Pokemon Card Investment Tool',
  description: 'AI-powered Pokemon card market analysis and investment recommendations',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen">
        <nav className="bg-white shadow-lg border-b-4 border-pokemon-blue">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-pokemon-blue rounded-full flex items-center justify-center">
                  <span className="text-white font-bold text-sm">⚡</span>
                </div>
                <h1 className="text-xl font-bold text-gray-900">TCG Research</h1>
              </div>
              <div className="text-sm text-gray-600">
                Pokemon Card Investment Analysis
              </div>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  )
}