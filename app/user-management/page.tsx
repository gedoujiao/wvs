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

    const handleUpdateUser = async (user_id: string, user_data: UserUpdate) => {
        if (!token) return;
        setIsLoading(true);
        try {
            await apiService.updateUser(user_id, user_data, token);
            // 更新用户列表
            const updatedUsers = users.map(user => user.id === user_id ? { ...user, ...user_data } : user);
            setUsers(updatedUsers);
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

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
            <div className="w-full max-w-7xl">
                <div className="text-center mb-8">
                    <h1 className="text-2xl font-bold text-gray-900">用户管理</h1>
                    <p className="text-gray-600 mt-2">管理系统中的所有用户</p>
                </div>

                {error && (
                    <Alert variant="destructive">
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

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
                                            <Button onClick={() => handleUpdateUser(user.id, { email: "newemail@example.com" })}>修改</Button>
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