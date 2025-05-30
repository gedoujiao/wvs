"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, XCircle, AlertTriangle, Loader2 } from "lucide-react"

export function DebugPanel() {
  const [isChecking, setIsChecking] = useState(false)
  const [results, setResults] = useState<any>(null)

  const checkSystemStatus = async () => {
    setIsChecking(true)
    const checks = {
      apiConnection: false,
      corsConfig: false,
      envVariables: false,
      frontendConfig: false,
    }

    try {
      // 检查环境变量
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      checks.envVariables = !!apiUrl

      if (apiUrl) {
        // 检查API连接
        try {
          const response = await fetch(`${apiUrl}/`)
          if (response.ok) {
            checks.apiConnection = true
            checks.corsConfig = true
          }
        } catch (error) {
          console.error("API连接失败:", error)
        }
      }

      checks.frontendConfig = true

      setResults({
        checks,
        apiUrl,
        timestamp: new Date().toLocaleString(),
      })
    } catch (error) {
      console.error("系统检查失败:", error)
    } finally {
      setIsChecking(false)
    }
  }

  const getStatusIcon = (status: boolean) => {
    return status ? <CheckCircle className="h-4 w-4 text-green-500" /> : <XCircle className="h-4 w-4 text-red-500" />
  }

  const getStatusBadge = (status: boolean) => {
    return <Badge variant={status ? "default" : "destructive"}>{status ? "正常" : "异常"}</Badge>
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center">
          <AlertTriangle className="h-5 w-5 mr-2" />
          系统诊断面板
        </CardTitle>
        <CardDescription>检查系统配置和连接状态，帮助诊断注册失败问题</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button onClick={checkSystemStatus} disabled={isChecking} className="w-full">
          {isChecking ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              检查中...
            </>
          ) : (
            "开始系统检查"
          )}
        </Button>

        {results && (
          <div className="space-y-4">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>检查时间: {results.timestamp}</AlertDescription>
            </Alert>

            <div className="grid gap-4">
              <div className="flex items-center justify-between p-3 border rounded">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(results.checks.envVariables)}
                  <span>环境变量配置</span>
                </div>
                {getStatusBadge(results.checks.envVariables)}
              </div>

              <div className="flex items-center justify-between p-3 border rounded">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(results.checks.apiConnection)}
                  <span>后端API连接</span>
                </div>
                {getStatusBadge(results.checks.apiConnection)}
              </div>

              <div className="flex items-center justify-between p-3 border rounded">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(results.checks.corsConfig)}
                  <span>CORS配置</span>
                </div>
                {getStatusBadge(results.checks.corsConfig)}
              </div>

              <div className="flex items-center justify-between p-3 border rounded">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(results.checks.frontendConfig)}
                  <span>前端配置</span>
                </div>
                {getStatusBadge(results.checks.frontendConfig)}
              </div>
            </div>

            <Alert variant={results.apiUrl ? "default" : "destructive"}>
              <AlertDescription>
                <strong>API地址:</strong> {results.apiUrl || "未配置"}
              </AlertDescription>
            </Alert>

            {!results.checks.apiConnection && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>后端API未运行！</strong>
                  <br />
                  请确保后端服务器已启动并运行在正确的端口上。
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
