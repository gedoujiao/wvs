"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/auth-context";
import { apiService } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Shield, Loader2 } from "lucide-react";
import Link from "next/link";

interface UserResponse {
    id: string;
    email: string;
    is_admin: boolean;
    created_at: string;
}

interface UserUpdate {
    email?: string;
    password?: string;
}
const [isAddingUser, setIsAddingUser] = useState(false);
const [newUserEmail, setNewUserEmail] = useState('');
const [newUserPassword, setNewUserPassword] = useState('');

export default function UserManagementPage() {
    const { user, token } = useAuth();

    // 权限检查
    if (!user || !user.is_admin) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
                <div className="w-full max-w-md">
                    <Alert variant="destructive">
                        <AlertDescription>只有管理员可以访问此页面</AlertDescription>
                    </Alert>
                </div>
            </div>
        );
    }

    const [users, setUsers] = useState<UserResponse[]>([]);
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        const fetchUsers = async () => {
            if (!user || !user.is_admin || !token) return;
            setIsLoading(true);
            try {
                const response = await apiService.getUsers(token);
                setUsers(response);
            } catch (err) {
                setError(err instanceof Error ? err.message : "获取用户列表失败");
            } finally {
                setIsLoading(false);
            }
        };
        fetchUsers();
    }, [user, token]);
    const [updateEmail, setUpdateEmail] = useState('');
    const [updatePassword, setUpdatePassword] = useState('');

    const handleUpdateUser = async (user_id: string) => {
        if (!token) return;
        setIsLoading(true);

        const user_data: UserUpdate = {};
        if (updateEmail) {
            user_data.email = updateEmail;
        }
        if (updatePassword) {
            user_data.password = updatePassword;
        }

        try {
            await apiService.updateUser(user_id, user_data, token);
            // 更新用户列表
            const updatedUsers = users.map(user => user.id === user_id ? { ...user, ...user_data } : user);
            setUsers(updatedUsers);
            // 清空输入框
            setUpdateEmail('');
            setUpdatePassword('');
        } catch (err) {
            setError(err instanceof Error ? err.message : "更新用户信息失败");
        } finally {
            setIsLoading(false);
        }
    };

    const handleDeleteUser = async (user_id: string) => {
        if (!token) return;
        setIsLoading(true);
        try {
            await apiService.deleteUser(user_id, token);
            // 更新用户列表
            const updatedUsers = users.filter(user => user.id !== user_id);
            setUsers(updatedUsers);
        } catch (err) {
            setError(err instanceof Error ? err.message : "删除用户失败");
        } finally {
            setIsLoading(false);
        }
    };

    const handleAddUser = async () => {
        if (!token) {
            console.error('Token 为空，无法添加用户');
            return;
        }
        setIsLoading(true);
        try {
            console.log('开始添加用户，邮箱:', newUserEmail, '密码:', newUserPassword);
            await apiService.register(newUserEmail, newUserPassword);
            console.log('用户添加成功');
            // 重新加载用户列表
            const response = await apiService.getUsers(token);
            setUsers(response);
            setIsAddingUser(false);
            setNewUserEmail('');
            setNewUserPassword('');
        } catch (err) {
            console.error('添加用户失败:', err);
            setError(err instanceof Error ? err.message : "添加用户失败");
        } finally {
            setIsLoading(false);
        }
    };
    const [isViewingUser, setIsViewingUser] = useState(false);
    const [viewedUser, setViewedUser] = useState<UserResponse | null>(null);

// 添加查看用户信息的处理函数
    const handleViewUser = (user: UserResponse) => {
        setViewedUser(user);
        setIsViewingUser(true);
    };

// 在返回的 JSX 中添加“添加用户”按钮和表单
 return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
            <div className="w-full max-w-7xl">
                {/* ... 其他代码 ... */}
                <Card>
                    <CardHeader>
                        <CardTitle>用户列表</CardTitle>
                        <CardDescription>查看、修改和删除系统用户</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <table className="w-full">
                            <thead>
                                <tr>
                                    <th className="px-4 py-2">ID</th>
                                    <th className="px-4 py-2">邮箱</th>
                                    <th className="px-4 py-2">是否为管理员</th>
                                    <th className="px-4 py-2">操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map(user => (
                                    <tr key={user.id}>
                                        <td className="px-4 py-2">{user.id}</td>
                                        <td className="px-4 py-2">{user.email}</td>
                                        <td className="px-4 py-2">{user.is_admin ? "是" : "否"}</td>
                                        <td className="px-4 py-2">
                                            {/* 添加表单 */}
                                            <form onSubmit={(e) => {
                                                e.preventDefault();
                                                handleUpdateUser(user.id);
                                            }}>
                                                <input
                                                    type="email"
                                                    placeholder="新邮箱"
                                                    value={updateEmail}
                                                    onChange={(e) => setUpdateEmail(e.target.value)}
                                                />
                                                <input
                                                    type="password"
                                                    placeholder="新密码"
                                                    value={updatePassword}
                                                    onChange={(e) => setUpdatePassword(e.target.value)}
                                                />
                                                <button type="submit">修改</button>
                                            </form>
                                            <Button onClick={() => handleDeleteUser(user.id)}>删除</Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </CardContent>
                </Card>
            </div>
        </div>
    );

}