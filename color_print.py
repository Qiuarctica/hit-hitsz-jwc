from colorama import Fore, Style, Back, init
import sys
import time
from datetime import datetime

# 初始化colorama，支持Windows终端彩色输出
init(autoreset=True)


class ColorPrint:
    # 定义颜色常量
    GREEN = Fore.GREEN
    RED = Fore.RED
    YELLOW = Fore.YELLOW
    CYAN = Fore.CYAN
    BLUE = Fore.BLUE
    MAGENTA = Fore.MAGENTA
    WHITE = Fore.WHITE
    BLACK = Fore.BLACK
    # 背景色
    BG_GREEN = Back.GREEN
    BG_RED = Back.RED
    BG_YELLOW = Back.YELLOW
    BG_CYAN = Back.CYAN
    BG_BLUE = Back.BLUE
    BG_MAGENTA = Back.MAGENTA
    BG_WHITE = Back.WHITE
    BG_BLACK = Back.BLACK
    # 样式
    BRIGHT = Style.BRIGHT
    DIM = Style.DIM
    NORMAL = Style.NORMAL
    RESET = Style.RESET_ALL

    def __init__(self, enable_timestamp=False, enable_level=True):
        self.enable_timestamp = enable_timestamp
        self.enable_level = enable_level

    def _format_message(self, text, level=""):
        parts = []

        if self.enable_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
            parts.append(f"{self.CYAN}[{timestamp}]{self.RESET}")

        if self.enable_level and level:
            parts.append(f"{level}")

        parts.append(text)

        return " ".join(parts)

    @staticmethod
    def success(text, end="\n"):
        message = f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}"
        print(message, end=end)

    @staticmethod
    def error(text, end="\n"):
        message = f"{Fore.RED}❌ {text}{Style.RESET_ALL}"
        print(message, end=end, file=sys.stderr)

    @staticmethod
    def warning(text, end="\n"):
        message = f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}"
        print(message, end=end)

    @staticmethod
    def info(text, end="\n"):
        message = f"{Fore.CYAN}ℹ️  {text}{Style.RESET_ALL}"
        print(message, end=end)

    @staticmethod
    def process(text, end="\n"):
        message = f"{Fore.BLUE}🔄 {text}{Style.RESET_ALL}"
        print(message, end=end)

    @staticmethod
    def debug(text, end="\n"):
        message = f"{Fore.WHITE}{Style.DIM}🐛 {text}{Style.RESET_ALL}"
        print(message, end=end)

    @staticmethod
    def header(text, char="═", width=60, style="double"):
        """
        显示标题头部

        Args:
            text: 标题文本
            char: 边框字符
            width: 总宽度
            style: 样式 ("double", "single", "bold", "gradient", "box")
        """
        if style == "double":
            print(f"\n{Fore.MAGENTA}{Style.BRIGHT}╔{'═' * (width-2)}╗{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}{Style.BRIGHT}║{text:^{width-2}}║{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}{Style.BRIGHT}╚{'═' * (width-2)}╝{Style.RESET_ALL}\n")

        elif style == "single":
            print(f"\n{Fore.CYAN}{Style.BRIGHT}┌{'─' * (width-2)}┐{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{Style.BRIGHT}│{text:^{width-2}}│{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{Style.BRIGHT}└{'─' * (width-2)}┘{Style.RESET_ALL}\n")

        elif style == "bold":
            print(f"\n{Fore.YELLOW}{Style.BRIGHT}█{'█' * (width-2)}█{Style.RESET_ALL}")
            print(
                f"{Fore.BLACK}{Back.YELLOW}{Style.BRIGHT}{text:^{width}}{Style.RESET_ALL}"
            )
            print(f"{Fore.YELLOW}{Style.BRIGHT}█{'█' * (width-2)}█{Style.RESET_ALL}\n")

        elif style == "gradient":
            colors = [
                Fore.RED,
                Fore.YELLOW,
                Fore.GREEN,
                Fore.CYAN,
                Fore.BLUE,
                Fore.MAGENTA,
            ]
            border = ""
            for i in range(width):
                color = colors[i % len(colors)]
                border += f"{color}▆"

            print(f"\n{border}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{Style.BRIGHT}{text:^{width}}{Style.RESET_ALL}")
            print(f"{border}{Style.RESET_ALL}\n")

        elif style == "box":
            # 方框样式
            print(f"\n{Fore.GREEN}{Style.BRIGHT}┏{'━' * (width-2)}┓{Style.RESET_ALL}")
            print(
                f"{Fore.GREEN}{Style.BRIGHT}┃{' ' * ((width-len(text)-2)//2)}{Fore.WHITE}{Style.BRIGHT}{text}{Fore.GREEN}{' ' * ((width-len(text)-2)//2 + (width-len(text)-2)%2)}┃{Style.RESET_ALL}"
            )
            print(f"{Fore.GREEN}{Style.BRIGHT}┗{'━' * (width-2)}┛{Style.RESET_ALL}\n")

        else:
            # 默认样式（原来的风格但优化）
            print(f"\n{Fore.MAGENTA}{Style.BRIGHT}{'═' * width}{Style.RESET_ALL}")
            print(
                f"{Fore.WHITE}{Back.MAGENTA}{Style.BRIGHT}{text:^{width}}{Style.RESET_ALL}"
            )
            print(f"{Fore.MAGENTA}{Style.BRIGHT}{'═' * width}{Style.RESET_ALL}\n")

    @staticmethod
    def subheader(text, char="─", width=40, style="simple"):
        """
        显示子标题

        Args:
            text: 子标题文本
            char: 分隔字符
            width: 总宽度
            style: 样式 ("simple", "bracket", "arrow", "star", "wave")
        """
        if style == "simple":
            print(f"\n{Fore.CYAN}{Style.BRIGHT}┌{'─' * (width-2)}┐{Style.RESET_ALL}")
            print(
                f"{Fore.CYAN}│ {Fore.WHITE}{Style.BRIGHT}{text:<{width-4}} {Fore.CYAN}│{Style.RESET_ALL}"
            )
            print(f"{Fore.CYAN}└{'─' * (width-2)}┘{Style.RESET_ALL}")

        elif style == "bracket":
            padding = (width - len(text) - 4) // 2
            print(
                f"\n{Fore.YELLOW}{Style.BRIGHT}{'─' * padding}[ {Fore.WHITE}{text} {Fore.YELLOW}]{'─' * padding}{Style.RESET_ALL}"
            )

        elif style == "arrow":
            print(
                f"\n{Fore.GREEN}{Style.BRIGHT}▶ {Fore.WHITE}{text} {Fore.GREEN}◀{Style.RESET_ALL}"
            )
            print(f"{Fore.GREEN}{'─' * width}{Style.RESET_ALL}")

        elif style == "star":
            padding = (width - len(text) - 6) // 2
            print(
                f"\n{Fore.YELLOW}{Style.BRIGHT}{'*' * padding}★ {Fore.WHITE}{text} {Fore.YELLOW}★{'*' * padding}{Style.RESET_ALL}"
            )

        elif style == "wave":
            print(f"\n{Fore.BLUE}{Style.BRIGHT}{'～' * width}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{Style.BRIGHT}{text:^{width}}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'～' * width}{Style.RESET_ALL}")

        else:
            print(f"\n{Fore.CYAN}{Style.BRIGHT}{char * width}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{Style.BRIGHT}{text:^{width}}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{char * width}{Style.RESET_ALL}")

    @staticmethod
    def section_divider(text="", char="═", width=60, color=Fore.CYAN):
        if text:
            # 有文字的分隔符
            text_len = len(text)
            side_len = (width - text_len - 2) // 2
            remainder = (width - text_len - 2) % 2

            print(
                f"\n{color}{Style.BRIGHT}{char * side_len} {Fore.WHITE}{text} {color}{char * (side_len + remainder)}{Style.RESET_ALL}\n"
            )
        else:
            # 纯分隔线
            print(f"\n{color}{Style.BRIGHT}{char * width}{Style.RESET_ALL}\n")

    @staticmethod
    def separator(char="-", width=60, color=Fore.WHITE):
        print(f"{color}{char*width}{Style.RESET_ALL}")

    @staticmethod
    def highlight(text, bg_color=Back.YELLOW, text_color=Fore.BLACK):
        message = f"{bg_color}{text_color} {text} {Style.RESET_ALL}"
        print(message)

    @staticmethod
    def custom(text, color=Fore.WHITE, bg_color="", style="", icon="", end="\n"):
        message = f"{style}{bg_color}{color}{icon}{text if not icon else ' ' + text}{Style.RESET_ALL}"
        print(message, end=end)

    @staticmethod
    def rainbow_text(text):
        colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
        result = ""
        for i, char in enumerate(text):
            color = colors[i % len(colors)]
            result += f"{color}{char}"
        result += Style.RESET_ALL
        print(result)

    @staticmethod
    def typing_effect(text, delay=0.05, color=Fore.GREEN):
        """打字机效果"""
        for char in text:
            print(f"{color}{char}{Style.RESET_ALL}", end="", flush=True)
            time.sleep(delay)
        print()

    @staticmethod
    def table_row(*columns, widths=None, colors=None):
        if widths is None:
            widths = [15] * len(columns)
        if colors is None:
            colors = [Fore.WHITE] * len(columns)

        row = "|"
        for i, (col, width, color) in enumerate(zip(columns, widths, colors)):
            row += f" {color}{str(col):<{width-1}}{Style.RESET_ALL}|"
        print(row)

    @staticmethod
    def table_header(*headers, widths=None):
        if widths is None:
            widths = [15] * len(headers)

        border = "+"
        for width in widths:
            border += "-" * width + "+"
        print(f"{Fore.CYAN}{border}{Style.RESET_ALL}")

        ColorPrint.table_row(
            *headers, widths=widths, colors=[Fore.YELLOW + Style.BRIGHT] * len(headers)
        )

        print(f"{Fore.CYAN}{border}{Style.RESET_ALL}")

    @staticmethod
    def ask_yes_no(question, default=None):
        suffix = ""
        if default is True:
            suffix = " [Y/n]"
        elif default is False:
            suffix = " [y/N]"
        else:
            suffix = " [y/n]"

        while True:
            answer = (
                input(f"{Fore.CYAN}❓ {question}{suffix}: {Style.RESET_ALL}")
                .strip()
                .lower()
            )

            if answer in ["y", "yes", "是", "1"]:
                return True
            elif answer in ["n", "no", "否", "0"]:
                return False
            elif answer == "" and default is not None:
                return default
            else:
                ColorPrint.warning("请输入 y/yes 或 n/no")

    @staticmethod
    def input_with_validation(prompt, validator=None, error_msg="输入无效，请重试"):
        while True:
            try:
                value = input(f"{Fore.CYAN}📝 {prompt}: {Style.RESET_ALL}").strip()
                if validator is None or validator(value):
                    return value
                else:
                    ColorPrint.warning(error_msg)
            except KeyboardInterrupt:
                ColorPrint.warning("\n用户取消输入")
                return None

    @staticmethod
    def countdown(seconds, message="倒计时"):
        for i in range(seconds, 0, -1):
            print(
                f"\r{Fore.YELLOW}{message}: {Fore.RED}{i}秒{Style.RESET_ALL}",
                end="",
                flush=True,
            )
            time.sleep(1)
        print(f"\r{Fore.GREEN}{message}: 完成!{Style.RESET_ALL}")

    @staticmethod
    def get_inputs(message, separator):
        # 获得以separator分隔的个输入，并保存为列表
        if separator is None:
            separator = "\n"
        if separator == "\n":
            print(f"{Fore.CYAN}📝 {message}（按 Enter 键结束输入）:{Style.RESET_ALL}")
            inputs = []
            while True:
                line = input().strip()
                if line == "":
                    break
                inputs.append(line)
        else:
            inputs = (
                input(f"{Fore.CYAN}📝 {message}: {Style.RESET_ALL}")
                .strip()
                .split(separator)
            )
        return inputs
