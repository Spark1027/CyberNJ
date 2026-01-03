import streamlit as st
import pandas as pd
import json
import random
import time
import re
import os
import csv
from datetime import datetime
from io import BytesIO

from logic_tcm import load_questions, calculate_scores, get_diagnosis_result
from logic_mapping import predict_mbti
from utils_viz import plot_radar, plot_bar, generate_share_image

# ==========================================
# 页面配置
# ==========================================
st.set_page_config(
    page_title="赛博内经 Cyber NJ",
    layout="wide",
    page_icon="☯️",
    initial_sidebar_state="expanded"
)

# ==========================================
# 0. 数据持久化 & URL同步模块 (新增)
# ==========================================
DATA_FILE = "research_data.csv"
ADMIN_PASSWORD = "admin2026"


def init_csv_file():
    """初始化数据文件"""
    if not os.path.exists(DATA_FILE):
        headers = [
            "timestamp", "consent", "gender", "real_mbti",
            "ai_mbti", "constitution_main",
            "score_pinghe", "score_qixu", "score_yangxu", "score_yinxu",
            "score_tanshi", "score_shire", "score_xueyu", "score_qiyu", "score_tebing",
            "raw_answers_str"
        ]
        with open(DATA_FILE, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)


def save_research_data(consent, gender, real_mbti, ai_mbti, main_const, scores, answers_list):
    """保存数据到本地 CSV"""
    init_csv_file()

    # 将答案列表压缩为字符串
    answers_str = "".join([str(x) for x in answers_list])

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Yes" if consent else "No",
        gender if consent else "N/A",
        real_mbti if consent else "N/A",
        ai_mbti,
        main_const,
        scores.get("平和质", 0), scores.get("气虚质", 0), scores.get("阳虚质", 0),
        scores.get("阴虚质", 0), scores.get("痰湿质", 0), scores.get("湿热质", 0),
        scores.get("血瘀质", 0), scores.get("气郁质", 0), scores.get("特禀质", 0),
        answers_str
    ]

    try:
        with open(DATA_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    except Exception as e:
        st.error(f"数据保存失败: {e}")


# --- URL 同步功能 (防丢失) ---
def update_url_from_state():
    """将答案同步到 URL 参数"""
    ans_str = ""
    for i in range(67):
        ans_str += str(st.session_state.get(f"q_{i}", 1))
    st.query_params["d"] = ans_str


def load_state_from_url():
    """从 URL 恢复答案"""
    params = st.query_params
    if "d" in params:
        ans_str = params["d"]
        if len(ans_str) == 67 and ans_str.isdigit():
            for i, char in enumerate(ans_str):
                st.session_state[f"q_{i}"] = int(char)
            return True
    return False


# ==========================================
# CSS 样式 (含移动端自适应)
# ==========================================
st.markdown("""
<style>
    /* =================================
       1. PC端基础样式
       ================================= */
    /* 滚动容器样式 */
    .scrollable-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 5px 20px 20px 20px;
        border: 1px solid #f0f2f6;
        border-radius: 10px;
        background-color: #ffffff;
        margin-bottom: 20px;
    }
    /* 隐藏 Radio 的 label */
    .stRadio > label { display: none; }
    /* 卡片样式 */
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* 步骤卡片 */
    .step-card {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #FF4B4B;
        margin-bottom: 10px;
    }

    /* =================================
       2. 移动端自适应 (Mobile Responsive)
       ================================= */
    @media only screen and (max-width: 600px) {
        /* 缩小大标题 */
        h1 {
            font-size: 1.8rem !important;
        }
        /* 缩小副标题 */
        h3 {
            font-size: 1.2rem !important;
        }
        /* 调整 Metric 指标卡字体 */
        div[data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.9rem !important;
        }
        /* 调整按钮大小，手机上撑满宽度 */
        button {
            width: 100% !important; 
        }
        /* 调整左右边距，防止内容贴边 */
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Prompt
# ==========================================
FULL_SYSTEM_PROMPT = """
【角色设定】
你是一位资深的中医体质辨识专家，精通《中医体质分类与判定》国家标准。
【任务】
1. 通过对话判断用户的中医体质（9种体质之一或复合）。
2. 根据"身心一元论"，推测该体质对应的 MBTI 人格类型。
3. 在问诊结束时，必须输出一段严格的 JSON 代码用于系统可视化。

【输出格式要求】
当信息收集完毕后，请仅输出以下 JSON 数据块，不要包含 markdown 标记，格式如下：

[[JSON_START]]
{
  "diagnosis_scores": {
    "平和质": 20, "气虚质": 80, "阳虚质": 40, "阴虚质": 30, 
    "痰湿质": 20, "湿热质": 10, "血瘀质": 10, "气郁质": 15, "特禀质": 5
  },
  "predicted_mbti": "ISFJ",
  "five_elements": {
    "木": 40, "火": 30, "土": 80, "金": 60, "水": 40
  },
  "analysis_summary": "你的气虚质特征明显，元气不足导致性格偏向内敛（I）..."
}
[[JSON_END]]
"""


# ==========================================
# 辅助函数
# ==========================================
def parse_pasted_result(text):
    try:
        pattern = r"\[\[JSON_START\]\](.*?)\[\[JSON_END\]\]"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = text[start:end]
            else:
                return None, "未找到 JSON 数据格式，请确认 AI 输出正确。"
        json_str = json_str.replace("```json", "").replace("```", "").strip()
        data = json.loads(json_str)
        return data, None
    except Exception as e:
        return None, f"解析出错: {str(e)}"


# 加载动画函数
def simulate_loading_animation():
    """
    模拟赛博风格的加载过程
    """
    loading_texts = [
        "📡 正在建立神经元与经络的连接...",
        "🖐️ 赛博悬丝诊脉中，请保持呼吸平稳...",
        "☯️ 正在解析您的阴阳虚实数据...",
        "💊 神经网络正在抓取云端方剂...",
        "🧠 正在由体质映射 MBTI 人格模型...",
        "✅ 诊断完成，正在生成全息报告..."
    ]

    progress_bar = st.progress(0, text="启动赛博诊断程序...")

    for percent_complete in range(100):
        time.sleep(0.02)  # 调整速度
        text_index = int(percent_complete / (100 / len(loading_texts)))
        if text_index < len(loading_texts):
            current_text = loading_texts[text_index]
            progress_bar.progress(percent_complete + 1, text=current_text)

    time.sleep(0.5)
    progress_bar.empty()


# ==========================================
# 核心交互：数据收集弹窗 (Dialog) - 新增
# ==========================================
@st.dialog("🧬 数据捐赠计划 (Data Donation)")
def show_consent_dialog(scores, main_diagnosis, mbti_pred, elements, answers_net):
    st.markdown("""
    **您是否愿意将本次匿名测试数据提供给后续课题研究？**

    您的贡献将帮助我们要优化【中医体质-MBTI映射模型】的准确率。
    *所有信息均严格保密，仅用于学术统计。*
    """)

    st.warning("⚠️ 如果本次测试使用的是【随机一键填表】，请务必选择「不参与」或「拒绝」。")

    # 意愿选择
    consent = st.radio("您的意愿：", ["愿意参与研究", "仅查看结果，不参与"], index=0)

    gender = "保密"
    real_mbti = "Unknown"

    if consent == "愿意参与研究":
        c1, c2 = st.columns(2)
        with c1:
            gender = st.selectbox("您的性别", ["男", "女"], index=0)
        with c2:
            mbti_options = ["不清楚", "ISTJ", "ISFJ", "INFJ", "INTJ", "ISTP", "ISFP", "INFP", "INTP",
                            "ESTP", "ESFP", "ENFP", "ENTP", "ESTJ", "ESFJ", "ENFJ", "ENTJ"]
            real_mbti = st.selectbox("您真实的 MBTI (如有)", mbti_options, index=0)

    st.divider()

    if st.button("确认并查看报告", type="primary", use_container_width=True):
        # 1. 保存数据
        is_willing = (consent == "愿意参与研究")
        save_research_data(
            consent=is_willing,
            gender=gender,
            real_mbti=real_mbti,
            ai_mbti=mbti_pred,
            main_const=main_diagnosis,
            scores=scores,
            answers_list=answers_net
        )

        # 2. 将结果存入 session 并关闭弹窗
        st.session_state.tab1_result = {
            "scores": scores,
            "main_diagnosis": main_diagnosis,
            "mbti": mbti_pred,
            "elements": elements
        }
        st.rerun()


# ==========================================
# 初始化逻辑 - 新增
# ==========================================
if "data_loaded" not in st.session_state:
    if load_state_from_url():
        st.toast("已恢复上次填写进度", icon="📂")
    st.session_state.data_loaded = True

# ==========================================
# 侧边栏
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/yin-yang.png", width=80)
    st.title("赛博内经 Guide")

    with st.expander("📖 量表测试操作流程", expanded=True):
        st.markdown("""
        **1. 问卷测试**
        右侧填写 67 题，支持一键随机填充。

        **2. 结果生成**
        查看体质与 MBTI 映射图表。

        **3. 分享海报**
        生成带有二维码的诊断单。
        """)
    st.divider()

    # 🔥 管理员数据下载通道 (仅在有密码时显示)
    with st.expander("🔐 管理员模式 (Admin)"):
        pwd = st.text_input("输入管理员密码", type="password")
        if pwd == ADMIN_PASSWORD:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8-sig") as f:
                    st.download_button(
                        label="📥 下载收集的数据 (CSV)",
                        data=f,
                        file_name=f"research_data_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("暂无数据文件")

    st.caption("""
    © 2026 CyberNJ Team. All Rights Reserved.

    Contact Us: spark_shi@tju.edu.cn
    """)

# ==========================================
# 主页面逻辑
# ==========================================
# 🔥 移动端 引导提示
with st.expander("📱 手机用户必读 (点击展开)", expanded=True):
    st.warning("""
    **⚠️ 如果您正在使用微信、小红书、QQ等应用的内置浏览器：**
    **图片下载可能失败，AI链接无法跳转**

    👉 **解决方案**：请点击屏幕右上角的 **[...]**，选择 **"在浏览器打开"**，即可获得完整体验。
    """)

st.title("🧬 赛博内经：AI 中医体质与 MBTI 分析系统")
st.markdown("##### *Cyber NJ: An AI-Powered Approach to TCM Constitution & MBTI Profiling*")

# 顶部免责声明
st.warning(
    "⚠️ 免责声明：本测试仅提供计算服务，测试结果仅供参考，在大规模评估和优化映射模型前不具备医学意义。如有不适，请咨询专业医师。")

st.divider()

if "tab1_result" not in st.session_state:
    st.session_state.tab1_result = None

tab1, tab2 = st.tabs(["📋 量表测评 (Standard Scale)", "🤖 AI 问诊 (Human-in-the-loop)"])

# --------------------------------------------------------
# TAB 1: 量表测评
# --------------------------------------------------------
with tab1:
    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.info("💡 请在下方滚动窗口中完成 67 道题目。")
    with col_btn:
        # 随机填表功能
        if st.button("🎲 随机一键填表", type="secondary"):
            target_type_index = random.randint(0, 8)
            base_answers = []
            for _ in range(67):
                if random.random() < 0.8:
                    base_answers.append(random.randint(1, 2))
                else:
                    base_answers.append(3)

            slices_indices = [(0, 7), (7, 15), (15, 23), (23, 31), (31, 38), (38, 45), (45, 52), (52, 59), (59, 67)]
            start, end = slices_indices[target_type_index]
            for i in range(start, end):
                base_answers[i] = random.randint(4, 5)

            for i in range(67):
                st.session_state[f"q_{i}"] = base_answers[i]

            # 🔥 随机填表后也更新 URL
            update_url_from_state()
            st.rerun()

    questions_df = load_questions()

    if questions_df is not None:
        with st.form("scale_form"):
            # 使用原生容器，解决顶部空白问题
            with st.container(height=500, border=True):
                for idx, row in questions_df.iterrows():
                    st.markdown(f"**{idx + 1}. {row['question']}**")
                    st.radio(
                        "选项", [1, 2, 3, 4, 5],
                        captions=["没有", "很少", "有时", "经常", "总是"],
                        horizontal=True,
                        label_visibility="collapsed",
                        key=f"q_{idx}"
                    )
                    st.divider()

            submitted = st.form_submit_button("🚀 提交并分析", type="primary", width="stretch")

        # 🟢 处理提交逻辑
        if submitted:
            # 🔥 1. 先把当前进度同步到 URL (防止此时用户刷新丢失)
            update_url_from_state()

            # 调用加载动画
            simulate_loading_animation()

            answers_for_logic_tcm = []
            answers_for_neural_net = []

            for idx, row in questions_df.iterrows():
                val = st.session_state.get(f"q_{idx}", 1)
                answers_for_logic_tcm.append({
                    "type": row['type'],
                    "score": val,
                    "direction": row.get('direction', 1)
                })
                answers_for_neural_net.append(int(val))

            scores = calculate_scores(pd.DataFrame(answers_for_logic_tcm))
            main_diagnosis = get_diagnosis_result(scores)

            mbti, elements = predict_mbti(constitution_scores=scores, answers=answers_for_neural_net)

            # 🔥 触发弹窗 (而不是直接设置 session_state.tab1_result)
            show_consent_dialog(scores, main_diagnosis, mbti, elements, answers_for_neural_net)

        # 🟢 结果展示区域
        if st.session_state.tab1_result:
            res = st.session_state.tab1_result
            st.divider()
            st.success("✅ 分析完成！Analysis Complete.")

            k1, k2, k3 = st.columns(3)
            k1.metric("主导体质", res["main_diagnosis"])
            k2.metric("映射人格", res["mbti"])
            k3.metric("五行特征", "复合型")

            col_a, col_b = st.columns([1, 1])
            with col_a:
                st.subheader("📊 体质得分分布")
                plot_bar(res["scores"])
            with col_b:
                st.subheader(f"🧠 MBTI人格映射：{res['mbti']} ")
                img_path = f"assets/mbti/{res['mbti']}.png"
                if os.path.exists(img_path):
                    st.image(img_path, caption=f"MBTI Archetype: {res['mbti']}", width=200)
                else:
                    st.info(f"（提示：请在 assets/mbti/ 放入 {res['mbti']}.png 以显示图片）")
                st.write("🌌 **五行能量雷达**")
                plot_radar(res["elements"])

            st.divider()
            st.subheader("📤 生成诊断报告")
            share_img = generate_share_image(res["main_diagnosis"], res["mbti"], res["scores"], res["elements"])
            buf = BytesIO()
            share_img.save(buf, format="PNG")

            c_img, c_dl = st.columns([1, 2])
            with c_img:
                st.image(share_img, caption="预览图", width=150)
            with c_dl:
                st.download_button(
                    label="💾 下载高清诊断单 (PNG)",
                    data=buf.getvalue(),
                    file_name=f"CyberNJ_Report_{res['mbti']}.png",
                    mime="image/png",
                    type="primary"
                )
                # 🔥 新增提示：下载失败处理
                st.caption("⚠️ 点下载没反应？请点击右上角[...]选择「在浏览器打开」")

# --------------------------------------------------------
# TAB 2: AI 问诊
# --------------------------------------------------------
with tab2:
    st.header("🤖 AI 问诊可视化工作台")
    st.caption("Human-in-the-loop Workflow")
    st.markdown('<div class="step-card"><h4>Step 1: 获取专家提示词</h4><p>复制下方代码块，发送给 AI。</p></div>',
                unsafe_allow_html=True)
    st.code(FULL_SYSTEM_PROMPT, language="json")

    st.markdown('<div class="step-card"><h4>Step 2: 前往 AI 平台问诊</h4></div>', unsafe_allow_html=True)

    # 🔥 新增提示：外链失败处理
    st.caption("⚠️ 如点击下方按钮无反应，请复制链接到浏览器访问，或使用「在浏览器打开」功能。")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.link_button("🚀 DeepSeek", "https://chat.deepseek.com", width="stretch")
    with c2:
        st.link_button("🌙 Kimi 智能", "https://kimi.moonshot.cn", width="stretch")
    with c3:
        st.link_button("🤖 ChatGPT", "https://chatgpt.com", width="stretch")

    st.markdown('<div class="step-card"><h4>Step 3: 粘贴 AI 返回的诊断数据</h4></div>', unsafe_allow_html=True)

    demo_json = """[[JSON_START]]
{
  "diagnosis_scores": {"平和质": 20, "气虚质": 85, "阳虚质": 60, "阴虚质": 30, "痰湿质": 20, "湿热质": 10, "血瘀质": 10, "气郁质": 15, "特禀质": 5},
  "predicted_mbti": "ISFJ",
  "five_elements": {"木": 30, "火": 20, "土": 90, "金": 60, "水": 30},
  "analysis_summary": "用户主诉乏力..."
}
[[JSON_END]]"""

    pasted_text = st.text_area("在此粘贴 (Ctrl+V)", height=150, value=demo_json)

    if st.button("✨ 解析并可视化", type="primary", width="stretch"):
        data, error = parse_pasted_result(pasted_text)
        if error:
            st.error(f"❌ {error}")
        else:
            st.success("✅ 数据解析成功！")
            scores = data.get("diagnosis_scores", {})
            mbti = data.get("predicted_mbti", "Unknown")
            elements = data.get("five_elements", {})
            summary = data.get("analysis_summary", "")
            main_type = max(scores, key=scores.get) if scores else "未知"

            k1, k2, k3 = st.columns(3)
            k1.metric("AI 诊断体质", main_type)
            k2.metric("映射人格", mbti)
            k3.metric("五行特征", "复合型")

            st.divider()
            col_viz1, col_viz2 = st.columns(2)
            with col_viz1:
                st.subheader("📊 体质得分")
                plot_bar(scores)
            with col_viz2:
                st.subheader("🕸️ 五行雷达")
                plot_radar(elements)
            st.info(f"📋 **AI 诊断摘要：** {summary}")

# ==========================================
# 参考文献
# ==========================================
st.divider()
with st.expander("📚 参考文献与理论依据 (References & Theoretical Basis)"):
    st.markdown("""
    本系统的算法模型基于以下中医体质学与藏象学说经典文献构建：

    1.  **王琦**. (2005). *中医体质学*. 北京: 人民卫生出版社.
        * *依据：九种中医体质的分类标准、特征描述与判定逻辑。*
    2.  **中华中医药学会**. (2009). *中医体质分类与判定 (ZYYXH/T157-2009)*.
        * *依据：国家标准量表计分方法与阈值设定。*
    3.  **孙广仁**. (2002). *中医基础理论*. 北京: 中国中医药出版社.
        * *依据：五行（木火土金水）与五脏（肝心脾肺肾）的生理病理映射关系。*
    4.  **张伯礼**. (2008). *中医内科学*. 北京: 人民卫生出版社.
        * *依据：特定体质（如阳虚、气郁）与脏腑功能失调的病机关联。*

    > **特别说明（叠甲）**: MBTI 映射部分基于"身心一元论"的探索性研究，结合了卷积神经网络的特征提取能力，旨在探索体质生理特征与心理人格特征的潜在关联，非传统中医理论的直接推论。
    """)