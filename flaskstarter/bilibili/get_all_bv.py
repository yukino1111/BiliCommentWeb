import json
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import os


class GetInfo:
    def __init__(self, user_id, headless=True):
        self.a_list = []  # 存储每一个视频的url
        # 初始化Chrome浏览器驱动，这里假设ChromeDriver在系统的PATH中
        # 如果不在PATH中，你需要指定路径，例如：
        # self.d = webdriver.Chrome(executable_path='/path/to/chromedriver')
        # 创建ChromeOptions对象
        # 1. 构建基于 assets_dir 的相对路径
        relative_user_data_dir = os.path.join("./flaskstarter/assets", "chrome_user_data")
        # 2. 将相对路径转换为绝对路径
        self.user_data_dir = os.path.abspath(relative_user_data_dir)
        # self.user_data_dir = os.path.join("./assets", "chrome_user_data")

        # if not os.path.exists(self.user_data_dir):
        #     os.makedirs(self.user_data_dir)
        #     print(f"创建 Chrome 用户配置文件目录: {self.user_data_dir}")
        # else:
        #     print(f"使用现有的 Chrome 用户配置文件目录: {self.user_data_dir}")

        #     driver_path = (
        #     ChromeDriverManager().install()
        # )
        chrome_options = Options()
        # 添加headless参数，启用无头模式
        # chrome_options.add_argument(f"user-data-dir={self.user_data_dir}")
        if headless:
            chrome_options.add_argument("--headless")
        # 添加其他可选参数，例如禁用GPU加速，避免一些问题
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-logging")  # 禁用 Chrome 日志
        chrome_options.add_argument(
            "--log-level=3"
        )  # 设置日志级别为 3 (OFF)，禁用所有日志输出
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-logging"]
        )  # 排除 enable-logging 开关
        # self.d = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
        self.d = webdriver.Chrome(
            service=Service("./flaskstarter/assets/chromedriver.exe"),
            options=chrome_options,
        )
        self.user_id = user_id
        self.base_url = f"https://space.bilibili.com/{user_id}/video"
        self.d.get(self.base_url)
        # 这篇文章写于2022年，当时B站免登入可以搜索视频，查看视频，但是这段时间再次尝试爬取资源时，加了必须认证登入，尝试过很多次，没有获取token，只能老老实实，登入后再去爬取信息
        # time.sleep(30)  # 等待用户扫码登录
        # print("速度扫码登入")

    def get_url(self):
        # 从当前页面获取所有视频的URL并保存到本地文件
        try:
            ul = WebDriverWait(self.d, 10).until(
                lambda x: x.find_element(By.XPATH, '//*[@id="submit-video-list"]/ul[1]')
            )
            lis = ul.find_elements(By.XPATH, "li")
            for li in lis:
                # 获取视频的aid（视频ID）
                id = li.get_attribute("data-aid")
                if id:  # 确保获取到了id
                    self.a_list.append(id)

        except Exception as e:
            print(f"获取当前页面视频id失败: {e}")

    def next_page(self):
        # 遍历所有页面，获取所有视频的URL
        try:
            # 等待总页数元素加载完成
            total_page_element = WebDriverWait(self.d, 10).until(
                lambda x: x.find_element(
                    By.XPATH, '//*[@id="submit-video-list"]/ul[3]/span[1]'
                )
            )
            # 使用正则表达式从文本中提取数字，即总页数
            number = re.findall(r"\d+", total_page_element.text)
            total_pages = int(number[0]) if number else 1  # 如果没有找到数字，默认为1页

            print(f"总页数: {total_pages}")

            # 循环遍历每一页
            for page in range(1, total_pages + 1):  # 循环到总页数
                print(f"正在处理第 {page} 页...")
                self.get_url()  # 获取当前页面的视频id

                # 如果不是最后一页，尝试点击下一页
                if page < total_pages:
                    try:
                        next_button = self.d.find_element(By.LINK_TEXT, "下一页")
                        next_button.click()
                        time.sleep(3)  # 等待页面加载，可以适当调整等待时间
                    except Exception as e:
                        print(f"点击下一页失败 (可能已是最后一页或元素未找到): {e}")
                        break  # 如果点击下一页失败，可能已经到达最后一页，退出循环
                else:
                    print("已到达最后一页。")

        except Exception as e:
            print(f"获取总页数或处理页面时发生错误: {e}")

        print("所有视频id获取完成:")
        print(self.a_list)
        # 关闭浏览器
        self.d.quit()
        return self.a_list


if __name__ == "__main__":
    # 示例：替换 '你的用户ID' 为实际的B站用户ID
    user_id_to_crawl = "28376308"
    video_ids = GetInfo(user_id_to_crawl, headless=True).next_page()
