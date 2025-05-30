const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
interface UserResponse {
    id: string;
    email: string;
    is_admin: boolean;
    created_at: string; // 假设后端返回的是字符串类型的时间
}
interface LoginResponse {
  access_token: string
  token_type: string
  user: UserResponse
}
interface UserUpdate {
    email?: string;
    password?: string;
}

interface ScanTask {
  id: string
  url: string
  status: "pending" | "running" | "completed" | "failed"
  created_at: string
  completed_at?: string
  vulnerabilities_count: number
}

interface ScanReport {
  id: string
  url: string
  status: string
  created_at: string
  completed_at?: string
  vulnerabilities: Array<{
    id: string
    type: string
    payload: string
    location: string
    description: string
    severity: "low" | "medium" | "high" | "critical"
  }>
  screenshots?: string[]
}

class ApiService {
  private async request<T>(endpoint: string, options: RequestInit = {}, token?: string): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`

    console.log(`🌐 API请求: ${options.method || "GET"} ${url}`)

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options.headers,
    }

    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      })

      console.log(`📡 API响应: ${response.status} ${response.statusText}`)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        console.error("❌ API错误响应:", errorData)

        // 提供更详细的错误信息
        let errorMessage = errorData.detail || `HTTP error! status: ${response.status}`

        if (response.status === 422) {
          errorMessage = "请求数据格式错误，请检查邮箱格式和密码长度"
        } else if (response.status === 500) {
          errorMessage = "服务器内部错误，请稍后重试"
        } else if (response.status === 0 || !response.status) {
          errorMessage = "无法连接到服务器，请检查网络连接和服务器状态"
        }

        throw new Error(errorMessage)
      }

      const data = await response.json()
      console.log("✅ API成功响应:", data)
      return data
    } catch (error) {
      console.error("🚨 API请求失败:", error)

      if (error instanceof TypeError && error.message.includes("fetch")) {
        throw new Error("无法连接到服务器，请确保后端服务正在运行")
      }

      throw error
    }
  }

  async login(email: string, password: string): Promise<LoginResponse> {
    return this.request<LoginResponse>("/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    })
  }

  async register(email: string, password: string): Promise<void> {
    return this.request<void>("/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    })
  }

  async getCurrentUser(token: string) {
    return this.request("/me", {}, token)
  }

  async createScanTask(url: string, token: string): Promise<ScanTask> {
    return this.request<ScanTask>(
      "/scan",
      {
        method: "POST",
        body: JSON.stringify({ url }),
      },
      token,
    )
  }

  async getScanTasks(token: string): Promise<ScanTask[]> {
    return this.request<ScanTask[]>("/scans", {}, token)
  }

  async getScanReport(id: string, token: string): Promise<ScanReport> {
    return this.request<ScanReport>(`/scan/${id}`, {}, token)
  }

  // 添加连接测试方法
  async testConnection(): Promise<boolean> {
    try {
      await this.request("/")
      return true
    } catch (error) {
      console.error("连接测试失败:", error)
      return false
    }
  }
 
    async getUsers(token: string): Promise<UserResponse[]> {
        return this.request<UserResponse[]>("/users", {}, token);
    }

    async updateUser(user_id: string, user_data: UserUpdate, token: string): Promise<UserResponse> {
        return this.request<UserResponse>(`/users/${user_id}`, {
            method: "PUT",
            body: JSON.stringify(user_data)
        }, token);
    }

    async deleteUser(user_id: string, token: string): Promise<void> {
        return this.request<void>(`/users/${user_id}`, {
            method: "DELETE"
        }, token);
    }
}





export const apiService = new ApiService()
