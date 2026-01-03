import torch
import torch.nn as nn
import numpy as np
import os
import random


# ==============================================================================
# 1. 模型定义 (保持不变)
# ==============================================================================
class MBTIPredictor(nn.Module):
    def __init__(self):
        super(MBTIPredictor, self).__init__()
        self.fc1 = nn.Linear(76, 32)
        self.fc2 = nn.Linear(32, 8)
        self.fc4 = nn.Linear(8, 16)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc4(x)
        return x


# ==============================================================================
# 2. 资源加载 (保持不变)
# ==============================================================================
MODEL_PATH = 'best_mbti_model.pth'
_model_instance = None
_num_to_mbti_map = None


def load_model_resources():
    global _model_instance, _num_to_mbti_map
    if _model_instance is not None:
        return _model_instance, _num_to_mbti_map

    if not os.path.exists(MODEL_PATH):
        print(f"[Warning] 模型文件 {MODEL_PATH} 未找到。")
        return None, None

    try:
        checkpoint = torch.load(MODEL_PATH, map_location=torch.device('cpu'), weights_only=False)
        model = MBTIPredictor()
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        _model_instance = model
        _num_to_mbti_map = checkpoint['num_to_mbti']
        return _model_instance, _num_to_mbti_map
    except Exception as e:
        print(f"[Error] 模型加载失败: {e}")
        return None, None


# ==============================================================================
# 3. 五行计算逻辑 (新增: 矩阵权重法)
# ==============================================================================
def calculate_five_elements_matrix(tcm_scores):
    """
    基于中医脏腑理论的线性映射：9种体质 -> 5行能量
    【优化版】增强差异性，使雷达图更具特征
    """
    # 1. 定义体质顺序
    labels = ['平和质', '气虚质', '阳虚质', '阴虚质', '痰湿质', '湿热质', '血瘀质', '气郁质', '特禀质']

    # -------------------------------------------------------------
    # 🔧 优化点 1: 预处理输入分数，抑制底噪
    # -------------------------------------------------------------
    # 原始分数
    raw_scores = np.array([tcm_scores.get(k, 0) for k in labels])

    # 只有当分数大于 30 (阈值) 时才计入有效贡献，
    # 否则视为“静默”状态，减少不相关的干扰
    # 但保留 "平和质" (索引0) 的原始值作为基底
    threshold_scores = np.where(raw_scores > 50, raw_scores, 0)
    threshold_scores[0] = raw_scores[0]  # 平和质不设阈值

    # 归一化输入 (0-1)
    score_vector = threshold_scores / 100.0

    # 2. 定义权重矩阵 W (5x9) - 保持不变
    # 行：木, 火, 土, 金, 水
    weights = np.array([
        # 平   气虚  阳虚  阴虚  痰湿  湿热  血瘀  气郁  特禀
        [0.1, 0.1, 0.1, 0.3, 0.1, 0.2, 0.6, 0.9, 0.1],  # 木 (降低了平和质权重 0.2->0.1)
        [0.1, 0.2, 0.1, 0.7, 0.1, 0.8, 0.5, 0.3, 0.1],  # 火
        [0.1, 0.8, 0.4, 0.1, 0.9, 0.5, 0.1, 0.2, 0.1],  # 土
        [0.1, 0.7, 0.2, 0.2, 0.4, 0.1, 0.1, 0.1, 0.9],  # 金
        [0.1, 0.1, 0.9, 0.6, 0.4, 0.2, 0.2, 0.1, 0.2]  # 水
    ])

    # 3. 矩阵乘法
    elements_raw = np.dot(weights, score_vector)

    # -------------------------------------------------------------
    # 🔧 优化点 2: 非线性放大 (重点！)
    # -------------------------------------------------------------
    # 使用指数函数 (Power Function) 拉伸差异
    # x^1.5 会让大的数值更大，小的数值更小
    elements_enhanced = np.power(elements_raw, 1.5)

    # 4. 重新缩放回 10-95
    # 先找到当前的最大值，以最大值为基准进行归一化
    if np.max(elements_enhanced) == 0:
        final_scores = elements_enhanced + 20  # 防止全0
    else:
        # 动态缩放：让最大值接近 95，最小值保留在 20 左右
        # 这样无论原始分多低，雷达图都会撑满，差异一眼可见
        norm = (elements_enhanced - np.min(elements_enhanced))
        if np.max(norm) == 0:
            ratio = 1
        else:
            ratio = 75 / np.max(norm)  # 95-20=75 的跨度

        final_scores = norm * ratio + 20

    # 5. 格式化输出
    element_names = ['木', '火', '土', '金', '水']
    result = {name: int(score) for name, score in zip(element_names, final_scores)}

    return result


# ==============================================================================
# 4. 核心预测接口 (整合了 MBTI模型预测 + 五行矩阵计算)
# ==============================================================================
def predict_mapping(tcm_scores, answers=None):
    """
    输入:
      tcm_scores: 9种体质得分字典
      answers: Excel顺序的原始问卷列表
    输出:
      mbti_result (str)
      five_elements_result (dict) - 真实计算值
    """

    # --- PART A: 准备工作 ---
    if answers is None:
        print("[Warning] predict_mapping 未接收到 answers，将使用全0补全。")
        answers = [0] * 67

    # 先计算五行得分 (因为这部分不需要 PyTorch 模型，只需要分数)
    # ✅ 这里改用了真实的矩阵计算，不再是随机数
    real_five_elements = calculate_five_elements_matrix(tcm_scores)

    model, mapper = load_model_resources()

    # --- PART B: 如果模型加载失败，返回模拟MBTI + 真实五行 ---
    if model is None:
        # 注意：这里我们返回 random MBTI，但返回 真实的五行
        return _simulate_mbti_fallback(tcm_scores), real_five_elements

    if len(answers) != 67:
        print(f"[Warning] 长度错误: {len(answers)}，自动补全。")
        answers = (answers + [0] * 67)[:67]

    # --- PART C: 数据预处理 (特征重排) ---
    q_yang = answers[0:7]
    q_yin = answers[7:15]
    q_qi = answers[15:23]
    q_phlegm = answers[23:31]
    q_damp = answers[31:38]
    q_blood = answers[38:45]
    q_qistagn = answers[45:52]
    q_special = answers[52:59]
    q_peace = answers[59:67]

    aligned_answers = (
            q_peace + q_qi + q_yang + q_yin + q_phlegm +
            q_damp + q_blood + q_qistagn + q_special
    )

    score_order = ['平和质', '气虚质', '阳虚质', '阴虚质', '痰湿质', '湿热质', '血瘀质', '气郁质', '特禀质']
    input_scores = [tcm_scores.get(k, 0) for k in score_order]
    input_76_features = aligned_answers + input_scores

    # --- PART D: 神经网络预测 MBTI ---
    input_tensor = torch.tensor(input_76_features, dtype=torch.float32).unsqueeze(0)
    input_tensor = (input_tensor - 0.0) / 1.0  # 标准化

    try:
        with torch.no_grad():
            output = model(input_tensor)
            _, pred_num = torch.max(output, 1)
            mbti_result = mapper[pred_num.item()]
    except Exception as e:
        print(f"[Error] 预测出错: {e}")
        return _simulate_mbti_fallback(tcm_scores), real_five_elements

    # ✅ 返回：神经网络预测的MBTI + 矩阵计算的五行
    return mbti_result, real_five_elements


# ==============================================================================
# 5. 备用模拟函数 (仅用于MBTI失败时)
# ==============================================================================
def _simulate_mbti_fallback(tcm_scores):
    """
    当 .pth 文件丢失时，根据最高分体质简单查表返回 MBTI
    """
    try:
        main_type = max(tcm_scores, key=tcm_scores.get)
        mapping_db = {
            "平和质": "ESFJ", "气虚质": "ISFJ", "阳虚质": "ISTJ",
            "阴虚质": "INFJ", "痰湿质": "ISFP", "湿热质": "ESTP",
            "血瘀质": "INTJ", "气郁质": "INFP", "特禀质": "ENFP"
        }
        return mapping_db.get(main_type, "ISTJ")
    except:
        return "ESTJ"