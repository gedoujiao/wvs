from playwright.async_api import async_playwright
import asyncio
import logging
from typing import List, Dict
import re
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class VulnerabilityScanner:
    def __init__(self):
        self.xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
            "\"><script>alert('XSS')</script>",
        ]
        
        self.sqli_payloads = [
            "' OR '1'='1",
            "' OR 1=1--",
            "' UNION SELECT NULL--",
            "'; DROP TABLE users--",
            "' OR 'a'='a",
            "1' OR '1'='1' #",
        ]

        self.progress_callback = None  # 新增回调函数用于推送进度

    async def _log(self, message: str):
        if self.progress_callback:
            await self.progress_callback(message)
        logger.info(message)

    async def scan_website(self, url: str) -> List[Dict]:
        """扫描网站漏洞"""
        vulnerabilities = []

        await self._log(f"正在访问目标网站 {url} ...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state('networkidle')
                await self._log("页面加载完成")

                xss_vulns = await self._scan_xss(page, url)
                vulnerabilities.extend(xss_vulns)

                sqli_vulns = await self._scan_sqli(page, url)
                vulnerabilities.extend(sqli_vulns)

                csrf_vulns = await self._scan_csrf(page, url)
                vulnerabilities.extend(csrf_vulns)

            except Exception as e:
                await self._log(f"扫描错误: {str(e)}")
            finally:
                await browser.close()

        await self._log(f"扫描完成，共发现 {len(vulnerabilities)} 个漏洞")
        return vulnerabilities

    async def _scan_xss(self, page, base_url: str) -> List[Dict]:
        vulnerabilities = []
        await self._log("开始 XSS 扫描")

        try:
            inputs = await page.query_selector_all('input[type="text"], input[type="search"], textarea')

            for i, input_element in enumerate(inputs):
                for payload in self.xss_payloads:
                    await self._log(f"尝试 XSS payload: {payload}")
                    try:
                        await input_element.clear()
                        await input_element.fill(payload)

                        form = await input_element.query_selector('xpath=ancestor::form')
                        if form:
                            submit_btn = await form.query_selector('input[type="submit"], button[type="submit"], button:not([type])')
                            if submit_btn:
                                await submit_btn.click()
                                await page.wait_for_timeout(1000)

                        content = await page.content()
                        if payload in content and not self._is_encoded(payload, content):
                            await self._log(f"发现反射型 XSS 漏洞: {payload}")
                            vulnerabilities.append({
                                "type": "xss",
                                "payload": payload,
                                "location": f"Input field #{i+1}",
                                "description": f"Reflected XSS found.",
                                "severity": "high"
                            })
                            break

                        try:
                            await page.wait_for_function("window.alert && window.alert.toString().includes('[native code]')", timeout=2000)
                            await self._log("检测到执行了 JavaScript 代码，可能存在 DOM XSS")
                            vulnerabilities.append({
                                "type": "xss",
                                "payload": payload,
                                "location": f"Input field #{i+1}",
                                "description": f"Stored/DOM XSS.",
                                "severity": "critical"
                            })
                            break
                        except:
                            pass
                    except Exception as e:
                        logger.debug(f"XSS 测试失败: {payload} 错误: {str(e)}")

        except Exception as e:
            await self._log(f"XSS 扫描异常: {str(e)}")

        return vulnerabilities

    async def _scan_sqli(self, page, base_url: str) -> List[Dict]:
        vulnerabilities = []
        await self._log("开始 SQL 注入扫描")

        try:
            inputs = await page.query_selector_all('input[type="text"], input[type="search"], input[type="email"]')

            for i, input_element in enumerate(inputs):
                for payload in self.sqli_payloads:
                    await self._log(f"尝试 SQLi payload: {payload}")
                    try:
                        await input_element.clear()
                        await input_element.fill(payload)

                        form = await input_element.query_selector('xpath=ancestor::form')
                        if form:
                            submit_btn = await form.query_selector('input[type="submit"], button[type="submit"], button:not([type])')
                            if submit_btn:
                                await submit_btn.click()
                                await page.wait_for_timeout(2000)

                        content = await page.content()
                        sql_errors = ["mysql_fetch_array", "ORA-01756", "PostgreSQL", "syntax error"]

                        for error in sql_errors:
                            if error.lower() in content.lower():
                                await self._log(f"发现 SQL 错误提示: {error}")
                                vulnerabilities.append({
                                    "type": "sqli",
                                    "payload": payload,
                                    "location": f"Input field #{i+1}",
                                    "description": f"SQL Injection based on error message.",
                                    "severity": "critical"
                                })
                                break

                        if "1=1" in payload:
                            await input_element.clear()
                            false_payload = payload.replace("1=1", "1=2")
                            await input_element.fill(false_payload)
                            if form and submit_btn:
                                await submit_btn.click()
                                await page.wait_for_timeout(1000)
                            false_content = await page.content()

                            if abs(len(content) - len(false_content)) > 100:
                                await self._log("检测到布尔盲注迹象")
                                vulnerabilities.append({
                                    "type": "sqli",
                                    "payload": payload,
                                    "location": f"Input field #{i+1}",
                                    "description": "Possible Boolean-based SQL Injection.",
                                    "severity": "high"
                                })
                                break
                    except Exception as e:
                        logger.debug(f"SQLi 测试失败: {payload} 错误: {str(e)}")
        except Exception as e:
            await self._log(f"SQL 注入扫描异常: {str(e)}")

        return vulnerabilities

    async def _scan_csrf(self, page, base_url: str) -> List[Dict]:
        vulnerabilities = []
        await self._log("开始 CSRF 扫描")

        try:
            forms = await page.query_selector_all('form')

            for i, form in enumerate(forms):
                csrf_inputs = await form.query_selector_all('input[name*="csrf"], input[name*="token"], input[name*="_token"]')
                if not csrf_inputs:
                    method = await form.get_attribute('method')
                    action = await form.get_attribute('action')
                    if method and method.upper() in ['POST', 'PUT', 'DELETE']:
                        await self._log(f"表单缺少CSRF防护: Form #{i+1} ({action})")
                        vulnerabilities.append({
                            "type": "csrf",
                            "payload": "No CSRF token found",
                            "location": f"Form #{i+1} (action: {action or 'current page'})",
                            "description": f"Form lacks CSRF protection. Method: {method.upper()}",
                            "severity": "medium"
                        })
        except Exception as e:
            await self._log(f"CSRF 扫描异常: {str(e)}")

        return vulnerabilities

    def _is_encoded(self, payload: str, content: str) -> bool:
        encoded_chars = {
            '<': ['&lt;', '%3C'],
            '>': ['&gt;', '%3E'],
            '"': ['&quot;', '%22'],
            "'": ['&#x27;', '%27'],
            '&': ['&amp;', '%26']
        }

        for char, encodings in encoded_chars.items():
            if char in payload:
                for encoding in encodings:
                    if encoding in content:
                        return True
        return False
