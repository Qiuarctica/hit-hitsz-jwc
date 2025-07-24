import os
import time
from tqdm import tqdm
import asyncio
import aiohttp
from color_print import ColorPrint
from hitsz_auth import HITSZJwxtAuth


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
                advance = 30  # 提前30秒开始预备选课
                wait_seconds = time.mktime(target_time) - time.mktime(now) - advance

                if wait_seconds > 0:
                    ColorPrint.info(
                        f"距离选课开始还有 {int(wait_seconds)} 秒，提前{advance}秒开始..."
                    )
                    long_wait_threshold = 60
                    refresh_advance_seconds = 40
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
                        desc=f"{ColorPrint.CYAN}⏳ 等待中",
                        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                        colour="cyan",
                    ) as pbar:
                        target_timestamp = time.mktime(target_time) - advance
                        refresh_done = False

                        while True:
                            # 实时计算剩余时间
                            remaining_seconds = target_timestamp - time.time()
                            if remaining_seconds <= 0:
                                break
                            # 检查是否需要重新登录
                            if (
                                should_refresh
                                and not refresh_done
                                and remaining_seconds <= refresh_advance_seconds
                            ):
                                pbar.set_description(
                                    f"{ColorPrint.YELLOW}🔄 重新登录中"
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
                                refresh_done = True
                                pbar.set_description(f"{ColorPrint.CYAN}⏳ 等待中")
                            elif remaining_seconds <= 10 and remaining_seconds > 0:
                                pbar.set_description(
                                    f"{ColorPrint.GREEN}🚀 准备就绪 {remaining_seconds:.1f}秒"
                                )
                            # 更新进度条
                            elapsed = wait_seconds - remaining_seconds
                            pbar.n = min(int(elapsed), int(wait_seconds))
                            pbar.refresh()
                            if remaining_seconds > 300:  # 5分钟以上
                                sleep_time = 5.0
                            elif remaining_seconds > 60:  # 1-5分钟
                                sleep_time = 1.0
                            elif remaining_seconds > 10:  # 10秒-1分钟
                                sleep_time = 0.5
                            else:
                                sleep_time = 0.2
                            time.sleep(sleep_time)

                    ColorPrint.success("⏰ 选课时间到，开始执行选课！")
                else:
                    ColorPrint.warning("选课时间已过，立即开始选课")

            except ValueError:
                ColorPrint.error("时间格式错误，请使用 HH:MM 格式")
                return False

        else:
            ColorPrint.info("立即开始选课")

    def auto_choose_class(self, choose_classes, start_time=None):
        # 等待选课时间
        self.wait_for_choose_time(start_time)

        if not choose_classes:
            ColorPrint.error("没有课程ID可供选择")
            return

        ColorPrint.process("开始自动选课...")
        asyncio.run(self._async_auto_choose(choose_classes))

    async def _async_auto_choose(self, choose_classes):
        completed_classes = set()

        # 获取现有cookies
        cookies = {cookie.name: cookie.value for cookie in self.session.cookies}

        async with aiohttp.ClientSession(cookies=cookies) as session:
            request_count = 0
            pending_tasks = []  # 存储待处理的任务

            while len(completed_classes) < len(choose_classes):
                # 清理已完成的任务
                finished_tasks = []
                for task, class_id in pending_tasks:
                    if task.done():
                        finished_tasks.append((task, class_id))

                for task, class_id in finished_tasks:
                    pending_tasks.remove((task, class_id))
                    if class_id not in completed_classes:
                        try:
                            result = await task
                            if result.get("success"):
                                completed_classes.add(class_id)
                                ColorPrint.success(
                                    f"课程 {class_id[:8]}... 选课成功！: {result['message']}"
                                )
                            else:
                                ColorPrint.error(
                                    f"课程 {class_id[:8]}... 选课失败: {result['message']}"
                                )
                        except Exception as e:
                            ColorPrint.warning(
                                f"课程 {class_id[:8]}... 请求异常: {str(e)}"
                            )

                remaining_classes = [
                    cid for cid in choose_classes if cid not in completed_classes
                ]

                if not remaining_classes:
                    break

                current_class = remaining_classes[
                    request_count % len(remaining_classes)
                ]
                request_count += 1

                task = asyncio.create_task(
                    self._send_course_request_simple(session, current_class)
                )
                pending_tasks.append((task, current_class))

                ColorPrint.info(
                    f"第 {request_count} 次请求 - 课程 {current_class[:8]}... "
                )

                # 显示进度
                ColorPrint.info(
                    f"已完成 {len(completed_classes)}/{len(choose_classes)} 个课程，待处理任务: {len(pending_tasks)}"
                )
                await asyncio.sleep(1.4)

            if pending_tasks:
                ColorPrint.info("等待剩余请求完成...")
                for task, class_id in pending_tasks:
                    try:
                        result = await task
                        if result.get("success") and class_id not in completed_classes:
                            completed_classes.add(class_id)
                            ColorPrint.success(
                                f"课程 {class_id[:8]}... 选课成功！: {result['message']}"
                            )
                    except Exception as e:
                        ColorPrint.warning(f"课程 {class_id[:8]}... 请求异常: {str(e)}")

            ColorPrint.success("🎉 所有课程处理完毕！")

    async def _send_course_request_simple(self, session, class_id):
        url = f"{self.base_url}/Xsxk/addGouwuche"
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "http://jw.hitsz.edu.cn/Xsxk/query/1",
            "rolecode": "null",
            "User-Agent": self.headers["User-Agent"],
        }

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
            async with session.post(
                url, headers=headers, data=data, timeout=15
            ) as response:
                if response.status == 200:
                    try:
                        result = await response.json()
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
                        return {"success": False, "message": "响应解析失败"}
                else:
                    return {"success": False, "message": f"HTTP {response.status}"}

        except asyncio.TimeoutError:
            return {"success": False, "message": "请求超时"}
        except Exception as e:
            return {"success": False, "message": str(e)}


class MenuSystem:

    def __init__(self, auth, jwxt):
        self.auth = auth
        self.jwxt = jwxt
        self.running = True

    def show_menu(self):
        """显示主菜单"""
        ColorPrint.subheader("哈深教务系统功能菜单")
        ColorPrint.custom("1. 查看个人信息", color=ColorPrint.CYAN, icon="👤")
        ColorPrint.custom("2. 查看所有课程", color=ColorPrint.CYAN, icon="📚")
        ColorPrint.custom("3. 按课程名称查询并选课", color=ColorPrint.CYAN, icon="🔍")
        ColorPrint.custom("4. 按课程ID直接选课", color=ColorPrint.CYAN, icon="🎯")
        ColorPrint.custom("5. 刷新登录状态", color=ColorPrint.CYAN, icon="🔄")
        ColorPrint.custom("q. 退出程序", color=ColorPrint.RED, icon="❌")
        ColorPrint.separator()

    @staticmethod
    def handle_keyboard_interrupt(func):

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except KeyboardInterrupt:
                ColorPrint.warning("\n操作被中断，返回主菜单...")
                return None

        return wrapper

    @handle_keyboard_interrupt
    def show_personal_info(self):
        ColorPrint.subheader("个人信息")
        person_info = self.jwxt.get_person_info()
        if person_info:
            ColorPrint.success("个人信息获取成功")
            # 格式化显示个人信息
            self._display_person_info(person_info)
        else:
            ColorPrint.error("获取个人信息失败")

        input(f"\n{ColorPrint.CYAN}按回车键返回主菜单...{ColorPrint.RESET}")

    def _display_person_info(self, person_info):
        try:
            if isinstance(person_info, dict):
                ColorPrint.subheader("详细信息", char="-", width=30)
                for key, value in person_info.items():
                    if isinstance(value, (str, int, float)):
                        ColorPrint.info(f"{key}: {value}")
                    elif isinstance(value, dict):
                        ColorPrint.info(f"{key}:")
                        for sub_key, sub_value in value.items():
                            ColorPrint.info(f"  {sub_key}: {sub_value}")
        except Exception as e:
            ColorPrint.debug(f"显示个人信息时出错: {e}")
            ColorPrint.info(f"原始数据: {person_info}")

    @handle_keyboard_interrupt
    def show_all_classes(self):
        ColorPrint.subheader("所有课程信息")
        all_classes = self.jwxt.get_classes()
        if not all_classes:
            ColorPrint.error("查询课程信息失败")
            input(f"\n{ColorPrint.CYAN}按回车键返回主菜单...{ColorPrint.RESET}")
            return

        # 显示课程表格
        ColorPrint.info("所有课程信息如下：")
        ColorPrint.table_header("课程名称", "课程ID", widths=[40, 30])
        for cls in all_classes.get("kxrwList", {}).get("list", []):
            ColorPrint.table_row(cls["kcmc"], cls["id"], widths=[40, 30])

        input(f"\n{ColorPrint.CYAN}按回车键返回主菜单...{ColorPrint.RESET}")

    @handle_keyboard_interrupt
    def choose_class_by_name(self):
        ColorPrint.subheader("按课程名称查询并选课")

        all_classes = self.jwxt.get_classes()
        if not all_classes:
            ColorPrint.error("查询课程信息失败")
            input(f"\n{ColorPrint.CYAN}按回车键返回主菜单...{ColorPrint.RESET}")
            return

        # 显示所有课程
        ColorPrint.info("所有课程信息如下：")
        ColorPrint.table_header("课程名称", "课程ID", widths=[40, 30])
        for cls in all_classes.get("kxrwList", {}).get("list", []):
            ColorPrint.table_row(cls["kcmc"], cls["id"], widths=[40, 30])

        # 输入课程名称
        class_names = []
        ColorPrint.info("请输入课程名称（每行一个，输入空行结束）：")
        while True:
            try:
                name = input(f"{ColorPrint.CYAN}课程名称: {ColorPrint.RESET}").strip()
                if not name:
                    break
                class_names.append(name)
            except KeyboardInterrupt:
                ColorPrint.warning("\n操作被中断，返回主菜单...")
                return

        if not class_names:
            ColorPrint.error("课程名称不能为空")
            input(f"\n{ColorPrint.CYAN}按回车键返回主菜单...{ColorPrint.RESET}")
            return

        # 查询课程ID
        ColorPrint.process("查询课程信息...")
        class_ids = self.jwxt.get_class_id_by_name(class_names, all_classes)
        if not class_ids:
            ColorPrint.error("未找到任何课程")
            input(f"\n{ColorPrint.CYAN}按回车键返回主菜单...{ColorPrint.RESET}")
            return

        # 询问选课时间
        start_time = self._get_start_time()
        if start_time is None:  # 用户中断
            return

        # 开始选课
        ColorPrint.process("开始自动选课...")
        self.jwxt.auto_choose_class(class_ids, start_time)

        input(f"\n{ColorPrint.CYAN}按回车键返回主菜单...{ColorPrint.RESET}")

    @handle_keyboard_interrupt
    def choose_class_by_id(self):
        ColorPrint.subheader("按课程ID直接选课")

        # 输入课程ID
        class_ids = []
        ColorPrint.info("请输入课程ID（每行一个，输入空行结束）：")
        while True:
            try:
                class_id = input(f"{ColorPrint.CYAN}课程ID: {ColorPrint.RESET}").strip()
                if not class_id:
                    break
                class_ids.append(class_id)
            except KeyboardInterrupt:
                ColorPrint.warning("\n操作被中断，返回主菜单...")
                return

        if not class_ids:
            ColorPrint.error("课程ID不能为空")
            input(f"\n{ColorPrint.CYAN}按回车键返回主菜单...{ColorPrint.RESET}")
            return

        # 询问选课时间
        start_time = self._get_start_time()
        if start_time is None:  # 用户中断
            return

        # 开始选课
        ColorPrint.process("开始自动选课...")
        self.jwxt.auto_choose_class(class_ids, start_time)

        input(f"\n{ColorPrint.CYAN}按回车键返回主菜单...{ColorPrint.RESET}")

    def _get_start_time(self):
        try:
            start_time = input(
                f"{ColorPrint.CYAN}请输入选课开始时间（格式如 13:00，留空则立即开始）: {ColorPrint.RESET}"
            ).strip()
            return start_time if start_time else None
        except KeyboardInterrupt:
            ColorPrint.warning("\n操作被中断，返回主菜单...")
            return None

    @handle_keyboard_interrupt
    def refresh_login(self):
        ColorPrint.subheader("刷新登录状态")

        if self.auth.auto_reconnect():
            ColorPrint.success("登录状态刷新成功！")
            # 更新session
            self.jwxt.session = self.auth.get_session()
        else:
            ColorPrint.error("登录状态刷新失败")

        input(f"\n{ColorPrint.CYAN}按回车键返回主菜单...{ColorPrint.RESET}")

    def run(self):
        ColorPrint.success("🎉 登录成功，菜单")

        # 初始检查
        person_info = self.jwxt.get_person_info()
        if not person_info:
            ColorPrint.error("获取个人信息失败，可能需要重新登录")
        else:
            ColorPrint.success("系统状态正常")

        while self.running:
            try:
                self.show_menu()
                choice = (
                    input(f"{ColorPrint.CYAN}请选择功能 (1-5, q): {ColorPrint.RESET}")
                    .strip()
                    .lower()
                )

                if choice == "q":
                    ColorPrint.info("再见喵！")
                    break
                elif choice == "1":
                    self.show_personal_info()
                elif choice == "2":
                    self.show_all_classes()
                elif choice == "3":
                    self.choose_class_by_name()
                elif choice == "4":
                    self.choose_class_by_id()
                elif choice == "5":
                    self.refresh_login()
                else:
                    ColorPrint.warning("无效选择，请输入 1-5 或 q")
                    time.sleep(1)

            except KeyboardInterrupt:
                if ColorPrint.ask_yes_no("\n确定要退出程序吗？"):
                    ColorPrint.info("再见喵！")
                    break
                else:
                    ColorPrint.info("继续使用...")
            except EOFError:
                ColorPrint.info("\n检测到EOF，退出程序")
                break


def main():
    ColorPrint.header("哈尔滨工业大学（深圳）教务辅助选课工具")

    ColorPrint.warning(
        "注意：本工具为辅助校外同学选课工具，请合理使用，谨慎传播以免对本研服务器造成负担。"
    )
    ColorPrint.info("本工具使用方法如下：")
    ColorPrint.info("1. 登录系统：使用您的学号和密码登录系统。")
    ColorPrint.info("2. 通过菜单选择功能进行操作。")
    ColorPrint.info("3. 在任何功能中按 Ctrl+C 可返回主菜单。")
    ColorPrint.info("4. 在主菜单按 Ctrl+C 或输入 q 退出程序。")

    auth = HITSZJwxtAuth()
    use_pwd = True

    # 检查已保存的Cookie
    if os.path.exists(auth.cookies_file):
        try:
            use_saved = ColorPrint.ask_yes_no("检测到已保存的Cookie，是否使用？")
            if use_saved:
                if auth.load_cookies() and auth.test_cookie():
                    ColorPrint.success("使用保存的Cookie成功登录！")
                    use_pwd = False
                else:
                    ColorPrint.warning("保存的Cookie无效，将重新登录")
                    auth = HITSZJwxtAuth()  # 重置认证对象
        except KeyboardInterrupt:
            ColorPrint.info("\n拜拜喵！")
            return

    # 输入用户名密码
    if use_pwd:
        try:
            username = ColorPrint.input_with_validation(
                "请输入学号/工号",
                validator=lambda x: len(x) > 0,
                error_msg="学号/工号不能为空",
            )

            if not username:
                ColorPrint.error("用户取消输入")
                return

            password = ColorPrint.input_with_validation(
                "请输入密码", validator=lambda x: len(x) > 0, error_msg="密码不能为空"
            )

            if not password:
                ColorPrint.error("用户取消输入")
                return

            if not auth.login(username, password):
                ColorPrint.error("登录失败")
                return

        except KeyboardInterrupt:
            ColorPrint.info("\n拜拜喵！")
            return

    # 初始化教务系统
    jwxt = HITSZJwxt(auth)

    # 创建并运行菜单系统
    menu = MenuSystem(auth, jwxt)
    menu.run()


if __name__ == "__main__":
    main()
