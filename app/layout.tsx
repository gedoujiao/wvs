import type React from "react";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/auth-context";
import { Toaster } from "@/components/ui/toaster";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Web漏洞挖掘系统",
    description: "面向开发者与安全测试人员的Web漏洞挖掘平台",
    generator: 'v0.dev'
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="zh-CN">
            <body className={inter.className}>
                <AuthProvider>
                    <header className="bg-white shadow-sm border-b">
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                            <div className="flex justify-between items-center py-4">
                                <div className="flex items-center">
                                    <Link href="/">
                                        <span className="text-xl font-bold text-gray-900">Web漏洞挖掘系统</span>
                                    </Link>
                                </div>
                                <div className="flex space-x-4">
                                    <Link href="/dashboard">
                                        <span className="text-sm text-gray-600 hover:text-blue-600">控制台</span>
                                    </Link>
                                    {/* 添加用户管理页面的导航链接 */}
                                    <Link href="/user-management">
                                        <span className="text-sm text-gray-600 hover:text-blue-600">用户管理</span>
                                    </Link>
                                </div>
                            </div>
                        </div>
                    </header>
                    {children}
                    <Toaster />
                </AuthProvider>
            </body>
        </html>
    );
}