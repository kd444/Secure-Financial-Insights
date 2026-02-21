"use client"

import { AppSidebar } from "@/components/app-sidebar"
import { ScrollArea } from "@/components/ui/scroll-area"

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <AppSidebar />
      <ScrollArea className="flex-1">
        <main className="min-h-screen p-6 lg:p-8">{children}</main>
      </ScrollArea>
    </div>
  )
}
