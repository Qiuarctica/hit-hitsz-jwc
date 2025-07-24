import time
import json
import hashlib
import hmac
import base64
import math
import socket
import threading
import schedule
from typing import Union
from urllib.parse import urlencode
from datetime import datetime
from color_print import ColorPrint
import requests
import platform


class HITSZNetAuth:
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.ip = None
        self.cookies_file = "hitsz_net_cookies.json"
        self.session = requests.Session()
        # SRUN认证参数
        self.base_url = "https://net.hitsz.edu.cn"
        self.callback = "jQueryCallback"
        self.UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        # 加密常量
        self.TYPE = "1"
        self.N = "200"
        self.ENC = "srun_bx1"
        self.ACID = "1"

        # 长期使用相关
        self.long_term_mode = False
        self.scheduler_thread = None
        self.is_running = False
        self.auto_approve_ip = False  # 长期模式下自动同意IP

    def get_local_ip(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                if not self.long_term_mode:
                    ColorPrint.success(f"自动获取到本机IP: {local_ip}")
                return local_ip
        except:
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip != "127.0.0.1":
                    if not self.long_term_mode:
                        ColorPrint.success(f"通过hostname获取到IP: {local_ip}")
                    return local_ip
            except:
                pass

        try:
            import netifaces

            for interface in netifaces.interfaces():
                if (
                    interface.startswith("以太网")
                    or interface.startswith("WLAN")
                    or interface.startswith("eth")
                    or interface.startswith("wlan")
                ):
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        for addr in addrs[netifaces.AF_INET]:
                            ip = addr["addr"]
                            if not ip.startswith("127.") and not ip.startswith(
                                "169.254"
                            ):
                                if not self.long_term_mode:
                                    ColorPrint.success(f"从网络接口获取到IP: {ip}")
                                return ip
        except ImportError:
            if not self.long_term_mode:
                ColorPrint.warning("未安装netifaces库，跳过网络接口方法")
        except:
            pass

        if not self.long_term_mode:
            ColorPrint.warning("无法自动获取IP地址")
        return None

    def get_ip_address(self, auto_mode=False):
        """获取IP地址，auto_mode为True时自动使用检测到的IP"""
        if not self.ip:
            if not self.long_term_mode:
                ColorPrint.process("正在获取IP地址...")
            auto_ip = self.get_local_ip()

            if auto_ip:
                # 长期模式或者auto_mode下自动使用检测到的IP
                if self.long_term_mode or auto_mode or self.auto_approve_ip:
                    self.ip = auto_ip
                    if not self.long_term_mode:
                        ColorPrint.info(f"自动使用检测到的IP: {auto_ip}")
                    return self.ip
                else:
                    use_auto = ColorPrint.ask_yes_no(
                        f"检测到IP地址 {auto_ip}，是否使用？", default=True
                    )
                    if use_auto:
                        self.ip = auto_ip
                        return self.ip

            # 只有在非长期模式下才请求手动输入
            if not self.long_term_mode and not auto_mode:
                manual_ip = ColorPrint.input_with_validation(
                    "请手动输入IP地址",
                    validator=self.validate_ip,
                    error_msg="请输入有效的IP地址",
                )
                self.ip = manual_ip
            else:
                ColorPrint.error("无法获取IP地址，长期模式下无法继续")
                return None

        return self.ip

    def validate_ip(self, ip):
        try:
            parts = ip.split(".")
            if len(parts) != 4:
                return False
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            return True
        except:
            return False

    def hmd5(self, msg: str, key: str) -> str:
        msg = msg.encode()
        key = key.encode()
        return hmac.new(key, msg, hashlib.md5).hexdigest()

    def sha1(self, msg: str) -> str:
        return hashlib.sha1(msg.encode()).hexdigest()

    def chkstr(
        self,
        token: str,
        username: str,
        hmd5: str,
        ac_id: str,
        ip: str,
        n: str,
        type_: str,
        info: str,
    ) -> str:
        result = token + username
        result += token + hmd5
        result += token + ac_id
        result += token + ip
        result += token + n
        result += token + type_
        result += token + info
        return result

    def trans_b64encode(self, s: str, alpha: Union[str, None] = None) -> str:
        result = base64.b64encode(s.encode(encoding="latin-1")).decode()
        if not alpha:
            return result
        assert len(alpha) == 64, "base64字母表的长度必须为64"
        table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        trans_table = str.maketrans(table, alpha)
        return result.translate(trans_table)

    class String(str):
        def charCodeAt(self, i: int) -> int:
            if len(self) > i:
                return ord(self[i])
            return 0

        @classmethod
        def fromCharCode(cls, *charCodes: list[int]) -> str:
            result = ""
            for c in charCodes:
                result += chr(c)
            return result

    def s(self, a, b: bool) -> list[int]:
        c = len(a)
        v = []
        for i in range(0, c, 4):
            v.append(
                a.charCodeAt(i)
                | a.charCodeAt(i + 1) << 8
                | a.charCodeAt(i + 2) << 16
                | a.charCodeAt(i + 3) << 24
            )
        if b:
            v.append(c)
        return v

    def l(self, a: list[int], b: bool):
        d = len(a)
        c = (d - 1) << 2
        if b:
            m = a[d - 1]
            if m < c - 3 or m > c:
                return None
            c = m
        for i in range(0, d):
            a[i] = self.String.fromCharCode(
                a[i] & 0xFF, a[i] >> 8 & 0xFF, a[i] >> 16 & 0xFF, a[i] >> 24 & 0xFF
            )
        return "".join(a)[0:c] if b else "".join(a)

    def xxtea(self, str_: str, key: str) -> str:
        str_, key = self.String(str_), self.String(key)

        if str_ == "":
            return ""
        v = self.s(str_, True)
        k = self.s(key, False)
        if len(k) < 4:
            k = k + [0] * (4 - len(k))
        n = len(v) - 1
        z = v[n]
        y = v[0]
        c = 0x86014019 | 0x183639A0
        m = 0
        e = 0
        p = 0
        q = math.floor(6 + 52 / (n + 1))
        d = 0
        while 0 < q:
            d = d + c & (0x8CE0D9BF | 0x731F2640)
            e = d >> 2 & 3
            p = 0
            while p < n:
                y = v[p + 1]
                m = z >> 5 ^ y << 2
                m += y >> 3 ^ z << 4 ^ (d ^ y)
                m += k[p & 3 ^ e] ^ z
                z = v[p] = v[p] + m & (0xEFB8D130 | 0x10472ECF)
                p += 1
            y = v[0]
            m = z >> 5 ^ y << 2
            m += y >> 3 ^ z << 4 ^ (d ^ y)
            m += k[p & 3 ^ e] ^ z
            z = v[n] = v[n] + m & (0xBB390742 | 0x44C6F8BD)
            q -= 1
        return self.l(v, False)

    def info_(self, info: dict, token: str) -> str:
        alpha = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"
        json_data = json.dumps(info).replace(" ", "")
        result = self.trans_b64encode(self.xxtea(json_data, token), alpha)
        return f"{{SRBX1}}{result}"

    def get_challenge(self):
        if not self.long_term_mode:
            ColorPrint.process("获取认证challenge...")

        if not self.ip:
            self.get_ip_address(auto_mode=True)

        params = urlencode(
            {"callback": self.callback, "username": self.username, "ip": self.ip}
        )

        try:
            resp = self.session.get(
                url=f"{self.base_url}/cgi-bin/get_challenge?{params}",
                headers={"User-Agent": self.UA},
                timeout=10,
            )

            if resp.status_code == 200:
                get_challenge = resp.text[len(self.callback) + 1 : -1]
                token = json.loads(get_challenge)["challenge"]
                if not self.long_term_mode:
                    ColorPrint.success(f"获取challenge成功: {token[:20]}...")
                return token
            else:
                if not self.long_term_mode:
                    ColorPrint.error(f"获取challenge失败，状态码: {resp.status_code}")
                return None

        except Exception as e:
            if not self.long_term_mode:
                ColorPrint.error(f"获取challenge异常: {e}")
            return None

    def get_os(self):
        os_name = platform.system()
        if os_name == "Windows":
            return "Windows"
        elif os_name == "Linux":
            return "Linux"
        elif os_name == "Darwin":
            return "macOS"
        else:
            return "Windows"

    def srun_login(self):
        if not self.long_term_mode:
            ColorPrint.process("执行SRUN校园网登录...")

        # 获取challenge
        token = self.get_challenge()
        if not token:
            return False
        # 加密密码
        hmd5_password = self.hmd5(self.password, token)
        # 生成info字段
        info = self.info_(
            {
                "username": self.username,
                "password": self.password,
                "ip": self.ip,
                "acid": self.ACID,
                "enc_ver": self.ENC,
            },
            token,
        )
        # 生成校验和
        chksum = self.sha1(
            self.chkstr(
                token,
                self.username,
                hmd5_password,
                self.ACID,
                self.ip,
                self.N,
                self.TYPE,
                info,
            )
        )
        # 获取操作系统信息
        os_name = self.get_os()
        # 构建登录参数
        params = urlencode(
            {
                "callback": self.callback,
                "action": "login",
                "username": self.username,
                "password": "{MD5}" + hmd5_password,
                "os": os_name,
                "name": os_name,
                "nas_ip": "",
                "double_stack": 0,
                "chksum": chksum,
                "info": info,
                "ac_id": self.ACID,
                "ip": self.ip,
                "n": self.N,
                "type": self.TYPE,
                "captchaVal": "",
                "_": int(time.time() * 1000),
            }
        )
        try:
            resp = self.session.get(
                url=f"{self.base_url}/cgi-bin/srun_portal?{params}",
                headers={"User-Agent": self.UA},
                timeout=15,
            )
            if resp.status_code == 200:
                result_text = resp.text[len(self.callback) + 1 : -1]
                result = json.loads(result_text)

                if result.get("res") == "ok":
                    if not self.long_term_mode:
                        ColorPrint.success("SRUN校园网登录成功")
                    return True
                else:
                    error_msg = result.get("error", "未知错误")
                    if not self.long_term_mode:
                        ColorPrint.error(f"SRUN登录失败: {error_msg}")
                    return False
            else:
                if not self.long_term_mode:
                    ColorPrint.error(f"SRUN登录请求失败，状态码: {resp.status_code}")
                return False

        except Exception as e:
            if not self.long_term_mode:
                ColorPrint.error(f"SRUN登录异常: {e}")
            return False

    def check_network_status(self):
        if not self.long_term_mode:
            ColorPrint.process("检查网络连接状态...")

        test_urls = [
            "https://www.baidu.com",
        ]

        for url in test_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    if not self.long_term_mode:
                        ColorPrint.success("网络连接正常，已联网")
                    return True
            except:
                continue

        if not self.long_term_mode:
            ColorPrint.warning("无法访问外网，需要校园网认证")
        return False

    def login(self, username=None, password=None):
        if username:
            self.username = username
        if password:
            self.password = password

        if not self.username or not self.password:
            if not self.long_term_mode:
                ColorPrint.error("用户名或密码未设置")
            return False

        return self.srun_login()

    def auto_reconnect(self, max_attempts=3):
        ColorPrint.subheader(
            f"自动重连检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            style="bracket",
        )

        # 首先检查网络状态
        if self.check_network_status():
            ColorPrint.success("网络连接正常，无需重连")
            return True

        ColorPrint.warning("检测到网络断开，开始自动重连...")

        for attempt in range(1, max_attempts + 1):
            ColorPrint.info(f"第 {attempt}/{max_attempts} 次重连尝试")

            try:
                # 重新获取IP（可能IP发生了变化）
                old_ip = self.ip
                self.ip = None
                # 在长期模式下自动获取IP
                new_ip = self.get_ip_address(auto_mode=True)
                if new_ip and new_ip != old_ip:
                    ColorPrint.info(f"IP地址已更新: {old_ip} -> {new_ip}")
                # 执行登录
                if self.login():
                    ColorPrint.success(f"第 {attempt} 次重连成功！")
                    # 等待网络生效
                    time.sleep(3)
                    # 验证连接
                    if self.check_network_status():
                        ColorPrint.success("网络重连验证成功")
                        return True
                    else:
                        ColorPrint.warning("认证成功但网络验证失败，继续下次尝试")
                else:
                    ColorPrint.error(f"第 {attempt} 次重连失败")

            except Exception as e:
                ColorPrint.error(f"第 {attempt} 次重连异常: {e}")
            # 如果不是最后一次尝试，等待一段时间再重试
            if attempt < max_attempts:
                ColorPrint.info("等待30秒后重试...")
                time.sleep(30)
        ColorPrint.error(f"所有 {max_attempts} 次重连尝试均失败")
        return False

    def scheduled_check(self):
        try:
            self.auto_reconnect(max_attempts=3)
        except Exception as e:
            ColorPrint.error(f"定时检查异常: {e}")

    def start_long_term_service(self, check_interval_hours=1):
        if self.long_term_mode:
            ColorPrint.warning("长期服务已在运行中")
            return

        self.long_term_mode = True
        self.is_running = True
        self.auto_approve_ip = True  # 长期模式下自动同意IP

        ColorPrint.success(
            f"启动长期服务模式，每 {check_interval_hours} 小时检查一次网络状态"
        )

        # 清空之前的任务
        schedule.clear()
        # 设置定时任务
        schedule.every(check_interval_hours).hours.do(self.scheduled_check)
        # 立即执行一次检查
        ColorPrint.info("执行初始网络检查...")
        self.auto_reconnect(max_attempts=3)
        # 启动调度器线程
        self.scheduler_thread = threading.Thread(
            target=self._run_scheduler, daemon=True
        )
        self.scheduler_thread.start()
        ColorPrint.success("长期服务模式已启动")

    def _run_scheduler(self):
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次是否有待执行的任务
            except Exception as e:
                ColorPrint.error(f"调度器运行异常: {e}")
                time.sleep(60)

    def stop_long_term_service(self):
        if not self.long_term_mode:
            ColorPrint.warning("长期服务未在运行")
            return

        ColorPrint.info("正在停止长期服务模式...")
        self.is_running = False
        self.long_term_mode = False
        self.auto_approve_ip = False
        # 清空定时任务
        schedule.clear()
        # 等待线程结束
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        ColorPrint.success("长期服务模式已停止")

    def get_service_status(self):
        if self.long_term_mode:
            next_run = schedule.next_run()
            if next_run:
                next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S")
                ColorPrint.info(f"长期服务运行中，下次检查时间: {next_run_str}")
            else:
                ColorPrint.info("长期服务运行中")
            return True
        else:
            ColorPrint.info("长期服务未运行")
            return False

    def long_term_work(self):
        check_interval = ColorPrint.input_with_validation(
            "请输入检查间隔（小时，默认1小时）",
            validator=lambda x: x == "" or (x.isdigit() and 1 <= int(x) <= 24),
            error_msg="请输入1-24之间的数字",
        )
        interval = int(check_interval) if check_interval else 1
        self.start_long_term_service(check_interval_hours=interval)
        ColorPrint.info("长期服务已启动，程序将在后台监控网络状态")
        ColorPrint.info("在长期模式下，程序将自动同意使用检测到的IP地址")
        ColorPrint.info("按 Ctrl+C 可以停止服务")
        try:
            # 保持程序运行
            while self.long_term_mode:
                time.sleep(300)  # 每5分钟检查一次状态
                # 每小时整点显示状态
                if datetime.now().minute == 0:
                    self.get_service_status()
        except KeyboardInterrupt:
            ColorPrint.info("\n收到停止信号...")
            self.stop_long_term_service()

    def network_login(self):
        ColorPrint.subheader("SRUN校园网认证登录", style="bracket")
        # 是否长期使用
        use_long_term = ColorPrint.ask_yes_no(
            "是否启用长期自动重连服务？", default=False
        )
        if use_long_term:
            self.long_term_work()
            return True
        # 检查网络状态
        if self.check_network_status():
            ColorPrint.info("网络已连接，无需认证")
            return True
        # 执行校园网认证
        if self.login():
            ColorPrint.success("🌐 SRUN校园网认证登录成功！")
            # 等待网络生效
            ColorPrint.process("等待网络生效...")
            time.sleep(3)
            if self.check_network_status():
                ColorPrint.success("网络连接验证成功")
                return True
            else:
                ColorPrint.warning("认证完成但网络可能需要更多时间生效")
                return True
        else:
            ColorPrint.error("SRUN校园网认证登录失败")
            return False


# 添加依赖库检查
def check_dependencies():
    try:
        import schedule
    except ImportError:
        ColorPrint.error("缺少必要依赖: schedule")
        ColorPrint.info("请运行: pip install schedule")
        return False
    return True


# 使用示例
def main():
    ColorPrint.header("SRUN校园网登录工具")

    # 检查依赖
    if not check_dependencies():
        return

    # 创建认证实例
    net_auth = HITSZNetAuth()

    try:
        # 输入用户名密码
        username = ColorPrint.input_with_validation(
            "请输入学号", validator=lambda x: len(x) > 0, error_msg="学号不能为空"
        )

        password = ColorPrint.input_with_validation(
            "请输入密码", validator=lambda x: len(x) > 0, error_msg="密码不能为空"
        )

        # 设置认证信息
        net_auth.username = username
        net_auth.password = password

        # 执行登录
        if net_auth.network_login():
            ColorPrint.success("校园网认证成功！")
        else:
            ColorPrint.error("校园网认证失败！")

    except KeyboardInterrupt:
        ColorPrint.info("\n正在清理资源...")
        if net_auth.long_term_mode:
            net_auth.stop_long_term_service()
        ColorPrint.info("拜拜喵！")


if __name__ == "__main__":
    main()
