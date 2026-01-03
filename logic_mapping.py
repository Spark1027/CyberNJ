import numpy as np
from logic_model import predict_mapping


def predict_mbti(constitution_scores, answers=None):
    """
    业务接口：根据体质得分和原始问卷预测 MBTI 及 五行得分
    """
    if answers is None:
        answers = [0] * 67

    # 1. 调用神经网络预测 MBTI
    mbti_result, _ = predict_mapping(
        tcm_scores=constitution_scores,
        answers=answers
    )

    # 2. 【新增】调用基于中医理论的线性映射计算五行
    five_elements_result = calculate_five_elements_matrix(constitution_scores)

    return mbti_result, five_elements_result


def calculate_five_elements_matrix(tcm_scores):
    """
    基于中医脏腑理论的线性映射：9种体质 -> 5行能量
    """
    # 1. 定义体质顺序 (向量 x)
    # 顺序：平和, 气虚, 阳虚, 阴虚, 痰湿, 湿热, 血瘀, 气郁, 特禀
    labels = ['平和质', '气虚质', '阳虚质', '阴虚质', '痰湿质', '湿热质', '血瘀质', '气郁质', '特禀质']

    # 提取分数向量 (归一化到 0-1 范围以便计算权重，防止溢出)
    # 假设输入分数是 0-100
    score_vector = np.array([tcm_scores.get(k, 0) for k in labels]) / 100.0

    # 2. 定义权重矩阵 W (5x9)
    # 行：木, 火, 土, 金, 水
    # 列：平和, 气虚, 阳虚, 阴虚, 痰湿, 湿热, 血瘀, 气郁, 特禀
    # -----------------------------------------------------------------------------------
    # 权重设定依据：
    # 平和质：对五行都有均衡的加持 (0.2)
    # 气郁 -> 木 (0.9)
    # 湿热 -> 火 (0.7), 土 (0.3)
    # 阴虚 -> 火 (0.6), 水 (0.4), 木 (0.3)
    # 痰湿 -> 土 (0.8), 水 (0.2)
    # 气虚 -> 土 (0.6), 金 (0.5)
    # 阳虚 -> 水 (0.8), 土 (0.2)
    # 血瘀 -> 木 (0.4), 火 (0.4)
    # 特禀 -> 金 (0.8)
    # -----------------------------------------------------------------------------------

    weights = np.array([
        # 平   气虚  阳虚  阴虚  痰湿  湿热  血瘀  气郁  特禀
        [0.2, 0.1, 0.1, 0.3, 0.1, 0.2, 0.5, 0.9, 0.1],  # 木 (Wood) - 肝
        [0.2, 0.2, 0.1, 0.7, 0.1, 0.8, 0.5, 0.3, 0.1],  # 火 (Fire) - 心
        [0.2, 0.8, 0.4, 0.1, 0.9, 0.5, 0.1, 0.2, 0.1],  # 土 (Earth) - 脾
        [0.2, 0.7, 0.2, 0.2, 0.4, 0.1, 0.1, 0.1, 0.9],  # 金 (Metal) - 肺
        [0.2, 0.1, 0.9, 0.6, 0.4, 0.2, 0.2, 0.1, 0.2]  # 水 (Water) - 肾
    ])

    # 3. 矩阵乘法: y = W * x
    # 结果维度: (5,)
    elements_raw = np.dot(weights, score_vector)

    # 4. 后处理：归一化与缩放
    # 矩阵乘法后的值可能会超过1，也可能很小，需要映射回 0-100 的直观分数
    # 这里的逻辑是：如果体质分很高，对应的脏腑“能量/负荷”就高

    # 简单的 MinMax 归一化是不够的，我们希望保留强弱对比
    # 采用 sigmoid 变体或直接缩放截断

    elements_scaled = elements_raw * 60 + 20  # 线性变换，保底20分

    # 限制在 10-95 之间 (避免 0 或 100 这种极端值)
    elements_scaled = np.clip(elements_scaled, 10, 95)

    # 5. 格式化输出
    element_names = ['木', '火', '土', '金', '水']
    result = {name: int(score) for name, score in zip(element_names, elements_scaled)}

    return result


def calculate_score_from_questionnaire(answers):
    """
    (保持你之前的逻辑不变)
    """
    # ... 省略之前的实现代码 ...
    # 仅为了占位，请保留你logic_mapping中原本完整的函数内容
    if len(answers) != 67:
        return {}

    slices = {
        '阳虚质': answers[0:7], '阴虚质': answers[7:15], '气虚质': answers[15:23],
        '痰湿质': answers[23:31], '湿热质': answers[31:38], '血瘀质': answers[38:45],
        '气郁质': answers[45:52], '特禀质': answers[52:59], '平和质': answers[59:67]
    }
    scores = {}
    for c_type, sub_answers in slices.items():
        raw_score = sum(sub_answers)
        n = len(sub_answers)
        if n == 0: scores[c_type] = 0; continue
        scores[c_type] = round(((raw_score - n) / (n * 4)) * 100, 2)
    return scores