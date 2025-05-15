import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from wordcloud import WordCloud
import jieba
import os
import re
from snownlp import SnowNLP
import matplotlib.dates as mdates
import collections


class CommentAnalyzer:
    def __init__(
        self,
        csv_path,
    ):
        self.csv_path = csv_path
        self.font_path = "./flaskstarter/assets/fonts/PingFang-Medium.ttf"
        self.stopwords_path = "./flaskstarter/assets/hit_stopwords.txt"
        self.output_dir = "./flaskstarter/static/image"
        self.df = None  # 存储原始评论数据
        self.df_unique_users = None  # 存储按用户ID去重后的数据
        self._setup_matplotlib_font()  # 设置matplotlib字体
        self._create_output_directory()  # 创建输出目录

    def show_and_save_plot(  # 新函数名区别于之前的
        self,
        plot_data,  # 要绘制的数据
        plot_type,  # 绘制类型 ('bar', 'pie', 'line', 'imshow')
        save_filename,
        x,
        y,
        show_plot=True,
        show_axis=True,  # 绘制时是否显示坐标轴 (默认为 True)
        show_title="",  # 显示时标题
        show_title_size=16,
        dpi=100,
        save_format="png",
        transparent_background=False,
        **plot_kwargs,  # 其他绘制时可能需要的参数，如 x, y, labels, colors, rotation等
    ):
        save_figsize = (x / dpi, y / dpi)

        save_fig, save_ax = plt.subplots(figsize=save_figsize, dpi=dpi)
        if "xlabel" in plot_kwargs:
            save_ax.set_xlabel(plot_kwargs["xlabel"])
        if "ylabel" in plot_kwargs:
            save_ax.set_ylabel(plot_kwargs["ylabel"])
        if plot_type == "imshow":
            save_ax.imshow(
                plot_data,
                interpolation=plot_kwargs.get("interpolation", "bilinear"),
            )
        elif plot_type == "bar":
            sns.barplot(
                x=plot_data[0],
                y=plot_data[1],
                ax=save_ax,
                palette=plot_kwargs.get("palette", "viridis"),
            )
        elif plot_type == "pie":
            save_ax.pie(
                plot_data[0],
                labels=plot_data[1],
                autopct=plot_kwargs.get("autopct", "%1.1f%%"),
                startangle=plot_kwargs.get("startangle", 140),
                colors=plot_kwargs.get("colors"),
            )
            save_ax.axis("equal")  # Make pie chart circular
        elif plot_type == "line":
            plot_data.plot(kind="line", ax=save_ax)
            # Handle date formatting for line plots
            if plot_kwargs.get("format_dates", False):
                save_ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
                save_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                save_fig.autofmt_xdate()  # Auto format date labels
        if not show_axis:  # Save plot usually does not show axis
            save_ax.axis("off")
        save_fig.subplots_adjust(bottom=0, top=1, left=0, right=1)
        if not save_filename.lower().endswith(f".{save_format}"):
            save_filename_with_ext = (
                f"{os.path.splitext(save_filename)[0]}.{save_format}"
            )
        else:
            save_filename_with_ext = save_filename
        getSavePath = os.path.join(self.output_dir, save_filename_with_ext)
        if save_format in ["png", "jpg", "jpeg", "bmp", "tiff"]:
            plt.savefig(
                getSavePath,
                bbox_inches="tight",
                format=save_format,
                transparent=transparent_background,
                dpi=dpi,
            )
        else:  # 矢量图格式
            plt.savefig(
                getSavePath,
                bbox_inches="tight",
                format=save_format,
                transparent=transparent_background,
            )
        print(
            f"图片已保存到: {getSavePath} (格式: {save_format}, 透明背景: {transparent_background})"
        )
        plt.close(save_fig)  # Close save figure
        if show_plot:
            display_fig, display_ax = plt.subplots(figsize=(x / dpi, y / dpi))
            if plot_type == "imshow":
                display_ax.imshow(
                    plot_data,
                    interpolation=plot_kwargs.get("interpolation", "bilinear"),
                )
            elif plot_type == "bar":
                sns.barplot(
                    x=plot_data[0],
                    y=plot_data[1],
                    ax=display_ax,
                    palette=plot_kwargs.get("palette", "viridis"),
                )
            elif plot_type == "pie":
                display_ax.pie(
                    plot_data[0],
                    labels=plot_data[1],
                    autopct=plot_kwargs.get("autopct", "%1.1f%%"),
                    startangle=plot_kwargs.get("startangle", 140),
                    colors=plot_kwargs.get("colors"),
                )
                display_ax.axis("equal")
            elif plot_type == "line":
                plot_data.plot(kind="line", ax=display_ax)
                if plot_kwargs.get("format_dates", False):
                    display_ax.xaxis.set_major_formatter(
                        mdates.DateFormatter("%Y-%m-%d")
                    )
                    display_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    display_fig.autofmt_xdate()
            if not show_axis:
                display_ax.axis("off")
            else:  # For display plot, set labels and title if show_axis is True
                if "xlabel" in plot_kwargs:
                    display_ax.set_xlabel(plot_kwargs["xlabel"])
                if "ylabel" in plot_kwargs:
                    display_ax.set_ylabel(plot_kwargs["ylabel"])
            if show_title:
                display_ax.set_title(show_title, fontsize=show_title_size)
            display_fig.tight_layout()
            plt.show()
            plt.close(display_fig)  # Close display figure

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
        filtered_users = self.df_unique_users.copy()
        filtered_users = filtered_users[filtered_users["IP属地"] != "未知"]
        # 统计过滤后用户的IP属地的Top 10
        ip_counts = filtered_users["IP属地"].value_counts().head(10)
        # 如果过滤后没有数据，或者Top 10都是空的，则不生成图表
        if ip_counts.empty:
            print("过滤IP属地为'未知'后，没有足够的有效数据进行IP属地分析。")
            return
        # 调用 show_and_save_plot 方法生成和处理图形
        self.show_and_save_plot(
            plot_data=(ip_counts.index, ip_counts.values),  # 数据为 x 和 y
            plot_type="bar",
            save_filename="user_ip_top10_distribution.png",
            x=1600,
            y=900,
            show_plot=True,
            show_axis=True,  # 柱状图通常需要显示轴
            show_title="用户IP属地 Top 10 分布",
            show_title_size=16,
            dpi=100,
            # 传递给 sns.barplot 的其他参数
            palette="viridis",
            xlabel="IP属地",
            ylabel="用户数量",
            xticks=ip_counts.index,  # Explicitly set xticks for rotation
            xticklabels=ip_counts.index,  # Explicitly set xticklabels for rotation
            rotation=45,  # Angle for labels
            ha="right",  # Horizontal alignment for labels
        )

    def analyze_vip_status(self):
        """分析用户大会员状态并生成扇形图（基于去重用户）。"""
        if self.df_unique_users is None:
            print("数据未加载，无法进行大会员状态分析。")
            return
        vip_counts = self.df_unique_users["是否是大会员"].value_counts()
        if vip_counts.empty:
            print("没有足够的数据进行大会员状态分析。")
            return
        self.show_and_save_plot(
            plot_data=(vip_counts.values, vip_counts.index),  # 数据为值和标签
            plot_type="pie",
            save_filename="user_vip_status.png",
            x=800,  # 扇形图可以方一点
            y=800,
            show_plot=True,
            show_axis=False,  # 扇形图通常不显示轴
            show_title="用户大会员状态分布",
            show_title_size=16,
            dpi=100,
            # 传递给 plt.pie 的其他参数
            autopct="%1.1f%%",
            startangle=140,
        )

    def analyze_gender_distribution(self):
        """分析用户性别分布并生成扇形图（基于去重用户）。"""
        if self.df_unique_users is None:
            print("数据未加载，无法进行性别分析。")
            return
        gender_counts = self.df_unique_users["性别"].value_counts()
        if gender_counts.empty:
            print("没有足够的数据进行性别分析。")
            return
        self.show_and_save_plot(
            plot_data=(gender_counts.values, gender_counts.index),  # 数据为值和标签
            plot_type="pie",
            save_filename="user_gender_distribution.png",
            x=800,
            y=800,
            show_plot=True,
            show_axis=False,
            show_title="用户性别分布",
            show_title_size=16,
            dpi=100,
            # 传递给 plt.pie 的其他参数
            autopct="%1.1f%%",
            startangle=140,
        )

    def analyze_level_distribution(self):
        """分析用户等级分布并生成扇形图（基于去重用户）。"""
        if self.df_unique_users is None:
            print("数据未加载，无法进行用户等级分析。")
            return
        level_counts = self.df_unique_users["用户等级"].value_counts().sort_index()
        if level_counts.empty:
            print("没有足够的数据进行用户等级分析。")
            return
        self.show_and_save_plot(
            plot_data=(level_counts.values, level_counts.index),  # 数据为值和标签
            plot_type="pie",
            save_filename="user_level_distribution.png",
            x=800,  # 可以稍微宽一些
            y=800,
            show_plot=True,
            show_axis=False,
            show_title="用户等级分布",
            show_title_size=16,
            dpi=100,
            # 传递给 plt.pie 的其他参数
            autopct="%1.1f%%",
            startangle=140,
            # 可能需要更多的颜色，如果等级很多的话
        )

    def analyze_comment_time_trend(self):
        """分析评论数量随时间变化趋势并生成折线图（基于所有评论）。"""
        if self.df is None:
            print("数据未加载，无法进行评论时间趋势分析。")
            return
        # 确保 '评论时间' 是 datetime 类型
        if not pd.api.types.is_datetime64_any_dtype(self.df["评论时间"]):
            self.df["评论时间"] = pd.to_datetime(self.df["评论时间"])
        df_sorted_time = self.df.sort_values(by="评论时间")
        comment_counts_by_day = df_sorted_time.groupby(
            df_sorted_time["评论时间"].dt.date
        ).size()
        if comment_counts_by_day.empty:
            print("没有足够的数据进行评论时间趋势分析。")
            return
        # 调用 show_and_save_plot 方法生成和处理图形
        self.show_and_save_plot(
            plot_data=comment_counts_by_day,  # Series 可以直接用 plot(kind='line')
            plot_type="line",
            save_filename="comment_time_trend.png",
            x=1600,  # 时间趋势图可以更宽
            y=900,
            show_plot=True,
            show_axis=True,  # 折线图通常需要显示轴
            show_title="评论数量随时间变化趋势",
            show_title_size=16,
            dpi=100,
            # 传递给 pandas plot 的其他参数
            xlabel="日期",
            ylabel="评论数量",
            format_dates=True,  # Signal to format x-axis as dates
        )

    def analyze_comment_hour_distribution(self):
        """分析评论数量按小时分布并生成柱状图（基于所有评论）。"""
        if self.df is None:
            print("数据未加载，无法进行评论小时分布分析。")
            return
        # 确保 '评论时间' 是 datetime 类型
        if not pd.api.types.is_datetime64_any_dtype(self.df["评论时间"]):
            self.df["评论时间"] = pd.to_datetime(self.df["评论时间"])
        self.df["评论小时"] = self.df["评论时间"].dt.hour
        comment_counts_by_hour = self.df["评论小时"].value_counts().sort_index()
        # 创建一个完整的 0-23 小时索引
        full_hour_index = pd.Index(range(24))
        # 重新索引 comment_counts_by_hour，缺失的小时用 0 填充
        comment_counts_by_hour = comment_counts_by_hour.reindex(
            full_hour_index, fill_value=0
        )
        if comment_counts_by_hour.empty:
            print("没有足够的数据进行评论小时分布分析。")
            return
        # 调用 show_and_save_plot 方法生成和处理图形
        self.show_and_save_plot(
            plot_data=(
                comment_counts_by_hour.index,
                comment_counts_by_hour.values,
            ),  # 数据为 x 和 y
            plot_type="bar",
            save_filename="comment_hour_distribution.png",
            x=1600,
            y=900,
            show_plot=True,
            show_axis=True,
            show_title="评论数量按小时分布",
            show_title_size=16,
            dpi=100,
            # 传递给 sns.barplot 的其他参数
            palette="viridis",
            xlabel="小时",
            ylabel="评论数量",
            xticks=range(24),  # Explicitly set xticks
        )

    def analyze_sentiment(self):
        if self.df is None or self.df.empty:
            print("评论数据为空，无法进行情感分析。")
            return
        print("开始进行情感分析...")
        # 添加情感分数列
        if "sentiment_score" not in self.df.columns:  # Avoid recalculating
            self.df["sentiment_score"] = self.df["评论内容"].apply(
                lambda x: SnowNLP(str(x)).sentiments if pd.notnull(x) else None
            )

        # 判断情感倾向 (可以自定义阈值)
        def classify_sentiment(score):
            if score is None:
                return "未知"
            elif score > 0.7:
                return "积极"
            elif score < 0.3:
                return "消极"
            else:
                return "中立"

        if "sentiment_label" not in self.df.columns:  # Avoid recalculating
            self.df["sentiment_label"] = self.df["sentiment_score"].apply(
                classify_sentiment
            )
        print("情感分析完成。")
        # 统计情感标签分布
        sentiment_counts = self.df["sentiment_label"].value_counts()
        if not sentiment_counts.empty:
            # 调用 show_and_save_plot 方法生成和处理图形
            self.show_and_save_plot(
                plot_data=(
                    sentiment_counts.values,
                    sentiment_counts.index,
                ),  # 数据为值和标签
                plot_type="pie",
                save_filename="comment_sentiment_distribution.png",
                x=800,
                y=800,
                show_plot=True,
                show_axis=False,
                show_title="评论情感分布",
                show_title_size=16,
                dpi=100,
                # 传递给 plt.pie 的其他参数
                autopct="%1.1f%%",
                startangle=140,
                colors=sns.color_palette("pastel"),
            )
        else:
            print("没有足够的有效情感分析结果来生成分布图。")
        average_sentiment_score = self.df["sentiment_score"].dropna().mean()
        print(f"评论的平均情感分数 (0-1, 1为最积极): {average_sentiment_score:.4f}")

    def generate_wordcloud(self):

        if self.df is None:
            print("数据未加载，无法生成词云。")
            return
        all_comments = " ".join(self.df["评论内容"].dropna())
        all_comments = re.sub(r"\[.*?\]", "", all_comments)
        stopwords = set()
        try:
            with open(self.stopwords_path, "r", encoding="utf-8") as f:
                for line in f:
                    stopwords.add(line.strip())
            print(f"成功加载停用词文件: {self.stopwords_path}")
        except FileNotFoundError:
            print(
                f"警告：未找到停用词文件: {self.stopwords_path}，将不使用停用词过滤。"
            )
        seg_list = jieba.cut(all_comments, cut_all=False)
        filtered_words = [
            word for word in seg_list if word not in stopwords and len(word) > 1
        ]

        word_count = collections.Counter(filtered_words)
        wordcloud = WordCloud(
            width=1600,
            height=900,
            background_color="white",
            collocations=False,
            font_path=self.font_path,
            scale=2,
        ).generate_from_frequencies(word_count)
        self.show_and_save_plot(
            plot_data=wordcloud,  # 直接传入词云图像数据
            plot_type="imshow",  # 指定绘制类型为 imshow
            save_filename="comment_wordcloud.png",
            x=1600,
            y=900,
            show_plot=True,
            show_axis=False,  # 词云通常不显示轴
            show_title="评论内容词云",
            show_title_size=16,
            dpi=100,
        )

    def run_all_analysis(self):
        """运行所有分析和图表生成。"""
        if self.load_data():
            self.analyze_ip_distribution()
            self.analyze_vip_status()
            self.analyze_gender_distribution()
            self.analyze_level_distribution()
            self.analyze_comment_time_trend()
            self.analyze_comment_hour_distribution()
            self.analyze_sentiment()
            self.generate_wordcloud()
            print("所有分析已完成。")


# --- 如何使用 ---
if __name__ == "__main__":
    # 请将这些路径替换为你实际的文件路径
    csv_file = "./assets/在百万豪装录音棚大声听陈_评论.csv"
    # 确保这个路径正确，可以使用绝对路径
    analyzer = CommentAnalyzer(csv_file)
    analyzer.run_all_analysis()
