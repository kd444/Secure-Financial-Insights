"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import {
  LayoutDashboard,
  Search,
  FileText,
  ShieldCheck,
  Settings,
  ChevronLeft,
  ChevronRight,
  Activity,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api"
import { useAppStore } from "@/lib/store"

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/query", label: "Query", icon: Search },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/evaluation", label: "Evaluation", icon: ShieldCheck },
  { href: "/settings", label: "Settings", icon: Settings },
]

export function AppSidebar() {
  const pathname = usePathname()
  const { sidebarCollapsed, toggleSidebar } = useAppStore()

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 30000,
    retry: 1,
  })

  const isHealthy = health?.status === "healthy"

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-border bg-sidebar transition-all duration-300",
        sidebarCollapsed ? "w-16" : "w-60"
      )}
    >
      <div className="flex items-center gap-3 border-b border-border px-4 py-4">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary">
          <Activity className="size-4 text-primary-foreground" />
        </div>
        {!sidebarCollapsed && (
          <div className="min-w-0">
            <h1 className="truncate text-sm font-semibold text-sidebar-foreground">
              Financial Insights
            </h1>
            <p className="truncate text-xs text-muted-foreground">Copilot</p>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-1 px-2 py-4">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-primary"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
            >
              <item.icon className="size-4 shrink-0" />
              {!sidebarCollapsed && <span>{item.label}</span>}
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-border px-3 py-3">
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "size-2 shrink-0 rounded-full",
              isHealthy ? "bg-success" : "bg-destructive"
            )}
          />
          {!sidebarCollapsed && (
            <span className="text-xs text-muted-foreground">
              {isHealthy ? "System Healthy" : "Degraded"}
            </span>
          )}
        </div>
      </div>

      <button
        onClick={toggleSidebar}
        className="flex items-center justify-center border-t border-border py-3 text-muted-foreground transition-colors hover:text-foreground"
        aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {sidebarCollapsed ? (
          <ChevronRight className="size-4" />
        ) : (
          <ChevronLeft className="size-4" />
        )}
      </button>
    </aside>
  )
}
