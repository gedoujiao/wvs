"use client"

import { DebugPanel } from "@/components/debug-panel"

export default function DebugPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">系统调试面板</h1>
          <p className="text-gray-600 mt-2">诊断和解决系统问题</p>
        </div>

        <DebugPanel />

        <div className="mt-8 space-y-4">
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">常见问题解决方案</h2>

            <div className="space-y-4">
              <div className="border-l-4 border-red-500 pl-4">
                <h3 className="font-medium text-red-700">问题1: 无法连接到服务器</h3>
                <p className="text-sm text-gray-600 mt-1">解决方案：确保后端服务器正在运行在 http://localhost:8000</p>
                <code className="text-xs bg-gray-100 p-1 rounded">cd server && python main.py</code>
              </div>

              <div className="border-l-4 border-yellow-500 pl-4">
                <h3 className="font-medium text-yellow-700">问题2: CORS错误</h3>
                <p className="text-sm text-gray-600 mt-1">解决方案：检查后端CORS配置是否包含前端域名</p>
              </div>

              <div className="border-l-4 border-blue-500 pl-4">
                <h3 className="font-medium text-blue-700">问题3: 环境变量未配置</h3>
                <p className="text-sm text-gray-600 mt-1">解决方案：确保 NEXT_PUBLIC_API_URL 环境变量已正确设置</p>
              </div>

              <div className="border-l-4 border-green-500 pl-4">
                <h3 className="font-medium text-green-700">问题4: 数据库连接失败</h3>
                <p className="text-sm text-gray-600 mt-1">解决方案：检查数据库配置和连接字符串</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
