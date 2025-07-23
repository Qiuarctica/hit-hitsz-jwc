import requests
from bs4 import BeautifulSoup
import base64
import json
import os
import time
from colorama import Fore, Back, Style, init
from tqdm import tqdm

# 初始化colorama
init(autoreset=True)


class ColorPrint:
    @staticmethod
    def success(text):
        print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")

    @staticmethod
    def error(text):
        print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")

    @staticmethod
    def warning(text):
        print(f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}")

    @staticmethod
    def info(text):
        print(f"{Fore.CYAN}ℹ️  {text}{Style.RESET_ALL}")

    @staticmethod
    def header(text):
        print(f"{Fore.MAGENTA}📚 {text}{Style.RESET_ALL}")
        # 注意事项
        print(
            f"{Fore.YELLOW}⚠️  注意：本工具为辅助校外同学选课工具，请合理使用，谨慎传播以免对本研服务器造成负担。{Style.RESET_ALL}"
        )
        print(
            f"{Fore.YELLOW}⚠️  本工具使用方法如下：\n"
            f"1. 登录系统：使用您的学号和密码登录系统。\n"
            f"2. 通过课程名称查询课程/通过课程id添加选课。由于涉及到教务系统服务器的不稳定性，我们建议您在选课高峰期前先查询到课程id，再在选课开前一段时间通过课程id进行选课，避免教务服务器崩溃导无法选课。\n"
            f"3. 等待自动辅助选课。\n"
            f"{Style.RESET_ALL}"
        )

    @staticmethod
    def process(text):
        print(f"{Fore.BLUE}🔄 {text}{Style.RESET_ALL}")


def get_inputs(message):
    # 获得以回车为分隔的输入并返回一个列表
    inputs = []
    ColorPrint.info(message)
    while True:
        user_input = input()
        if user_input:
            inputs.append(user_input)
        else:
            break
    return inputs


class HITSZAuth:
    def __init__(self, username=None, password=None):
        self.session = requests.Session()
        self.base_url = "https://ids.hit.edu.cn"
        self.service_url = "http://jw.hitsz.edu.cn/casLogin"
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

        response = self.session.get(login_url, params=params, headers=self.headers)
        if response.status_code == 200:
            return response.text
        else:
            ColorPrint.error(f"访问登录页面失败，状态码: {response.status_code}")
            return None

    def extract_login_params(self, html_content):
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

        return params

    def encrypt_password_with_aes(self, password, salt):
        try:
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import pad
            import random

            def random_string(length):
                chars = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"
                return "".join(random.choice(chars) for _ in range(length))

            if not salt:
                return password

            random_prefix = random_string(64)
            iv = random_string(16).encode("utf-8")
            plaintext = random_prefix + password

            key = salt.encode("utf-8")
            cipher = AES.new(key[:32], AES.MODE_CBC, iv[:16])
            padded_data = pad(plaintext.encode("utf-8"), AES.block_size)
            encrypted = cipher.encrypt(padded_data)

            return base64.b64encode(encrypted).decode("utf-8")

        except Exception:
            return password

    def perform_login(self, username, password, login_params):
        ColorPrint.process("提交登录信息...")
        login_url = f"{self.base_url}/authserver/login"

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

        response = self.session.post(
            login_url,
            params=params,
            data=login_data,
            headers=headers,
            allow_redirects=False,
        )

        if response.status_code == 302:
            redirect_url = response.headers.get("Location")
            if redirect_url and "ticket=" in redirect_url:
                ColorPrint.process("访问教务系统获取Cookie...")
                jwxt_response = self.session.get(
                    redirect_url, headers=self.headers, allow_redirects=True
                )
                return jwxt_response.status_code == 200
            else:
                ColorPrint.error("重定向URL中没有找到ticket参数")
                return False
        else:
            if "您提供的用户名或者密码有误" in response.text:
                ColorPrint.error("账号或密码错误")
            else:
                ColorPrint.error(f"登录失败，状态码: {response.status_code}")
            return False

    def auto_reconnect(self):
        if not self.username or not self.password:
            ColorPrint.error("无法自动重连：缺少用户名或密码")
            return False

        self.session = requests.Session()
        for attempt in range(3):
            ColorPrint.process(f"第 {attempt + 1} 次尝试重新登录...")
            if self.login(self.username, self.password):
                ColorPrint.success("自动重新登录成功！")
                return True
            if attempt < 2:
                time.sleep(2)

        ColorPrint.error("自动重连失败，已达到最大重试次数")
        return False

    def login(self, username=None, password=None):
        if username:
            self.username = username
        if password:
            self.password = password

        if not self.username or not self.password:
            ColorPrint.error("需要用户名和密码进行登录")
            return False

        login_page = self.get_login_page()
        if not login_page:
            return False

        login_params = self.extract_login_params(login_page)
        if not login_params:
            return False

        if self.perform_login(self.username, self.password, login_params):
            self.save_cookies()
            return True
        return False

    def save_cookies(self):
        try:
            cookies = {cookie.name: cookie.value for cookie in self.session.cookies}
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            ColorPrint.error("保存Cookies失败")
            return False

    def load_cookies(self):
        if not os.path.exists(self.cookies_file):
            return False

        try:
            with open(self.cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            self.session.cookies.update(cookies)
            return True
        except Exception:
            ColorPrint.error("加载Cookies失败")
            return False

    def test_cookie(self):
        ColorPrint.process("测试Cookie有效性...")
        test_url = "http://jw.hitsz.edu.cn/authentication/main"

        try:
            response = self.session.get(
                test_url, headers=self.headers, timeout=10, allow_redirects=False
            )
            if "require" in response.url or "invalid" in response.url:
                return False
            return response.status_code == 200
        except Exception:
            return False

    def get_session(self):
        return self.session


class HITSZJwxt:
    def __init__(self, auth):
        self.auth = auth
        self.session = auth.get_session()
        self.base_url = "http://jw.hitsz.edu.cn"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def _request_with_retry(self, method, url, **kwargs):
        for attempt in range(3):
            try:
                response = getattr(self.session, method.lower())(url, **kwargs)

                if "require" in response.url or "invalid" in response.url:
                    if attempt < 2 and self.auth.auto_reconnect():
                        self.session = self.auth.get_session()
                        continue
                    else:
                        raise Exception("Cookie失效且重连失败")

                return response

            except Exception as e:
                if attempt < 2:
                    ColorPrint.warning(f"请求失败，第 {attempt + 1} 次重试")
                    time.sleep(1)
                else:
                    raise e

    def get_person_info(self):
        ColorPrint.process("获取个人信息...")
        url = f"{self.base_url}/UserManager/queryxsxx"

        try:
            response = self._request_with_retry("POST", url, headers=self.headers)
            if response and response.status_code == 200:
                data = response.json()
                ColorPrint.success("个人信息获取成功")
                return data
            else:
                ColorPrint.error("获取个人信息失败")
                return None
        except Exception:
            ColorPrint.error("获取个人信息异常")
            return None

    def get_classes(self):
        ColorPrint.process("查询课程...")
        url = f"{self.base_url}/Xsxk/queryKxrw"
        # body 每次选课都需要更换
        body = "cxsfmt=0&p_pylx=1&mxpylx=1&p_sfgldjr=0&p_sfredis=0&p_sfsyxkgwc=0&p_xktjz=&p_chaxunxh=&p_gjz=&p_skjs=&p_xn=2025-2026&p_xq=1&p_xnxq=2025-20261&p_dqxn=2024-2025&p_dqxq=3&p_dqxnxq=2024-20253&p_xkfsdm=sx-b-b&p_xiaoqu=&p_kkyx=&p_kclb=&p_xkxs=&p_dyc=&p_kkxnxq=&p_id=&p_sfhlctkc=1&p_sfhllrlkc=1&p_kxsj_xqj=&p_kxsj_ksjc=&p_kxsj_jsjc=&p_kcdm_js=&p_kcdm_cxrw=&p_kcdm_cxrw_zckc=&p_kc_gjz=&p_xzcxtjz_nj=&p_xzcxtjz_yx=&p_xzcxtjz_zy=&p_xzcxtjz_zyfx=&p_xzcxtjz_bj=&p_sfxsgwckb=1&p_skyy=&p_chaxunxkfsdm=&pageNum=1&pageSize=100"
        headers = self.headers.copy()
        headers.update(
            {
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "http://jw.hitsz.edu.cn/Xsxk/query/1",
                "rolecode": "null",
            }
        )
        try:
            response = self._request_with_retry("POST", url, headers=headers, data=body)
            if response and response.status_code == 200:
                return response.json()
            else:
                ColorPrint.error(
                    f"查询课程失败，HTTP {response.status_code if response else 'None'}"
                )
                return None
        except Exception as e:
            ColorPrint.error(f"查询课程异常: {str(e)}")
            return None

    def get_class_id_by_name(self, class_names, all_classes):
        ColorPrint.process("根据课程名称获取课程ID...")
        class_ids = []
        class_list = all_classes.get("kxrwList", {}).get("list", [])
        for name in class_names:
            found = False
            for cls in class_list:
                if name in cls.get("kcmc", ""):
                    class_ids.append(cls["id"])
                    found = True
                    ColorPrint.success(f"找到课程: {cls['kcmc']} - ID: {cls['id']}")
                    break
            if not found:
                ColorPrint.warning(f"未找到课程: {name}")
        return class_ids

    def choose_class_by_id(self, class_id):
        url = f"{self.base_url}/Xsxk/addGouwuche"
        headers = self.headers.copy()
        headers.update(
            {
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "http://jw.hitsz.edu.cn/Xsxk/query/1",
                "rolecode": "null",
            }
        )
        data = {
            "cxsfmt": "0",
            "p_pylx": "1",
            "mxpylx": "1",
            "p_sfgldjr": "0",
            "p_sfredis": "0",
            "p_sfsyxkgwc": "0",
            "p_xktjz": "rwtjzyx",
            "p_chaxunxh": "",
            "p_gjz": "",
            "p_skjs": "",
            "p_xn": "2025-2026",
            "p_xq": "1",
            "p_xnxq": "2025-20261",
            "p_dqxn": "2024-2025",
            "p_dqxq": "3",
            "p_dqxnxq": "2024-20253",
            "p_xkfsdm": "sx-b-b",
            "p_xiaoqu": "",
            "p_kkyx": "",
            "p_kclb": "",
            "p_xkxs": "",
            "p_dyc": "",
            "p_kkxnxq": "",
            "p_id": class_id,
            "p_sfhlctkc": "1",
            "p_sfhllrlkc": "1",
            "p_kxsj_xqj": "",
            "p_kxsj_ksjc": "",
            "p_kxsj_jsjc": "",
            "p_kcdm_js": "",
            "p_kcdm_cxrw": "",
            "p_kcdm_cxrw_zckc": "",
            "p_kc_gjz": "",
            "p_xzcxtjz_nj": "",
            "p_xzcxtjz_yx": "",
            "p_xzcxtjz_zy": "",
            "p_xzcxtjz_zyfx": "",
            "p_xzcxtjz_bj": "",
            "p_sfxsgwckb": "1",
            "p_skyy": "",
            "p_chaxunxkfsdm": "",
            "pageNum": "1",
            "pageSize": "18",
        }
        try:
            response = self._request_with_retry("POST", url, headers=headers, data=data)
            if response and response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("jg") == "-1":
                        return {
                            "success": False,
                            "message": result.get("message", "选课失败"),
                        }
                    elif result.get("code") == "500":
                        return {"success": False, "message": "服务器内部错误"}
                    else:
                        return {
                            "success": True,
                            "message": result.get("message", "选课成功"),
                        }
                except:
                    return {"success": False, "message": "选课请求已发送"}
            else:
                return {
                    "success": False,
                    "message": f"HTTP {response.status_code if response else 'None'}",
                }
        except Exception as e:
            return {"success": False, "message": str(e)}

    # 等待并且提前10s开始预备选课
    def wait_for_choose_time(self, start_time):
        if start_time:
            ColorPrint.info(f"等待选课时间: {start_time}")
            # 解析时间
            try:
                target_time = time.strptime(start_time, "%H:%M")
                now = time.localtime()
                target_time = time.struct_time(
                    (
                        now.tm_year,
                        now.tm_mon,
                        now.tm_mday,
                        target_time.tm_hour,
                        target_time.tm_min,
                        0,
                        0,
                        0,
                        -1,
                    )
                )
                wait_seconds = time.mktime(target_time) - time.mktime(now) - 10

                if wait_seconds > 0:
                    ColorPrint.info(
                        f"距离选课开始还有 {int(wait_seconds)} 秒，提前10秒开始..."
                    )
                    # 判断是否需要长时间等待并设置重新登录时间点
                    # 调试时使用30秒，正式环境使用5分钟(300秒)
                    long_wait_threshold = 30  # 调试时使用，正式环境改为 300
                    refresh_advance_seconds = 20  # 提前20秒重新登录
                    # 重新登录一定要输入用户名和密码
                    should_refresh = (wait_seconds > long_wait_threshold) and (
                        self.auth.username and self.auth.password
                    )
                    refresh_time = (
                        wait_seconds - refresh_advance_seconds
                        if should_refresh
                        else None
                    )
                    if should_refresh:
                        ColorPrint.warning(
                            f"检测到长时间等待，将在倒计时剩余 {refresh_advance_seconds} 秒时重新登录刷新Cookie"
                        )
                    # 添加进度条
                    with tqdm(
                        total=int(wait_seconds),
                        desc=f"{Fore.CYAN}⏳ 等待中{Style.RESET_ALL}",
                        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                        colour="cyan",
                    ) as pbar:
                        for i in range(int(wait_seconds)):
                            time.sleep(1)
                            pbar.update(1)
                            # 检查是否需要重新登录
                            remaining_seconds = wait_seconds - i - 1
                            if (
                                should_refresh
                                and remaining_seconds == refresh_advance_seconds
                            ):
                                pbar.set_description(
                                    f"{Fore.YELLOW}🔄 重新登录中{Style.RESET_ALL}"
                                )
                                ColorPrint.warning("开始重新登录刷新Cookie...")
                                # 重新登录
                                if self.auth.auto_reconnect():
                                    ColorPrint.success("Cookie刷新成功！")
                                    self.session = self.auth.get_session()
                                else:
                                    ColorPrint.error(
                                        "Cookie刷新失败，将使用现有Cookie继续"
                                    )
                                pbar.set_description(
                                    f"{Fore.CYAN}⏳ 等待中{Style.RESET_ALL}"
                                )
                            elif remaining_seconds <= 10 and remaining_seconds > 0:
                                pbar.set_description(
                                    f"{Fore.GREEN}🚀 准备就绪 {remaining_seconds}秒{Style.RESET_ALL}"
                                )

                    ColorPrint.success("⏰ 选课时间到，开始执行选课！")
                else:
                    ColorPrint.warning("选课时间已过，立即开始选课")

            except ValueError:
                ColorPrint.error("时间格式错误，请使用 HH:MM 格式")
                return False

        else:
            ColorPrint.info("立即开始选课")

    def auto_choose_class(self, choose_classes, start_time=None):
        """自动选课"""
        self.wait_for_choose_time(start_time)
        ColorPrint.header("开始自动选课")

        while choose_classes:
            for class_id in choose_classes[:]:
                result = self.choose_class_by_id(class_id)

                if result["success"]:
                    ColorPrint.success(
                        f"课程 {class_id[:8]}... 选课成功: {result['message']}"
                    )
                    choose_classes.remove(class_id)
                else:
                    ColorPrint.error(
                        f"课程 {class_id[:8]}... 选课失败: {result['message']}"
                    )

                time.sleep(1.25)

            if choose_classes:
                ColorPrint.info(f"剩余 {len(choose_classes)} 个课程待处理")
            else:
                ColorPrint.success("🎉 所有课程处理完毕！")
                break


def main():
    """主程序"""
    ColorPrint.header("哈尔滨工业大学（深圳）教务辅助选课工具")

    auth = HITSZAuth()
    use_pwd = True

    # 检查已保存的Cookie
    if os.path.exists(auth.cookies_file):
        use_saved = (
            input(
                f"{Fore.CYAN}检测到已保存的Cookie，是否使用？(y/n): {Style.RESET_ALL}"
            )
            .strip()
            .lower()
        )
        if use_saved == "y":
            if auth.load_cookies() and auth.test_cookie():
                ColorPrint.success("使用保存的Cookie成功登录！")
                use_pwd = False
            else:
                ColorPrint.warning("保存的Cookie无效，将重新登录")
                auth = HITSZAuth()

    # 输入用户名密码
    if use_pwd:
        username = input(f"{Fore.GREEN}请输入学号/工号: {Style.RESET_ALL}").strip()
        password = input(f"{Fore.GREEN}请输入密码: {Style.RESET_ALL}").strip()

        if not username or not password:
            ColorPrint.error("学号/工号和密码不能为空")
            return

        if not auth.login(username, password):
            ColorPrint.error("登录失败")
            return

        ColorPrint.success("登录成功！")

    # 初始化教务系统
    jwxt = HITSZJwxt(auth)
    jwxt.get_person_info()

    ColorPrint.success("个人信息获取成功")

    # 询问是否需要通过名字查询课程id
    search_by_name = (
        input(f"{Fore.CYAN}是否通过课程名称查询课程id？(y/n): {Style.RESET_ALL}")
        .strip()
        .lower()
    )
    class_ids = []
    if search_by_name == "y":
        all_classes = jwxt.get_classes()
        if not all_classes:
            ColorPrint.error("查询课程信息失败")
            return
        # 打印所有课程名字
        ColorPrint.info("所有课程信息如下：")
        for cls in all_classes.get("kxrwList", {}).get("list", []):
            print(f"{cls['kcmc']}: {cls['id']}")
        class_names = get_inputs("请输入课程名称（每行一个，输入空行结束）")
        if not class_names:
            ColorPrint.error("课程名称不能为空")
            return
        ColorPrint.process("查询课程信息...")
        class_ids = jwxt.get_class_id_by_name(class_names, all_classes)
        if not class_ids:
            ColorPrint.error("未找到任何课程")
            return
    else:
        # 直接输入课程id
        class_ids = get_inputs("请输入课程ID（每行一个，输入空行结束）")
        if not class_ids:
            ColorPrint.error("课程ID不能为空")
            return

    # 自动选课 时间只需要一个代表今天几点几分(13:00)即可 留空则立刻开始
    start_time = input(
        f"{Fore.CYAN}请输入选课开始时间（格式如 13:00，留空则立即开始）（提前10秒开始预备选课）: {Style.RESET_ALL}"
    ).strip()

    ColorPrint.process("开始自动选课...")
    jwxt.auto_choose_class(class_ids, start_time)


if __name__ == "__main__":
    main()
