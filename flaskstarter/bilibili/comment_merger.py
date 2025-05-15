import pandas as pd
import os


class CommentMerger:
    def __init__(self):
        """
        初始化评论合并器。

        Args:
            base_comment_dir (str): 存放各个视频评论 CSV 文件的基础目录。
                                      默认值为 "./comment/bv/"。
        """
        self.base_comment_dir = "./flaskstarter/comment/bv/"
        if not os.path.isdir(self.base_comment_dir):
            print(
                f"警告：基础评论目录不存在：{self.base_comment_dir}，请确保目录存在。"
            )

    def merge_comments(
        self,
        video_ids,
        id,
        output_dir="./flaskstarter/comment/",
        output_filename=None,
    ):
        is_bv = is_bv_code(id)
        if is_bv:
            output_dir += "bv/"
        else:
            output_dir += "up/"
        all_comments = []
        valid_files_count = 0

        print(f"开始合并用户评论文件...")

        for bv in video_ids:
            file_path = os.path.join(self.base_comment_dir, f"{bv}.csv")
            if os.path.exists(file_path):
                try:
                    # 读取 CSV 文件
                    df = pd.read_csv(
                        file_path, encoding="utf-8-sig"
                    )  # 使用 utf-8-sig 处理可能的 BOM
                    # 添加 '视频BV号' 列，值为当前的 BV 号
                    df["BV号"] = bv
                    all_comments.append(df)
                    valid_files_count += 1
                    print(f"成功读取并处理文件：{file_path}")
                except FileNotFoundError:
                    print(f"警告：文件不存在：{file_path}")
                except pd.errors.EmptyDataError:
                    print(f"警告：文件为空：{file_path}")
                except Exception as e:
                    print(f"读取文件 {file_path} 时发生错误：{e}")
            else:
                print(f"警告：文件不存在：{file_path}")

        if not all_comments:
            print("没有找到任何有效的评论文件进行合并。")
            return None

        # 合并所有 DataFrame
        try:
            merged_df = pd.concat(all_comments, ignore_index=True)
        except Exception as e:
            print(f"合并 DataFrame 时发生错误：{e}")
            return None

        # 指定输出文件名和路径
        if output_filename is None:
            output_filename = f"{id}.csv"
        output_path = os.path.join(output_dir, output_filename)

        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"创建输出目录：{output_dir}")

        # 保存合并后的 DataFrame 到 CSV 文件
        try:
            merged_df.to_csv(output_path, index=False, encoding="utf-8-sig")
            print(
                f"评论合并完成！合并了 {valid_files_count} 个文件，总计 {len(merged_df)} 条评论。"
            )
            print(f"合并后的文件已保存到：{output_path}")
            return output_path
        except Exception as e:
            print(f"保存合并文件到 {output_path} 时发生错误：{e}")
            return None


def is_bv_code(input_string):
    # 转换为小写进行比较，实现大小写不敏感
    if input_string.lower().startswith("bv"):
        return 1
    else:
        return 0


# 示例用法 (这部分代码在导入 CommentMerger 类时不会自动执行)
if __name__ == "__main__":
    # 假设你已经有了这些 BV 号对应的 csv 文件在 ./comment/bv/ 目录下
    video_ids_list = [
        "BV1aeEcz9E4z",
        "BV1njEczKEYg",
    ]
    uploader_id = "12345"  # 替换成你想要的用户标识

    # 创建 CommentMerger 实例
    merger = CommentMerger()

    # 调用 merge_comments 方法进行合并
    output_csv_path = merger.merge_comments(
        video_ids_list, uploader_id
    )  # 可以指定输出目录
