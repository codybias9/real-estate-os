import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-primary-50 to-secondary-50">
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <h1 className="text-6xl font-bold text-gray-900 mb-6">
          Real Estate OS
        </h1>
        <p className="text-2xl text-gray-600 mb-4">
          10x better decision speed, not just data
        </p>
        <p className="text-lg text-gray-500 mb-12 max-w-2xl mx-auto">
          Surface the one thing to do next for each deal, with context. Bring email, calls,
          docs, and investor share-outs into your pipeline.
        </p>

        <div className="flex gap-4 justify-center">
          <Link
            href="/auth/login"
            className="px-8 py-3 bg-primary-600 text-white rounded-lg font-semibold hover:bg-primary-700 transition-colors shadow-medium"
          >
            Sign In
          </Link>
          <Link
            href="/auth/register"
            className="px-8 py-3 bg-white text-primary-600 rounded-lg font-semibold hover:bg-gray-50 transition-colors shadow-medium border border-primary-200"
          >
            Get Started
          </Link>
        </div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-lg shadow-soft">
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              🎯 Quick Wins
            </h3>
            <p className="text-gray-600">
              Generate & send, auto-assign, stage-aware templates
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-soft">
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              🚀 Workflow Accelerators
            </h3>
            <p className="text-gray-600">
              Next Best Action, smart lists, one-click tasking
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-soft">
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              💰 Portfolio & Outcomes
            </h3>
            <p className="text-gray-600">
              Deal economics, investor readiness, template leaderboards
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
