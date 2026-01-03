import pandas as pd
import streamlit as st


def load_questions(file_path="data/tcm_questions.xlsx"):
    """读取题目，并处理缺失的 direction 列"""
    try:
        df = pd.read_excel(file_path)
        # 如果没有 direction 列，默认设为 1 (正向)
        if 'direction' not in df.columns:
            df['direction'] = 1
        return df
    except Exception as e:
        st.error(f"❌ 读取题库失败，请检查 data/tcm_questions.xlsx 是否存在。\n错误信息: {e}")
        return None


def calculate_scores(user_answers_df):
    """
    计算王琦九种体质得分
    输入: DataFrame (包含 type, score, direction)
    """
    results = {}

    # 1. 处理反向计分 (1->5, 5->1)
    # 公式: 实际分 = 6 - 原始分 (当 direction 为 -1 时)
    user_answers_df['final_score'] = user_answers_df.apply(
        lambda row: (6 - row['score']) if row.get('direction', 1) == -1 else row['score'],
        axis=1
    )

    # 2. 分组计算转化分
    types = user_answers_df['type'].unique()

    for t_type in types:
        sub_df = user_answers_df[user_answers_df['type'] == t_type]

        original_sum = sub_df['final_score'].sum()
        num_questions = len(sub_df)

        # 王琦公式: [(原始分 - 题数) / (题数 * 4)] * 100
        if num_questions > 0:
            converted = ((original_sum - num_questions) / (num_questions * 4)) * 100
            converted = max(0, min(100, converted))  # 限制在 0-100
            results[t_type] = round(converted, 2)
        else:
            results[t_type] = 0.0

    return results


def get_diagnosis_result(scores):
    """
    (可选) 简单的规则判定，用于在前端显示主次体质
    这里只返回分数最高的体质作为主体质
    """
    # 排除平和质，看病理体质里谁最高
    pathological = {k: v for k, v in scores.items() if k != "平和质"}
    if not pathological:
        return "平和质"

    max_type = max(pathological, key=pathological.get)
    max_score = pathological[max_type]

    # 平和质判定逻辑比较复杂，这里简化处理：
    # 如果平和质 >= 60 且其他都 < 40，则为主平和
    if scores.get("平和质", 0) >= 60 and max_score < 40:
        return "平和质"

    return max_type