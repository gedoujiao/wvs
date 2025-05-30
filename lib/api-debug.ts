// API调试工具
export class ApiDebugger {
  static async testConnection(apiUrl: string) {
    const tests = {
      ping: false,
      register: false,
      cors: false,
    }

    try {
      // 测试基本连接
      const pingResponse = await fetch(`${apiUrl}/`)
      tests.ping = pingResponse.ok
      tests.cors = true // 如果能发送请求说明CORS基本正常

      // 测试注册端点
      try {
        const registerResponse = await fetch(`${apiUrl}/register`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: "test@example.com",
            password: "testpassword123",
          }),
        })

        // 即使返回错误，只要能收到响应就说明端点存在
        tests.register = registerResponse.status !== 404
      } catch (error) {
        console.error("注册端点测试失败:", error)
      }
    } catch (error) {
      console.error("API连接测试失败:", error)
    }

    return tests
  }

  static logApiError(error: any, context: string) {
    console.group(`🚨 API错误 - ${context}`)
    console.error("错误详情:", error)
    console.error("错误消息:", error.message)
    console.error("错误堆栈:", error.stack)
    console.groupEnd()
  }
}
