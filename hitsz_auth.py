import requests
from bs4 import BeautifulSoup
import base64
import json
import os
import time
from color_print import ColorPrint


class HITSZAuth:

    def __init__(self, username=None, password=None, service_url=None):
        self.session = requests.Session()
        self.base_url = "https://ids.hit.edu.cn"
        self.service_url = service_url or "http://jw.hitsz.edu.cn/casLogin"
        self.cookies_file = "hitsz_cookies.json"
        self.username = username
        self.password = password
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def get_login_page(self):
        ColorPrint.process("访问统一身份认证登录页面...")
        login_url = f"{self.base_url}/authserver/login"
        params = {"service": self.service_url}

        try:
            response = self.session.get(
                login_url, params=params, headers=self.headers, timeout=10
            )
            if response.status_code == 200:
                ColorPrint.success("成功获取登录页面")
                return response.text
            else:
                ColorPrint.error(f"访问登录页面失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            ColorPrint.error(f"访问登录页面异常: {e}")
            return None

    def extract_login_params(self, html_content):
        ColorPrint.process("解析登录页面参数...")

        try:
            soup = BeautifulSoup(html_content, "html.parser")
            login_form = soup.find("form", id="pwdFromId")

            if not login_form:
                ColorPrint.error("未找到登录表单")
                return None

            params = {}
            for input_tag in login_form.find_all("input", type="hidden"):
                if input_tag.get("name"):
                    params[input_tag["name"]] = input_tag.get("value", "")

            # 提取公钥盐值
            pwd_encrypt_salt = login_form.find("input", id="pwdEncryptSalt")
            if pwd_encrypt_salt and pwd_encrypt_salt.get("value"):
                params["pwdEncryptSalt"] = pwd_encrypt_salt.get("value")

            # 验证必要参数
            required_params = ["execution", "lt", "_eventId", "cllt", "dllt"]
            if not all(param in params for param in required_params):
                ColorPrint.error("缺少必要的登录参数")
                return None

            ColorPrint.success("登录参数解析成功")
            return params

        except Exception as e:
            ColorPrint.error(f"解析登录页面失败: {e}")
            return None

    def encrypt_password_with_aes(self, password, salt):
        try:
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import pad
            import random

            def random_string(length):
                chars = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"
                return "".join(random.choice(chars) for _ in range(length))

            if not salt:
                ColorPrint.warning("未找到加密盐值，使用原密码")
                return password

            random_prefix = random_string(64)
            iv = random_string(16).encode("utf-8")
            plaintext = random_prefix + password

            key = salt.encode("utf-8")
            cipher = AES.new(key[:32], AES.MODE_CBC, iv[:16])
            padded_data = pad(plaintext.encode("utf-8"), AES.block_size)
            encrypted = cipher.encrypt(padded_data)

            encrypted_password = base64.b64encode(encrypted).decode("utf-8")
            ColorPrint.success("密码AES加密成功")
            return encrypted_password

        except ImportError:
            ColorPrint.warning("未安装pycryptodome库，使用原密码")
            return password
        except Exception as e:
            ColorPrint.warning(f"AES加密失败，使用原密码: {e}")
            return password

    def perform_login(self, username, password, login_params):
        ColorPrint.process("提交统一身份认证信息...")
        login_url = f"{self.base_url}/authserver/login"

        # 加密密码
        encrypted_pwd = self.encrypt_password_with_aes(
            password, login_params.get("pwdEncryptSalt", "")
        )

        login_data = {
            "username": username,
            "password": encrypted_pwd,
            "_eventId": login_params["_eventId"],
            "cllt": login_params["cllt"],
            "dllt": login_params["dllt"],
            "lt": login_params["lt"],
            "execution": login_params["execution"],
            "rememberMe": "true",
        }

        params = {"service": self.service_url}
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": f"{self.base_url}/authserver/login?service={self.service_url}",
            "Origin": self.base_url,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            response = self.session.post(
                login_url,
                params=params,
                data=login_data,
                headers=headers,
                allow_redirects=False,
                timeout=15,
            )

            if response.status_code == 302:
                redirect_url = response.headers.get("Location")
                ColorPrint.info(f"收到重定向: {redirect_url[:50]}...")

                if redirect_url and "ticket=" in redirect_url:
                    ColorPrint.success("统一身份认证成功")
                    # 访问目标服务获取Cookie
                    ColorPrint.process("访问目标服务获取Cookie...")
                    target_response = self.session.get(
                        redirect_url,
                        headers=self.headers,
                        allow_redirects=False,
                        timeout=15,
                    )

                    if target_response.status_code == 200:
                        ColorPrint.success("目标服务访问成功")
                        return True
                    elif target_response.status_code == 301:
                        # 处理301重定向
                        ColorPrint.warning("目标服务被永久重定向")
                        new_url = target_response.headers.get("Location")
                        if new_url:
                            ColorPrint.info(f"重定向到: {new_url}")
                            target_response = self.session.get(
                                new_url, headers=self.headers, timeout=15
                            )
                            if target_response.status_code == 200:
                                ColorPrint.success("重定向访问成功")
                                return True
                            else:
                                ColorPrint.error(
                                    f"重定向访问失败，状态码: {target_response.status_code}"
                                )
                                return False
                    else:
                        ColorPrint.error(
                            f"目标服务访问失败，状态码: {target_response.status_code}"
                        )
                        return False
                else:
                    ColorPrint.error("重定向URL中没有找到ticket参数")
                    return False
            else:
                if "您提供的用户名或者密码有误" in response.text:
                    ColorPrint.error("账号或密码错误")
                elif "验证码" in response.text:
                    ColorPrint.error("需要验证码，请稍后重试")
                else:
                    ColorPrint.error(
                        f"统一身份认证失败，状态码: {response.status_code}"
                    )
                return False

        except Exception as e:
            ColorPrint.error(f"统一身份认证异常: {e}")
            return False

    def login(self, username=None, password=None, service_url=None):
        if username:
            self.username = username
        if password:
            self.password = password
        if service_url:
            self.service_url = service_url

        if not self.username or not self.password:
            ColorPrint.error("需要用户名和密码进行登录")
            return False

        ColorPrint.subheader(f"统一身份认证登录", style="bracket")
        ColorPrint.info(f"目标服务: {self.service_url}")

        # 获取登录页面
        login_page = self.get_login_page()
        if not login_page:
            return False

        # 解析登录参数
        login_params = self.extract_login_params(login_page)
        if not login_params:
            return False

        # 执行登录
        if self.perform_login(self.username, self.password, login_params):
            self.save_cookies()
            ColorPrint.success("🎉 统一身份认证登录成功！")
            return True
        else:
            ColorPrint.error("统一身份认证登录失败")
            return False

    def auto_reconnect(self):
        if not self.username or not self.password:
            ColorPrint.error("无法自动重连：缺少用户名或密码")
            return False

        ColorPrint.warning("检测到会话失效，开始自动重连...")

        # 重置session
        self.session = requests.Session()

        for attempt in range(3):
            ColorPrint.process(f"第 {attempt + 1} 次尝试重新登录...")
            if self.login(self.username, self.password):
                ColorPrint.success("自动重新登录成功！")
                return True
            if attempt < 2:
                ColorPrint.info("等待2秒后重试...")
                time.sleep(2)

        ColorPrint.error("自动重连失败，已达到最大重试次数")
        return False

    def save_cookies(self, custom_file=None):
        try:
            cookies_file = custom_file or self.cookies_file
            cookies = {cookie.name: cookie.value for cookie in self.session.cookies}

            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)

            ColorPrint.success(f"Cookies已保存到: {cookies_file}")
            return True
        except Exception as e:
            ColorPrint.error(f"保存Cookies失败: {e}")
            return False

    def load_cookies(self, custom_file=None):
        cookies_file = custom_file or self.cookies_file

        if not os.path.exists(cookies_file):
            ColorPrint.warning(f"Cookies文件不存在: {cookies_file}")
            return False

        try:
            with open(cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            self.session.cookies.update(cookies)
            ColorPrint.success(f"Cookies已从 {cookies_file} 加载")
            return True
        except Exception as e:
            ColorPrint.error(f"加载Cookies失败: {e}")
            return False

    def test_cookie(self, test_url=None):
        ColorPrint.process("测试Cookie有效性...")

        # 默认测试URL
        if not test_url:
            test_url = "http://jw.hitsz.edu.cn/authentication/main"

        try:
            response = self.session.get(
                test_url, headers=self.headers, timeout=10, allow_redirects=False
            )

            # 检查是否被重定向到登录页面
            if response.status_code == 302 and "authserver" in response.headers.get(
                "Location", ""
            ):
                ColorPrint.warning("Cookie已失效，需要重新登录")
                return False
            elif "require" in response.url or "invalid" in response.url:
                ColorPrint.warning("Cookie无效")
                return False
            elif response.status_code == 200:
                ColorPrint.success("Cookie有效")
                return True
            else:
                ColorPrint.warning(f"未知状态，状态码: {response.status_code}")
                return False

        except Exception as e:
            ColorPrint.error(f"测试Cookie异常: {e}")
            return False

    def logout(self):
        ColorPrint.process("执行统一身份认证注销...")

        logout_url = f"{self.base_url}/authserver/logout"

        try:
            response = self.session.get(logout_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                ColorPrint.success("统一身份认证注销成功")

                # 清除cookies文件
                if os.path.exists(self.cookies_file):
                    os.remove(self.cookies_file)
                    ColorPrint.info("已清除本地Cookies文件")

                return True
            else:
                ColorPrint.error("统一身份认证注销失败")
                return False
        except Exception as e:
            ColorPrint.error(f"统一身份认证注销异常: {e}")
            return False

    def get_session(self):
        return self.session

    def set_service_url(self, service_url):
        self.service_url = service_url
        ColorPrint.info(f"目标服务已设置为: {service_url}")

    def get_user_info(self):
        return {
            "username": self.username,
            "service_url": self.service_url,
            "base_url": self.base_url,
            "cookies_file": self.cookies_file,
        }


class HITSZJwxtAuth(HITSZAuth):
    def __init__(self, username=None, password=None):
        super().__init__(username, password, "http://jw.hitsz.edu.cn/casLogin")
        self.cookies_file = "hitsz_jwxt_cookies.json"

    def test_cookie(self):
        return super().test_cookie("http://jw.hitsz.edu.cn/authentication/main")


# 统一身份认证不知道为什么无法使用
class HITSZNetworkAuth(HITSZAuth):
    def __init__(self, username=None, password=None):
        # 修正service_url - 这个是统一身份认证的重定向目标
        super().__init__(username, password, "http://10.248.98.2/srun_portal_sso")
        self.cookies_file = "hitsz_network_cookies.json"
        self.network_base_url = "https://net.hitsz.edu.cn"
        self.current_ticket = None

    def perform_login(self, username, password, login_params):
        """重写登录方法，添加校园网认证流程"""
        ColorPrint.process("提交统一身份认证信息...")
        login_url = f"{self.base_url}/authserver/login"

        # 加密密码
        encrypted_pwd = self.encrypt_password_with_aes(
            password, login_params.get("pwdEncryptSalt", "")
        )

        login_data = {
            "username": username,
            "password": encrypted_pwd,
            "_eventId": login_params["_eventId"],
            "cllt": login_params["cllt"],
            "dllt": login_params["dllt"],
            "lt": login_params["lt"],
            "execution": login_params["execution"],
            "rememberMe": "true",
        }

        params = {"service": self.service_url}
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": f"{self.base_url}/authserver/login?service={self.service_url}",
            "Origin": self.base_url,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            response = self.session.post(
                login_url,
                params=params,
                data=login_data,
                headers=headers,
                allow_redirects=False,
                timeout=15,
            )

            if response.status_code == 302:
                redirect_url = response.headers.get("Location")
                ColorPrint.info(f"收到重定向: {redirect_url[:50]}...")

                if redirect_url and "ticket=" in redirect_url:
                    # 提取ticket
                    import re

                    ticket_match = re.search(r"ticket=([^&]+)", redirect_url)
                    if ticket_match:
                        self.current_ticket = ticket_match.group(1)
                        ColorPrint.success(
                            f"获取到ticket: {self.current_ticket[:20]}..."
                        )

                    ColorPrint.success("统一身份认证成功")

                    # 先访问重定向URL获取基础cookie
                    ColorPrint.process("访问校园网认证页面...")
                    initial_response = self.session.get(
                        redirect_url,
                        headers=self.headers,
                        allow_redirects=True,
                        timeout=15,
                    )

                    if initial_response.status_code == 200:
                        ColorPrint.success("校园网认证页面访问成功")
                        # 执行完整的校园网认证流程
                        return self.complete_srun_authentication()
                    else:
                        ColorPrint.error(
                            f"校园网认证页面访问失败，状态码: {initial_response.status_code}"
                        )
                        return False
                else:
                    ColorPrint.error("重定向URL中没有找到ticket参数")
                    return False
            else:
                if "您提供的用户名或者密码有误" in response.text:
                    ColorPrint.error("账号或密码错误")
                elif "验证码" in response.text:
                    ColorPrint.error("需要验证码，请稍后重试")
                else:
                    ColorPrint.error(
                        f"统一身份认证失败，状态码: {response.status_code}"
                    )
                return False

        except Exception as e:
            ColorPrint.error(f"统一身份认证异常: {e}")
            return False

    def complete_srun_authentication(self):
        """完成SRUN校园网认证的完整流程"""
        if not self.current_ticket:
            ColorPrint.error("缺少认证票据")
            return False

        # 步骤1: 执行srun_portal_sso验证
        if not self.srun_portal_sso_verification():
            return False

        # 步骤2: 访问srun_portal_success
        if not self.srun_portal_success():
            return False

        # 步骤3: 访问srun_portal_detect
        if not self.srun_portal_detect():
            return False

        ColorPrint.success("校园网SRUN认证流程完成")
        return True

    def srun_portal_detect(self):
        """执行srun_portal_detect检测 - 对应第三个fetch请求"""
        ColorPrint.process("执行校园网状态检测...")

        detect_url = f"{self.network_base_url}/v1/srun_portal_detect"

        headers = {
            **self.headers,
            "X-Requested-With": "XMLHttpRequest",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": f"{self.network_base_url}/srun_portal_success?ac_id=1",
        }

        try:
            response = self.session.get(detect_url, headers=headers, timeout=15)

            if response.status_code == 200:
                ColorPrint.success("校园网状态检测成功")
                # 检查响应内容
                try:
                    result = response.json() if response.content else {}
                    if result:
                        ColorPrint.info(f"检测结果: {result}")
                        # 可以根据返回结果判断网络状态
                        if isinstance(result, dict):
                            if result.get("message") == "success":
                                ColorPrint.success("网络状态正常")
                except:
                    ColorPrint.info("状态检测完成")
                return True
            else:
                ColorPrint.error(f"校园网状态检测失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            ColorPrint.error(f"校园网状态检测异常: {e}")
            return False

    def srun_portal_sso_verification(self):
        ColorPrint.process("执行SRUN单点登录验证...")

        sso_url = f"{self.network_base_url}/v1/srun_portal_sso"
        params = {"ticket": self.current_ticket}

        headers = {
            **self.headers,
            "X-Requested-With": "XMLHttpRequest",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": f"{self.network_base_url}/srun_portal_sso?ticket={self.current_ticket}",
        }
        try:
            response = self.session.get(
                sso_url, params=params, headers=headers, timeout=15
            )
            if response.status_code == 200:
                ColorPrint.success("SRUN单点登录验证成功")
                # 检查响应内容
                try:
                    result = response.json() if response.content else {}
                    if result:
                        ColorPrint.info(f"验证结果: {result}")
                except:
                    ColorPrint.info("验证成功，获得认证状态")
                return True
            else:
                ColorPrint.error(
                    f"SRUN单点登录验证失败，状态码: {response.status_code}"
                )
                return False

        except Exception as e:
            ColorPrint.error(f"SRUN单点登录验证异常: {e}")
            return False

    def srun_portal_success(self):
        ColorPrint.process("完成校园网认证确认...")

        success_url = f"{self.network_base_url}/srun_portal_success"
        params = {"ac_id": "1"}

        headers = {
            **self.headers,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
            "Referer": f"{self.network_base_url}/srun_portal_sso?ticket={self.current_ticket}",
        }

        try:
            response = self.session.get(
                success_url, params=params, headers=headers, timeout=15
            )

            if response.status_code == 200:
                ColorPrint.success("校园网认证确认成功")
                return True
            else:
                ColorPrint.error(f"校园网认证确认失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            ColorPrint.error(f"校园网认证确认异常: {e}")
            return False

    def test_cookie(self):
        """测试校园网认证状态"""
        ColorPrint.process("测试校园网认证状态...")
        # 直接测试网络连通性
        return self.check_network_status()

    def check_network_status(self):
        ColorPrint.process("检查网络连接状态...")
        try:
            response = requests.get("https://www.baidu.com", timeout=5)
            if response.status_code == 200:
                ColorPrint.success("网络连接正常，已联网")
                return True
            else:
                ColorPrint.warning("网络连接异常")
                return False
        except:
            ColorPrint.warning("无法访问外网，需要校园网认证")
            return False
