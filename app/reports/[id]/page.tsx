"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/contexts/auth-context"
import { apiService } from "@/lib/api"
import { ProtectedRoute } from "@/components/protected-route"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Shield, ArrowLeft, Download, AlertTriangle, Info, CheckCircle, XCircle, Loader2 } from "lucide-react"
import Link from "next/link"
import { useParams } from "next/navigation"

interface Vulnerability {
  id: string
  type: string
  payload: string
  location: string
  description: string
  severity: "low" | "medium" | "high" | "critical"
}

interface ScanReport {
  id: string
  url: string
  status: string
  created_at: string
  completed_at?: string
  vulnerabilities: Vulnerability[]
  screenshots?: string[]
}

export default function ReportPage() {
  const { token } = useAuth()
  const params = useParams()
  const [report, setReport] = useState<ScanReport | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    loadReport()
  }, [])

  const loadReport = async () => {
    if (!token || !params.id) return

    try {
      const reportData = await apiService.getScanReport(params.id as string, token)
      setReport(reportData)
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载报告失败")
    } finally {
      setIsLoading(false)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "destructive"
      case "high":
        return "destructive"
      case "medium":
        return "default"
      case "low":
        return "secondary"
      default:
        return "secondary"
    }
  }

  const getSeverityText = (severity: string) => {
    switch (severity) {
      case "critical":
        return "严重"
      case "high":
        return "高危"
      case "medium":
        return "中危"
      case "low":
        return "低危"
      default:
        return severity
    }
  }

  const getVulnerabilityTypeText = (type: string) => {
    switch (type) {
      case "xss":
        return "XSS跨站脚本"
      case "sqli":
        return "SQL注入"
      case "csrf":
        return "CSRF跨站请求伪造"
      case "lfi":
        return "本地文件包含"
      case "rfi":
        return "远程文件包含"
      default:
        return type.toUpperCase()
    }
  }

  if (isLoading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </ProtectedRoute>
    )
  }

  if (error || !report) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-gray-50 px-4 py-8">
          <div className="max-w-4xl mx-auto">
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertDescription>{error || "报告不存在"}</AlertDescription>
            </Alert>
            <div className="mt-4">
              <Link href="/dashboard">
                <Button variant="outline">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  返回控制台
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <div className="flex items-center">
                <Link href="/dashboard">
                  <Button variant="ghost" size="sm">
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    返回控制台
                  </Button>
                </Link>
                <div className="ml-4 flex items-center">
                  <Shield className="h-6 w-6 text-blue-600" />
                  <span className="ml-2 text-lg font-semibold text-gray-900">扫描报告</span>
                </div>
              </div>
              <Button variant="outline">
                <Download className="h-4 w-4 mr-2" />
                导出PDF
              </Button>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Report Overview */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>扫描概览</span>
                <Badge variant={report.status === "completed" ? "default" : "secondary"}>
                  {report.status === "completed" ? "已完成" : report.status}
                </Badge>
              </CardTitle>
              <CardDescription>目标网站: {report.url}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{report.vulnerabilities.length}</div>
                  <div className="text-sm text-gray-500">发现漏洞总数</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {report.vulnerabilities.filter((v) => v.severity === "critical" || v.severity === "high").length}
                  </div>
                  <div className="text-sm text-gray-500">高危漏洞</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{report.completed_at ? "✓" : "○"}</div>
                  <div className="text-sm text-gray-500">扫描状态</div>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">开始时间:</span> {new Date(report.created_at).toLocaleString()}
                </div>
                {report.completed_at && (
                  <div>
                    <span className="font-medium">完成时间:</span> {new Date(report.completed_at).toLocaleString()}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Vulnerabilities */}
          {report.vulnerabilities.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <AlertTriangle className="h-5 w-5 mr-2 text-orange-500" />
                  发现的漏洞
                </CardTitle>
                <CardDescription>以下是扫描过程中发现的安全漏洞详情</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {report.vulnerabilities.map((vuln, index) => (
                    <div key={vuln.id} className="border rounded-lg p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="text-lg font-semibold flex items-center">
                            <span className="mr-2">#{index + 1}</span>
                            {getVulnerabilityTypeText(vuln.type)}
                          </h3>
                          <p className="text-gray-600 mt-1">{vuln.description}</p>
                        </div>
                        <Badge variant={getSeverityColor(vuln.severity) as any}>{getSeverityText(vuln.severity)}</Badge>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-medium">发现位置:</span>
                          <code className="ml-2 px-2 py-1 bg-gray-100 rounded text-xs">{vuln.location}</code>
                        </div>
                        <div>
                          <span className="font-medium">测试载荷:</span>
                          <code className="ml-2 px-2 py-1 bg-gray-100 rounded text-xs">{vuln.payload}</code>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="text-center py-12">
                <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">未发现安全漏洞</h3>
                <p className="text-gray-600">恭喜！目标网站在本次扫描中未发现明显的安全漏洞。</p>
                <Alert className="mt-6 max-w-md mx-auto">
                  <Info className="h-4 w-4" />
                  <AlertDescription>建议定期进行安全扫描，以确保网站持续安全。</AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </ProtectedRoute>
  )
}
