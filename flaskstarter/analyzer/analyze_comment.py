import pandas as pd
import matplotlib
matplotlib.use("Agg")
import warnings
warnings.filterwarnings("ignore")
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
import numpy as np

# 确保这些是从你的config导入
from ..tools.config import FONT_PATH, HIT_STOPWORDS_PATH, IMAGE_DIR 


class CommentAnalyzer:
    def __init__(
        self,
        csv_path,
        db_name="bilibili_comments.db"
    ):
        self.csv_path = csv_path
        self.db_name = db_name

        self.font_path = FONT_PATH
        self.stopwords_path = HIT_STOPWORDS_PATH
        self.output_dir = IMAGE_DIR
        self.df = None  # 存储原始评论数据
        self.df_unique_users = None  # 存储按用户ID去重后的数据
        self._setup_matplotlib_font()  # 设置matplotlib字体
        self._create_output_directory()  # 创建输出目录

    def _setup_matplotlib_font(self):
        """设置matplotlib支持中文显示和使用指定字体。"""
        try:
            font = fm.FontProperties(fname=self.font_path)
            plt.rcParams["font.sans-serif"] = [font.get_name()]
            plt.rcParams["axes.unicode_minus"] = False
            print(f"成功设置matplotlib字体: {font.get_name()}")
        except Exception as e:
            print(
                f"警告: 设置matplotlib字体失败，请检查字体文件路径 '{self.font_path}' 是否正确或文件是否有效。错误信息: {e}"
            )
            plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS"] # Fallback
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

            self.df["评论ID"] = self.df["评论ID"].astype(str)
            self.df["评论时间"] = pd.to_datetime(self.df["评论时间"])

            # 针对用户维度的分析，根据用户ID去重，保留每个用户的第一次出现记录
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

    def _display_plot(self, plot_data, plot_type, show_title, show_title_size, x, y, dpi, **plot_kwargs):
        """
        在新窗口显示图表。
        """
        display_fig, display_ax = plt.subplots(figsize=(x / dpi, y / dpi), dpi=dpi)

        self._render_plot_on_ax(display_ax, plot_data, plot_type, **plot_kwargs)

        if plot_type == "imshow" or plot_type == "pie":
            display_ax.axis("off")
        else:
            if "xlabel" in plot_kwargs:
                display_ax.set_xlabel(plot_kwargs["xlabel"])
            if "ylabel" in plot_kwargs:
                display_ax.set_ylabel(plot_kwargs["ylabel"])

        if show_title:
            display_ax.set_title(show_title, fontsize=show_title_size)

        display_fig.tight_layout()
        plt.show()
        plt.close(display_fig)

    def _save_plot(self, plot_data, plot_type, save_filename, x, y, dpi, save_format, **plot_kwargs):
        """
        将图表保存到文件。
        """
        save_figsize = (x / dpi, y / dpi)

        save_fig, save_ax = plt.subplots(figsize=save_figsize, dpi=dpi)

        self._render_plot_on_ax(save_ax, plot_data, plot_type, **plot_kwargs)

        if plot_type == "imshow" or plot_type == "pie":
            save_ax.axis("off")
        else:
            if "xlabel" in plot_kwargs:
                save_ax.set_xlabel(plot_kwargs["xlabel"])
            if "ylabel" in plot_kwargs:
                save_ax.set_ylabel(plot_kwargs["ylabel"])

        save_fig.subplots_adjust(bottom=0, top=1, left=0, right=1)

        if not save_filename.lower().endswith(f".{save_format}"):
            save_filename_with_ext = f"{os.path.splitext(save_filename)[0]}.{save_format}"
        else:
            save_filename_with_ext = save_filename

        getSavePath = os.path.join(self.output_dir, save_filename_with_ext)

        plt.savefig(
            getSavePath,
            bbox_inches="tight",
            format=save_format,
            transparent=True,
            dpi=dpi,
        )
        print(
            f"图片已保存到: {getSavePath} (格式: {save_format}, 透明背景: True)"
        )
        plt.close(save_fig)

    def _render_plot_on_ax(self, ax, plot_data, plot_type, **plot_kwargs):
        """
        内部辅助方法：在给定的Axes对象上绘制图表。
        """
        if plot_type == "imshow":
            ax.imshow(
                plot_data,
                interpolation=plot_kwargs.get("interpolation", "bilinear"),
            )
        elif plot_type == "bar":
            sns.barplot(
                x=plot_data[0],
                y=plot_data[1],
                ax=ax,
                palette=plot_kwargs.get("palette", "viridis"),
            )
            if "rotation" in plot_kwargs and plot_kwargs["rotation"] is not None:
                ax.set_xticks(plot_kwargs.get("xticks", ax.get_xticks()))
                ax.set_xticklabels(plot_kwargs.get("xticklabels", ax.get_xticklabels()),
                                   rotation=plot_kwargs["rotation"], ha=plot_kwargs.get("ha", "center"))
        elif plot_type == "pie":
            ax.pie(
                plot_data[0],
                labels=plot_data[1],
                autopct=plot_kwargs.get("autopct", "%1.1f%%"),
                startangle=plot_kwargs.get("startangle", 140),
                colors=plot_kwargs.get("colors"),
            )
            ax.axis("equal")
        elif plot_type == "line":
            plot_data.plot(kind="line", ax=ax)
            pass

    def plot_figure(self, 
                    plot_data, 
                    plot_type, 
                    save_filename, 
                    x: int, 
                    y: int, 
                    show_plot: bool = True, 
                    show_title: str = "", 
                    show_title_size: int = 16, 
                    dpi: int = 100, 
                    save_format: str = "png",
                    **plot_kwargs):
        """
        统一的绘图和保存函数（不包括雷达图）。
        """
        self._save_plot(plot_data, plot_type, save_filename, x, y, dpi, save_format, **plot_kwargs)
        if show_plot:
            self._display_plot(plot_data, plot_type, show_title, show_title_size, x, y, dpi, **plot_kwargs)

    # (其他分析方法保持不变)
    def analyze_ip_distribution(self):
        """分析用户IP属地分布并生成柱状图（基于去重用户）。"""
        if self.df_unique_users is None:
            print("数据未加载，无法进行IP属地分析。")
            return
        filtered_users = self.df_unique_users.copy()
        filtered_users = filtered_users[filtered_users["IP属地"] != "未知"]
        ip_counts = filtered_users["IP属地"].value_counts().head(10)
        if ip_counts.empty:
            print("过滤IP属地为'未知'后，没有足够的有效数据进行IP属地分析。")
            return
        self.plot_figure(
            plot_data=(ip_counts.index, ip_counts.values),
            plot_type="bar",
            save_filename="user_ip_top10_distribution.png",
            x=1600,
            y=900,
            show_plot=True,
            show_title="用户IP属地 Top 10 分布",
            show_title_size=16,
            dpi=100,
            palette="viridis",
            xlabel="IP属地",
            ylabel="用户数量",
            rotation=45,
            ha="right",
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
        self.plot_figure(
            plot_data=(vip_counts.values, vip_counts.index),
            plot_type="pie",
            save_filename="user_vip_status.png",
            x=800,
            y=800,
            show_plot=True,
            show_title="用户大会员状态分布",
            show_title_size=16,
            dpi=100,
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
        self.plot_figure(
            plot_data=(gender_counts.values, gender_counts.index),
            plot_type="pie",
            save_filename="user_gender_distribution.png",
            x=800,
            y=800,
            show_plot=True,
            show_title="用户性别分布",
            show_title_size=16,
            dpi=100,
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
        self.plot_figure(
            plot_data=(level_counts.values, level_counts.index),
            plot_type="pie",
            save_filename="user_level_distribution.png",
            x=800,
            y=800,
            show_plot=True,
            show_title="用户等级分布",
            show_title_size=16,
            dpi=100,
            autopct="%1.1f%%",
            startangle=140,
        )

    def analyze_comment_time_trend(self):
        """分析评论数量随时间变化趋势并生成折线图（基于所有评论）。"""
        if self.df is None:
            print("数据未加载，无法进行评论时间趋势分析。")
            return
        if not pd.api.types.is_datetime64_any_dtype(self.df["评论时间"]):
            self.df["评论时间"] = pd.to_datetime(self.df["评论时间"])
        df_sorted_time = self.df.sort_values(by="评论时间")
        comment_counts_by_day = df_sorted_time.groupby(
            df_sorted_time["评论时间"].dt.date
        ).size()
        if comment_counts_by_day.empty:
            print("没有足够的数据进行评论时间趋势分析。")
            return
        self.plot_figure(
            plot_data=comment_counts_by_day,
            plot_type="line",
            save_filename="comment_time_trend.png",
            x=1600,
            y=900,
            show_plot=True,
            show_title="评论数量随时间变化趋势",
            show_title_size=16,
            dpi=100,
            xlabel="日期",
            ylabel="评论数量",
            format_dates=True,
        )

    def analyze_comment_hour_distribution(self):
        """分析评论数量按小时分布并生成柱状图（基于所有评论）。"""
        if self.df is None:
            print("数据未加载，无法进行评论小时分布分析。")
            return
        if not pd.api.types.is_datetime64_any_dtype(self.df["评论时间"]):
            self.df["评论时间"] = pd.to_datetime(self.df["评论时间"])
        self.df["评论小时"] = self.df["评论时间"].dt.hour
        comment_counts_by_hour = self.df["评论小时"].value_counts().sort_index()
        full_hour_index = pd.Index(range(24))
        comment_counts_by_hour = comment_counts_by_hour.reindex(
            full_hour_index, fill_value=0
        )
        if comment_counts_by_hour.empty:
            print("没有足够的数据进行评论小时分布分析。")
            return
        self.plot_figure(
            plot_data=(
                comment_counts_by_hour.index,
                comment_counts_by_hour.values,
            ),
            plot_type="bar",
            save_filename="comment_hour_distribution.png",
            x=1600,
            y=900,
            show_plot=True,
            show_title="评论数量按小时分布",
            show_title_size=16,
            dpi=100,
            palette="viridis",
            xlabel="小时",
            ylabel="评论数量",
            xticks=range(24),
        )

    def analyze_sentiment(self):
        if self.df is None or self.df.empty:
            print("评论数据为空，无法进行情感分析。")
            return
        if "sentiment_score" not in self.df.columns:
            self.df["sentiment_score"] = self.df["评论内容"].apply(
                lambda x: SnowNLP(str(x)).sentiments if pd.notnull(x) else None
            )

        def classify_sentiment(score):
            if score is None:
                return "未知"
            elif score > 0.7:
                return "积极"
            elif score < 0.3:
                return "消极"
            else:
                return "中立"

        if "sentiment_label" not in self.df.columns:
            self.df["sentiment_label"] = self.df["sentiment_score"].apply(
                classify_sentiment
            )
        sentiment_counts = self.df["sentiment_label"].value_counts()
        if not sentiment_counts.empty:
            self.plot_figure(
                plot_data=(
                    sentiment_counts.values,
                    sentiment_counts.index,
                ),
                plot_type="pie",
                save_filename="comment_sentiment_distribution.png",
                x=800,
                y=800,
                show_plot=True,
                show_title="评论情感分布",
                show_title_size=16,
                dpi=100,
                autopct="%1.1f%%",
                startangle=140,
                colors=sns.color_palette("pastel"),
            )
        else:
            print("没有足够的有效情感分析结果来生成分布图。")
        average_sentiment_score = self.df["sentiment_score"].dropna().mean()
        # print(f"评论的平均情感分数 (0-1, 1为最积极): {average_sentiment_score:.4f}")

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
        self.plot_figure(
            plot_data=wordcloud,
            plot_type="imshow",
            save_filename="comment_wordcloud.png",
            x=1600,
            y=900,
            show_plot=True,
            show_title="评论内容词云",
            show_title_size=16,
            dpi=100,
        )

    def _render_radar_plot_on_ax(self, ax, plot_data, show_title: str = "", show_title_size: int = 16, is_display: bool = False):
        """
        内部辅助方法：在给定的Axes对象上绘制雷达图。
        :param ax: matplotlib Axes对象。
        :param plot_data: 包含雷达图数据的字典。
        :param show_title: 显示图表的标题（仅在is_display为True时有效）。
        :param show_title_size: 标题字体大小。
        :param is_display: 是否为显示模式（True则显示标题）。
        """
        categories = plot_data['categories']
        values_top5_avg = plot_data['values_top5_avg']
        values_avg = plot_data['values_avg']

        num_vars = len(categories)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles = angles + angles[:1] # 闭合雷达图

        # 绘制红线（赞数Top5评论的平均值）
        ax.plot(angles, values_top5_avg + values_top5_avg[:1], 'o-', linewidth=2, color='red', label='赞数Top5评论平均')
        ax.fill(angles, values_top5_avg + values_top5_avg[:1], color='red', alpha=0.25)

        # 绘制蓝线（所有评论的平均值）
        ax.plot(angles, values_avg + values_avg[:1], 'o-', linewidth=2, color='blue', label='所有评论平均')
        ax.fill(angles, values_avg + values_avg[:1], color='blue', alpha=0.25)

        ax.set_theta_offset(np.pi / 2) # 设置0度在顶部
        ax.set_theta_direction(-1) # 顺时针方向

        # 设置径向轴标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontproperties=fm.FontProperties(fname=self.font_path), fontsize=12)

        # 不显示径向刻度
        ax.set_yticks([])
        ax.set_yticklabels([])

        # 设置径向轴的范围，确保所有数据点都在0到1之间，并且图表能显示完整的圆
        ax.set_ylim(0, 1) 

        ax.legend(loc='upper right', bbox_to_anchor=(1.1, 1.1), prop=fm.FontProperties(fname=self.font_path))

        if is_display and show_title:
            ax.set_title(show_title, fontsize=show_title_size, fontproperties=fm.FontProperties(fname=self.font_path))

    def _display_radar_plot(self, plot_data, show_title: str, show_title_size: int, x: int, y: int, dpi: int):
        """
        在新窗口显示雷达图。
        """
        display_figsize = (x / dpi, y / dpi)
        display_fig = plt.figure(figsize=display_figsize, dpi=dpi)
        display_ax = display_fig.add_subplot(111, polar=True) # 极坐标投影

        self._render_radar_plot_on_ax(display_ax, plot_data, show_title, show_title_size, is_display=True)

        display_fig.tight_layout()
        plt.show()
        plt.close(display_fig)

    def _save_radar_plot(self, plot_data, save_filename: str, x: int, y: int, dpi: int, save_format: str):
        """
        将雷达图保存到文件，无标题，透明背景。
        """
        save_figsize = (x / dpi, y / dpi)
        save_fig = plt.figure(figsize=save_figsize, dpi=dpi)
        save_ax = save_fig.add_subplot(111, polar=True) # 极坐标投影

        self._render_radar_plot_on_ax(save_ax, plot_data, is_display=False) # 不显示标题

        save_fig.subplots_adjust(bottom=0, top=1, left=0, right=1) # 紧密布局

        if not save_filename.lower().endswith(f".{save_format}"):
            save_filename_with_ext = f"{os.path.splitext(save_filename)[0]}.{save_format}"
        else:
            save_filename_with_ext = save_filename

        getSavePath = os.path.join(self.output_dir, save_filename_with_ext)

        plt.savefig(
            getSavePath,
            bbox_inches="tight",
            format=save_format,
            transparent=True, # 严格要求透明背景
            dpi=dpi,
        )
        print(
            f"图片已保存到: {getSavePath} (格式: {save_format}, 透明背景: True)"
        )
        plt.close(save_fig)

    def analyze_radar_chart(self, show_plot: bool = True):
        """
        生成雷达图，对比赞数Top5评论的平均值和所有评论的平均值。
        维度：用户等级、回复数、点赞数、是否是大会员。
        :param show_plot: 是否在弹窗显示图表。
        """
        if self.df is None or self.df.empty:
            print("评论数据为空，无法生成雷达图。")
            return

        # 1. 计算所有评论的平均特征
        avg_level = self.df["用户等级"].mean()
        avg_reply_num = self.df["回复数"].mean()
        avg_like_num = self.df["点赞数"].mean()
        avg_vip = (self.df["是否是大会员"] == "是").astype(int).mean()

        # print(f"所有评论的平均特征:")
        # print(f"  等级: {avg_level:.2f}, 回复数: {avg_reply_num:.2f}, 点赞数: {avg_like_num:.2f}, 大会员: {avg_vip:.2f}")

        # 2. 找出点赞数Top5的评论，并计算其平均特征
        if self.df.empty:
            print("评论数据为空，无法计算Top5评论。")
            return

        # 确保点赞数是数值类型，并处理NaN值
        df_sorted_by_like = self.df.sort_values(by="点赞数", ascending=False).copy()

        # 确保至少有5条评论，否则取所有评论
        top5_comments = df_sorted_by_like.head(5)

        if top5_comments.empty:
            print("没有足够的评论数据来计算Top5评论的平均特征。")
            return

        top5_avg_level = top5_comments["用户等级"].mean()
        top5_avg_reply_num = top5_comments["回复数"].mean()
        top5_avg_like_num = top5_comments["点赞数"].mean()
        top5_avg_vip = (top5_comments["是否是大会员"] == "是").astype(int).mean()

        # print(f"\n赞数Top5评论的平均特征:")
        # print(f"  等级: {top5_avg_level:.2f}, 回复数: {top5_avg_reply_num:.2f}, 点赞数: {top5_avg_like_num:.2f}, 大会员: {top5_avg_vip:.2f}")

        # 3. 数据归一化
        categories = ["用户等级", "回复数", "点赞数", "是否是大会员"]

        # 定义每个维度的最大值，用于归一化
        max_level = 6
        max_vip = 1

        # 回复数和点赞数：取两组数据中该维度上的最大值作为归一化范围
        # 确保至少为1，避免除以0
        max_reply_num_for_norm = max(avg_reply_num, top5_avg_reply_num)
        if max_reply_num_for_norm == 0: max_reply_num_for_norm = 1

        max_like_num_for_norm = max(avg_like_num, top5_avg_like_num)
        if max_like_num_for_norm == 0: max_like_num_for_norm = 1

        # print("\n--- 各维度归一化范围 ---")
        # print(f"用户等级归一化最大值: {max_level}")
        # print(f"回复数归一化最大值 (取两组中最大): {max_reply_num_for_norm}")
        # print(f"点赞数归一化最大值 (取两组中最大): {max_like_num_for_norm}")
        # print(f"大会员归一化最大值: {max_vip}")

        # 归一化赞数Top5评论的平均值
        normalized_top5_avg_values = [
            top5_avg_level / max_level,
            top5_avg_reply_num / max_reply_num_for_norm,
            top5_avg_like_num / max_like_num_for_norm,
            top5_avg_vip / max_vip
        ]

        # 归一化所有评论的平均值
        normalized_avg_values = [
            avg_level / max_level,
            avg_reply_num / max_reply_num_for_norm,
            avg_like_num / max_like_num_for_norm,
            avg_vip / max_vip
        ]

        # 确保归一化后的值在0-1之间，防止浮点数误差导致超出
        normalized_top5_avg_values = [min(1.0, max(0.0, v)) for v in normalized_top5_avg_values]
        normalized_avg_values = [min(1.0, max(0.0, v)) for v in normalized_avg_values]

        # print("\n--- 归一化后的数据 ---")
        # print(f"赞数Top5评论平均归一化值: {normalized_top5_avg_values}")
        # print(f"所有评论平均归一化值: {normalized_avg_values}")

        # 4. 绘制雷达图
        plot_data = {
            'categories': categories,
            'values_top5_avg': normalized_top5_avg_values,
            'values_avg': normalized_avg_values
        }

        # 调用独立的保存函数
        self._save_radar_plot(
            plot_data=plot_data,
            save_filename="comment_radar_chart.png",
            x=1000,
            y=1000,
            dpi=100,
            save_format="png"
        )

        # 调用独立的显示函数
        if show_plot:
            self._display_radar_plot(
                plot_data=plot_data,
                show_title="评论特征雷达图：赞数Top5评论平均 vs 所有评论平均",
                show_title_size=16,
                x=1000,
                y=1000,
                dpi=100
            )

    def run_all_analysis(self):
        if self.load_data():
            self.analyze_ip_distribution()
            self.analyze_vip_status()
            self.analyze_gender_distribution()
            self.analyze_level_distribution()
            self.analyze_comment_time_trend()
            self.analyze_comment_hour_distribution()
            self.analyze_sentiment()
            self.generate_wordcloud()
            self.analyze_radar_chart()
            print("所有分析已完成。")

    def run_mini_analysis(self):
        if self.load_data():
            self.analyze_comment_time_trend()
            self.analyze_comment_hour_distribution()
            self.analyze_sentiment()
            self.generate_wordcloud()
            print("mini分析已完成。")
