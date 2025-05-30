"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { useAuth } from "@/contexts/auth-context"
import { apiService } from "@/lib/api"
import { ProtectedRoute } from "@/components/protected-route"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { Shield, Search, Clock, CheckCircle, XCircle, AlertTriangle, LogOut, Eye, Loader2 } from "lucide-react"
import Link from "next/link"

interface ScanTask {
  id: string
  url: string
  status: "pending" | "running" | "completed" | "failed"
  created_at: string
  completed_at?: string
  vulnerabilities_count: number
}

export default function DashboardPage() {
  const { user, logout, token } = useAuth()
  const { toast } = useToast()
  const [url, setUrl] = useState("")
  const [isScanning, setIsScanning] = useState(false)
  const [tasks, setTasks] = useState<ScanTask[]>([])
  const [isLoadingTasks, setIsLoadingTasks] = useState(true)

  useEffect(() => {
    loadTasks()
  }, [])

  const loadTasks = async () => {
    if (!token) return

    try {
      const tasksData = await apiService.getScanTasks(token)
      setTasks(tasksData)
    } catch (error) {
      toast({
        title: "加载失败",
        description: "无法加载扫描任务列表",
        variant: "destructive",
      })
    } finally {
      setIsLoadingTasks(false)
    }
  }

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url || !token) return

    setIsScanning(true)
    try {
      const task = await apiService.createScanTask(url, token)
      setTasks((prev) => [task, ...prev])
      setUrl("")
      toast({
        title: "扫描任务已创建",
        description: `正在扫描 ${url}`,
      })
    } catch (error) {
      toast({
        title: "创建失败",
        description: error instanceof Error ? error.message : "创建扫描任务失败",
        variant: "destructive",
      })
    } finally {
      setIsScanning(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "pending":
        return <Clock className="h-4 w-4" />
      case "running":
        return <Loader2 className="h-4 w-4 animate-spin" />
      case "completed":
        return <CheckCircle className="h-4 w-4" />
      case "failed":
        return <XCircle className="h-4 w-4" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending":
        return "secondary"
      case "running":
        return "default"
      case "completed":
        return "default"
      case "failed":
        return "destructive"
      default:
        return "secondary"
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case "pending":
        return "等待中"
      case "running":
        return "扫描中"
      case "completed":
        return "已完成"
      case "failed":
        return "失败"
      default:
        return status
    }
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <div className="flex items-center">
                <Shield className="h-8 w-8 text-blue-600" />
                <span className="ml-2 text-xl font-bold text-gray-900">漏洞扫描控制台</span>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-600">欢迎，{user?.email}</span>
                <Button variant="outline" size="sm" onClick={logout}>
                  <LogOut className="h-4 w-4 mr-2" />
                  退出
                </Button>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Scan Form */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Search className="h-5 w-5 mr-2" />
                新建扫描任务
              </CardTitle>
              <CardDescription>输入目标网站URL，系统将自动进行安全漏洞检测</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleScan} className="flex space-x-4">
                <Input
                  type="url"
                  placeholder="https://example.com"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="flex-1"
                  required
                  disabled={isScanning}
                />
                <Button type="submit" disabled={isScanning || !url}>
                  {isScanning ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      扫描中...
                    </>
                  ) : (
                    <>
                      <Search className="mr-2 h-4 w-4" />
                      开始扫描
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Tasks List */}
          <Card>
            <CardHeader>
              <CardTitle>扫描任务历史</CardTitle>
              <CardDescription>查看您的所有扫描任务和结果</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingTasks ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin" />
                </div>
              ) : tasks.length === 0 ? (
                <div className="text-center py-8">
                  <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">还没有扫描任务</p>
                  <p className="text-sm text-gray-400">创建您的第一个扫描任务开始使用</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {tasks.map((task) => (
                    <div
                      key={task.id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50"
                    >
                      <div className="flex-1">
                        <div className="flex items-center space-x-3">
                          <div className="flex items-center space-x-2">
                            {getStatusIcon(task.status)}
                            <Badge variant={getStatusColor(task.status) as any}>{getStatusText(task.status)}</Badge>
                          </div>
                          <span className="font-medium">{task.url}</span>
                        </div>
                        <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
                          <span>创建时间: {new Date(task.created_at).toLocaleString()}</span>
                          {task.completed_at && <span>完成时间: {new Date(task.completed_at).toLocaleString()}</span>}
                          {task.status === "completed" && (
                            <span className="flex items-center">
                              <AlertTriangle className="h-4 w-4 mr-1" />
                              发现 {task.vulnerabilities_count} 个漏洞
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {task.status === "completed" && (
                          <Link href={`/reports/${task.id}`}>
                            <Button variant="outline" size="sm">
                              <Eye className="h-4 w-4 mr-2" />
                              查看报告
                            </Button>
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </main>
      </div>
    </ProtectedRoute>
  )
}
