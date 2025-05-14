import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from wordcloud import WordCloud
import jieba
import os
import re

class CommentAnalyzer:
    def __init__(
        self,
        csv_path,
    ):
        """
        初始化评论分析器。

        Args:
            csv_path (str): 评论数据CSV文件的路径。
            font_path (str): 中文字体文件路径。
            stopwords_path (str): 停用词文件路径。
            output_dir (str): 保存图片的文件夹路径。
        """
        self.csv_path = csv_path
        self.font_path = "./assets/fonts/PingFang-Medium.ttf"
        self.stopwords_path = "./assets/hit_stopwords.txt"
        self.output_dir = "./image"
        self.df = None  # 存储原始评论数据
        self.df_unique_users = None  # 存储按用户ID去重后的数据
        self._setup_matplotlib_font()  # 设置matplotlib字体
        self._create_output_directory()  # 创建输出目录

    def _setup_matplotlib_font(self):
        """设置matplotlib支持中文显示和使用指定字体。"""
        try:
            font = fm.FontProperties(fname=self.font_path)
            # 使用指定字体名称设置matplotlib的字体
            plt.rcParams["font.sans-serif"] = [font.get_name()]
            # 解决保存图像时负号'-'显示为方块的问题
            plt.rcParams["axes.unicode_minus"] = False
            print(f"成功设置matplotlib字体: {font.get_name()}")
        except Exception as e:
            print(
                f"警告: 设置matplotlib字体失败，请检查字体文件路径 '{self.font_path}' 是否正确或文件是否有效。错误信息: {e}"
            )
            # 如果设置指定字体失败，回退到默认中文字体（如果系统有）
            plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS"]
            plt.rcParams["axes.unicode_minus"] = False
            print("回退到默认中文字体。")

    def _create_output_directory(self):
        """创建保存图片的文件夹。"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"创建输出目录: {self.output_dir}")

    def load_data(self):
        """加载CSV文件并进行初步数据清洗。"""
        try:
            self.df = pd.read_csv(self.csv_path)
            print(f"成功加载数据文件: {self.csv_path}")

            # 数据清洗和预处理
            # 将评论ID列转换为字符串，避免科学计数法影响去重
            self.df["评论ID"] = self.df["评论ID"].astype(str)
            # 将评论时间列转换为datetime对象，方便时间序列分析
            self.df["评论时间"] = pd.to_datetime(self.df["评论时间"])

            # 针对用户维度的分析，根据用户ID去重，保留每个用户的第一次出现记录
            # 使用copy()避免SettingWithCopyWarning
            self.df_unique_users = self.df.drop_duplicates(subset=["用户ID"]).copy()
            print(f"原始评论数量: {len(self.df)}")
            print(f"去重用户数量: {len(self.df_unique_users)}")

        except FileNotFoundError:
            print(
                f"错误：未找到指定的CSV文件: {self.csv_path}。请检查文件路径是否正确。"
            )
            self.df = None
            self.df_unique_users = None
            return False
        except Exception as e:
            print(f"加载或处理数据时发生错误: {e}")
            self.df = None
            self.df_unique_users = None
            return False
        return True

    def analyze_ip_distribution(self):
        """分析用户IP属地分布并生成柱状图（基于去重用户）。"""
        if self.df_unique_users is None:
            print("数据未加载，无法进行IP属地分析。")
            return

        # 统计去重用户IP属地的Top 10
        ip_counts = self.df_unique_users["IP属地"].value_counts().head(10)
        plt.figure(figsize=(12, 8))
        sns.barplot(x=ip_counts.index, y=ip_counts.values, palette="viridis")
        plt.title("用户IP属地 Top 10 分布")
        plt.xlabel("IP属地")
        plt.ylabel("用户数量")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "user_ip_top10_distribution.png"))
        plt.show()
        print("已生成用户IP属地 Top 10 分布图。")

    def analyze_vip_status(self):
        """分析用户大会员状态并生成扇形图（基于去重用户）。"""
        if self.df_unique_users is None:
            print("数据未加载，无法进行大会员状态分析。")
            return

        # 统计去重用户的大会员状态
        vip_counts = self.df_unique_users["是否是大会员"].value_counts()
        plt.figure(figsize=(8, 6))
        plt.pie(vip_counts, labels=vip_counts.index, autopct="%1.1f%%", startangle=140)
        plt.title("用户大会员状态分布")
        plt.axis("equal")
        plt.savefig(os.path.join(self.output_dir, "user_vip_status.png"))
        plt.show()
        print("已生成用户大会员状态分布图。")

    def analyze_gender_distribution(self):
        """分析用户性别分布并生成扇形图（基于去重用户）。"""
        if self.df_unique_users is None:
            print("数据未加载，无法进行性别分析。")
            return

        # 统计去重用户的性别分布
        gender_counts = self.df_unique_users["性别"].value_counts()
        plt.figure(figsize=(8, 6))
        plt.pie(
            gender_counts, labels=gender_counts.index, autopct="%1.1f%%", startangle=140
        )
        plt.title("用户性别分布")
        plt.axis("equal")
        plt.savefig(os.path.join(self.output_dir, "user_gender_distribution.png"))
        plt.show()
        print("已生成用户性别分布图。")

    def analyze_level_distribution(self):
        """分析用户等级分布并生成扇形图（基于去重用户）。"""
        if self.df_unique_users is None:
            print("数据未加载，无法进行用户等级分析。")
            return

        # 统计去重用户的用户等级分布并按等级排序
        level_counts = self.df_unique_users["用户等级"].value_counts().sort_index()
        plt.figure(figsize=(8, 6))
        plt.pie(
            level_counts, labels=level_counts.index, autopct="%1.1f%%", startangle=140
        )
        plt.title("用户等级分布")
        plt.axis("equal")
        plt.savefig(os.path.join(self.output_dir, "user_level_distribution.png"))
        plt.show()
        print("已生成用户等级分布图。")

    def analyze_comment_time_trend(self):
        """分析评论数量随时间变化趋势并生成折线图（基于所有评论）。"""
        if self.df is None:
            print("数据未加载，无法进行评论时间趋势分析。")
            return

        # 按评论时间排序原始数据
        df_sorted_time = self.df.sort_values(by="评论时间")
        # 按天统计评论数量
        comment_counts_by_day = df_sorted_time.groupby(
            df_sorted_time["评论时间"].dt.date
        ).size()

        plt.figure(figsize=(15, 7))
        # 绘制折线图，不显示数据点
        comment_counts_by_day.plot(kind="line")

        # --- 修改部分：设置横轴日期格式和显示 ---
        # 获取日期范围
        dates = comment_counts_by_day.index
        if not dates.empty:
            # 设置日期格式
            plt.gca().xaxis.set_major_formatter(
                plt.matplotlib.dates.DateFormatter("%Y-%m-%d")
            )
            # 设置日期刻度定位器，例如每隔几天显示一个刻度
            # 可以根据日期范围的大小调整间隔
            plt.gca().xaxis.set_major_locator(plt.matplotlib.dates.AutoDateLocator())
            # 自动调整日期标签的倾斜角度，避免重叠
            plt.gcf().autofmt_xdate()

            # 确保开始和结束日期显示在刻度上
            # 如果数据点不多，AutoDateLocator通常会包含开始和结束日期
            # 如果数据点很多，可能需要更精细的控制，但AutoDateLocator通常是一个好的起点

        # --- 修改部分结束 ---

        plt.title("评论数量随时间变化趋势")
        plt.xlabel("日期")
        plt.ylabel("评论数量")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "comment_time_trend.png"))
        plt.show()
        print("已生成评论数量随时间变化趋势图。")

    def analyze_comment_hour_distribution(self):
        """分析评论数量按小时分布并生成柱状图（基于所有评论）。"""
        if self.df is None:
            print("数据未加载，无法进行评论小时分布分析。")
            return

        # 从评论时间中提取小时
        self.df["评论小时"] = self.df["评论时间"].dt.hour
        # 统计每个小时的评论数量并按小时排序
        comment_counts_by_hour = self.df["评论小时"].value_counts().sort_index()

        plt.figure(figsize=(12, 7))
        sns.barplot(
            x=comment_counts_by_hour.index,
            y=comment_counts_by_hour.values,
            palette="viridis",
        )
        plt.title("评论数量按小时分布")
        plt.xlabel("小时")
        plt.ylabel("评论数量")
        plt.xticks(range(24))  # 确保显示所有24小时
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "comment_hour_distribution.png"))
        plt.show()
        print("已生成评论数量按小时分布图。")

    def generate_wordcloud(self):
        """生成评论内容词云（基于所有评论）。"""
        if self.df is None:
            print("数据未加载，无法生成词云。")
            return
        # 合并所有评论内容，去除空值
        all_comments = " ".join(self.df["评论内容"].dropna())
        # --- 修改部分：移除 [xxx] 形式的表情符号 ---
        # 使用正则表达式匹配并替换 [xxx] 模式为空字符串
        # re.sub(pattern, repl, string)
        # pattern: 要匹配的模式，\[.*?\] 匹配以 [ 开头，以 ] 结尾，中间包含任意字符（非贪婪匹配）
        # repl: 替换的字符串，这里是空字符串 ''
        # string: 要处理的字符串
        all_comments = re.sub(r"\[.*?\]", "", all_comments)
        # --- 修改部分结束 ---
        stopwords = set()
        try:
            # 加载停用词表
            with open(self.stopwords_path, "r", encoding="utf-8") as f:
                for line in f:
                    stopwords.add(line.strip())
            print(f"成功加载停用词文件: {self.stopwords_path}")
        except FileNotFoundError:
            print(
                f"警告：未找到停用词文件: {self.stopwords_path}，将不使用停用词过滤。"
            )
        # 使用jieba进行分词，精确模式
        seg_list = jieba.cut(all_comments, cut_all=False)
        # 过滤停用词和单个字的词
        filtered_words = [
            word for word in seg_list if word not in stopwords and len(word) > 1
        ]
        # 生成词云，使用指定的字体路径
        wordcloud = WordCloud(
            width=800, height=400, background_color="white", font_path=self.font_path
        ).generate(" ".join(filtered_words))
        plt.figure(figsize=(10, 7))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.title("评论内容词云")
        plt.savefig(os.path.join(self.output_dir, "comment_wordcloud.png"))
        plt.show()
        print("已生成评论内容词云。")

    def run_all_analysis(self):
        """运行所有分析和图表生成。"""
        if self.load_data():
            self.analyze_ip_distribution()
            self.analyze_vip_status()
            self.analyze_gender_distribution()
            self.analyze_level_distribution()
            self.analyze_comment_time_trend()
            self.analyze_comment_hour_distribution()
            self.generate_wordcloud()
            print("所有分析已完成。")


# --- 如何使用 ---
if __name__ == "__main__":
    # 请将这些路径替换为你实际的文件路径
    csv_file = "./assets/在百万豪装录音棚大声听陈_评论.csv"
    # 确保这个路径正确，可以使用绝对路径
    analyzer = CommentAnalyzer(csv_file)
    analyzer.run_all_analysis()
