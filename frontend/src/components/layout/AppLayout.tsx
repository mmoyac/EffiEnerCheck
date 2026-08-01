import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden bg-slate-900">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar desktop */}
      <div className="hidden md:flex md:flex-shrink-0">
        <Sidebar />
      </div>

      {/* Sidebar mobile (drawer) */}
      <div className={`fixed inset-y-0 left-0 z-50 md:hidden transition-transform duration-300 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <Sidebar />
      </div>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile header with hamburger */}
        <div className="flex h-14 items-center border-b border-slate-700 bg-slate-900 px-4 md:hidden">
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="mr-3 rounded-lg p-2 text-slate-400 hover:bg-slate-700 hover:text-slate-100"
          >
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <span className="text-sm font-semibold text-slate-100">EnerCheck</span>
        </div>

        {/* Desktop header */}
        <div className="hidden md:block">
          <Header />
        </div>

        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
