import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Link from 'next/link';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Real Estate OS - Investment Platform',
  description: 'Automated real estate investment analysis and outreach platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          {/* Navigation */}
          <nav className="bg-white shadow-sm border-b">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex">
                  <Link href="/" className="flex items-center">
                    <span className="text-2xl font-bold text-primary-600">Real Estate OS</span>
                  </Link>
                  <div className="hidden sm:ml-10 sm:flex sm:space-x-8">
                    <Link
                      href="/"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-primary-600"
                    >
                      Dashboard
                    </Link>
                    <Link
                      href="/properties"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-900"
                    >
                      Properties
                    </Link>
                    <Link
                      href="/pipeline"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-900"
                    >
                      Pipeline
                    </Link>
                    <Link
                      href="/campaigns"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-900"
                    >
                      Campaigns
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </nav>

          {/* Main Content */}
          <main className="py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
