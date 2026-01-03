import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import math
import os
import qrcode


# ==========================================
# 1. 五行雷达图 (Visual Optimization)
# ==========================================
def plot_radar(elements_dict):
    """
    绘制五行能量雷达图
    特性: 锁定 0-100 坐标系，顶点显示具体数值，样式美化
    """
    # 1. 数据准备
    order = ['木', '火', '土', '金', '水']
    values = [elements_dict.get(k, 0) for k in order]

    # 闭合雷达图
    values += values[:1]
    categories = order + order[:1]
    text_labels = [str(v) for v in values]

    # 2. 构建图表
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='五行能量',
        line=dict(color='#FF4B4B', width=2),
        fillcolor='rgba(255, 75, 75, 0.2)',
        mode='lines+markers+text',
        text=text_labels,
        textposition="top center",
        textfont=dict(size=14, color='#FF4B4B', family="Arial Black"),
        marker=dict(size=6, color='#FF4B4B')
    ))

    # 3. 布局设置
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showticklabels=False,
                linecolor='rgba(0,0,0,0.1)',
                gridcolor='rgba(0,0,0,0.1)'
            ),
            angularaxis=dict(
                tickfont=dict(size=14, color="black"),
                rotation=90,
                direction="clockwise"
            )
        ),
        showlegend=False,
        margin=dict(t=40, b=40, l=40, r=40),
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    # 4. 渲染 (修复参数警告)
    st.plotly_chart(fig, width="stretch")


# ==========================================
# 2. 体质柱状图 (Visual Optimization)
# ==========================================
def plot_bar(scores_dict):
    """
    绘制横向柱状图
    """
    # 排序
    sorted_items = sorted(scores_dict.items(), key=lambda x: x[1], reverse=False)
    types = [k for k, v in sorted_items]
    scores = [v for k, v in sorted_items]

    # 颜色逻辑
    colors = ['#FF4B4B' if s >= 60 else '#888888' for s in scores]
    if all(s < 60 for s in scores) and scores:
        colors[-1] = '#FF4B4B'

    fig = go.Figure(go.Bar(
        x=scores,
        y=types,
        orientation='h',
        marker_color=colors,
        text=scores,
        textposition='auto',
        opacity=0.9
    ))

    fig.update_layout(
        xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False),
        yaxis=dict(tickfont=dict(size=13)),
        margin=dict(t=10, b=10, l=10, r=10),
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    # 渲染 (修复参数警告)
    st.plotly_chart(fig, width="stretch")


# ==========================================
# 3. 生成分享海报 (终极版：含真实二维码)
# ==========================================
def generate_share_image(main_diagnosis, mbti, scores, elements):
    """
    绘制包含 MBTI 图片、五行雷达图、完整得分、真实二维码和免责声明的诊断单
    """
    # ==========================================
    # 0. 配置部分 (DEPLOY时修改这里!)
    # ==========================================
    # 部署后的 Streamlit App 真实网址
    SHARE_URL = "https://cybernj-2026.streamlit.app"

    # ----------------------------------
    # 1. 画布配置
    # ----------------------------------
    width, height = 800, 1600
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # ----------------------------------
    # 2. 字体加载 (适配云端 Linux 环境)
    # ----------------------------------
    # 优先级：项目根目录字体 > 系统字体 > 默认
    font_files = ["SimHei.ttf", "msyh.ttc", "PingFang.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    valid_font = None

    for f in font_files:
        if os.path.exists(f) or os.path.exists(os.path.join(os.getcwd(), f)):
            valid_font = f
            break

    # 如果没找到任何中文字体，使用默认
    if valid_font is None:
        valid_font = "arial.ttf"  # 假定一个英文

    try:
        # 调整字号
        font_title_main = ImageFont.truetype(valid_font, 40)  # 标题缩小防止截断
        font_subtitle = ImageFont.truetype(valid_font, 24)

        font_card_label = ImageFont.truetype(valid_font, 26)
        font_card_val = ImageFont.truetype(valid_font, 72)

        font_section = ImageFont.truetype(valid_font, 40)

        font_list_name = ImageFont.truetype(valid_font, 32)
        font_list_score = ImageFont.truetype(valid_font, 28)

        font_radar = ImageFont.truetype(valid_font, 30)

        # 底部专用
        font_slogan = ImageFont.truetype(valid_font, 34)
        font_disclaimer = ImageFont.truetype(valid_font, 18)
        font_copyright = ImageFont.truetype(valid_font, 18)
        font_qr_label = ImageFont.truetype(valid_font, 20)
    except:
        # 回退模式
        font_title_main = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_card_label = ImageFont.load_default()
        font_card_val = ImageFont.load_default()
        font_section = ImageFont.load_default()
        font_list_name = ImageFont.load_default()
        font_list_score = ImageFont.load_default()
        font_radar = ImageFont.load_default()
        font_slogan = ImageFont.load_default()
        font_disclaimer = ImageFont.load_default()
        font_copyright = ImageFont.load_default()
        font_qr_label = ImageFont.load_default()

    # ----------------------------------
    # 3. 头部设计
    # ----------------------------------
    draw.rectangle([(0, 0), (width, 24)], fill="#FF4B4B")

    draw.text((40, 65), "赛博内经：中医学体质-MBTI评估报告", font=font_title_main, fill="#333333")
    draw.text((40, 125), "Cyber NJ: TCM & MBTI Analysis System", font=font_subtitle, fill="#999999")

    draw.line([(40, 165), (760, 165)], fill="#EEEEEE", width=2)

    # ----------------------------------
    # 4. 核心数据卡片
    # ----------------------------------
    card_y_start = 200
    card_height = 160

    # 左卡片
    draw.rounded_rectangle([(40, card_y_start), (380, card_y_start + card_height)], radius=15, fill="#FFF5F5",
                           outline="#FFDCDC", width=2)
    draw.text((70, card_y_start + 25), "主导体质", font=font_card_label, fill="#888888")
    text_w = draw.textlength(main_diagnosis, font=font_card_val)
    draw.text((210 - text_w / 2, card_y_start + 65), main_diagnosis, font=font_card_val, fill="#FF4B4B")

    # 右卡片
    draw.rounded_rectangle([(420, card_y_start), (760, card_y_start + card_height)], radius=15, fill="#F0F9FF",
                           outline="#D0EFFF", width=2)
    draw.text((450, card_y_start + 25), "MBTI 人格", font=font_card_label, fill="#888888")
    text_w = draw.textlength(mbti, font=font_card_val)
    draw.text((590 - text_w / 2, card_y_start + 65), mbti, font=font_card_val, fill="#0099CC")

    # ----------------------------------
    # 5. 可视化区域
    # ----------------------------------
    viz_y_start = 400

    # >>> 左侧：MBTI 图片 <<<
    mbti_img_path = f"assets/mbti/{mbti}.png"
    img_box_size = 360

    if os.path.exists(mbti_img_path):
        try:
            mbti_img = Image.open(mbti_img_path).convert("RGBA")
            mbti_img.thumbnail((img_box_size, 320))
            # 居中计算
            paste_x = 40 + (360 - mbti_img.width) // 2
            paste_y = viz_y_start + (320 - mbti_img.height) // 2
            img.paste(mbti_img, (paste_x, paste_y), mbti_img)
        except:
            pass
    else:
        draw.rounded_rectangle([(60, viz_y_start + 20), (340, viz_y_start + 300)], radius=10, outline="#F0F0F0",
                               width=2)
        draw.text((150, viz_y_start + 140), "No Image", font=font_card_label, fill="#CCCCCC")

    # >>> 右侧：雷达图 (手绘版) <<<
    cx, cy = 600, viz_y_start + 160
    radius = 150
    # 背景圆
    for r_ratio in [0.25, 0.5, 0.75, 1.0]:
        r = radius * r_ratio
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline="#EEEEEE", width=2)

    # 轴线
    angles = [-90, -18, 54, 126, 198]
    labels = ['木', '火', '土', '金', '水']
    for i, angle in enumerate(angles):
        rad_angle = math.radians(angle)
        end_x = cx + radius * math.cos(rad_angle)
        end_y = cy + radius * math.sin(rad_angle)
        draw.line([(cx, cy), (end_x, end_y)], fill="#E0E0E0", width=2)

        label_dist = radius + 35
        lx = cx + label_dist * math.cos(rad_angle)
        ly = cy + label_dist * math.sin(rad_angle)
        txt = labels[i]
        tw = draw.textlength(txt, font=font_radar)
        draw.text((lx - tw / 2, ly - 15), txt, font=font_radar, fill="#555555")

    # 数据点连线
    data_points = []
    element_order = ['木', '火', '土', '金', '水']
    for i, ele in enumerate(element_order):
        val = elements.get(ele, 0)
        ratio = min(val / 100.0, 1.0)
        rad_angle = math.radians(angles[i])
        px = cx + radius * ratio * math.cos(rad_angle)
        py = cy + radius * ratio * math.sin(rad_angle)
        data_points.append((px, py))

    if len(data_points) == 5:
        draw.line(data_points + [data_points[0]], fill="#FF4B4B", width=5)
        for px, py in data_points:
            draw.ellipse([(px - 6, py - 6), (px + 6, py + 6)], fill="#FFFFFF", outline="#FF4B4B", width=3)

    draw.text((cx - 70, cy + 180), "五行能量雷达", font=font_card_label, fill="#AAAAAA")

    # ----------------------------------
    # 6. 完整体质得分列表
    # ----------------------------------
    list_y_start = 800
    draw.line([(40, list_y_start), (760, list_y_start)], fill="#EEEEEE", width=2)
    draw.text((40, list_y_start + 30), "完整体质得分 (Constitution Scores)", font=font_section, fill="#333333")

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    col_1_x, col_2_x = 40, 440
    row_height = 60
    table_start_y = list_y_start + 100

    for i, (name, val) in enumerate(sorted_scores):
        is_left = (i < 5)
        curr_x = col_1_x if is_left else col_2_x
        curr_y = table_start_y + (i if is_left else i - 5) * row_height

        name_color = "#000000" if i == 0 else "#666666"
        draw.text((curr_x, curr_y), name, font=font_list_name, fill=name_color)

        bar_x = curr_x + 110
        bar_y = curr_y + 10
        bar_max_w, bar_h = 160, 16

        # 背景
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_max_w, bar_y + bar_h)], radius=8, fill="#F2F2F2")

        # 前景
        fill_color = "#FF4B4B" if val >= 60 else "#BBBBBB"
        if i == 0: fill_color = "#FF4B4B"
        curr_w = int((val / 100) * bar_max_w)
        if curr_w < 8: curr_w = 8
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + curr_w, bar_y + bar_h)], radius=8, fill=fill_color)

        # 分数
        score_text = f"{val}"
        draw.text((bar_x + bar_max_w + 15, curr_y - 2), score_text, font=font_list_score, fill="#333333")
        draw.text((bar_x + bar_max_w + 15 + draw.textlength(score_text, font_list_score), curr_y + 4), "分",
                  font=ImageFont.truetype(valid_font, 20), fill="#999999")

    # ----------------------------------
    # 7. 底部互动区域 (真实二维码 + 标语)
    # ----------------------------------
    footer_start_y = 1260
    draw.line([(40, footer_start_y), (760, footer_start_y)], fill="#EEEEEE", width=2)

    # >>> 真实二维码生成 <<<
    qr_size = 140
    qr_x, qr_y = 50, footer_start_y + 35

    # 生成 QR 图片
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1,
    )
    qr.add_data(SHARE_URL)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_img.resize((qr_size, qr_size))

    # 粘贴二维码
    img.paste(qr_img, (qr_x, qr_y))
    # 绘制边框
    draw.rectangle([(qr_x - 2, qr_y - 2), (qr_x + qr_size + 2, qr_y + qr_size + 2)], outline="#DDDDDD", width=1)

    # 二维码下方文字
    qr_text = "长按识别体验"
    try:
        qw = draw.textlength(qr_text, font=font_qr_label)
    except:
        qw = 100
    draw.text((qr_x + (qr_size - qw) / 2, qr_y + qr_size + 10), qr_text, font=font_qr_label, fill="#888888")

    # >>> 右侧信息区 <<<
    text_left_x = 220

    # 分享标语
    slogan_y = footer_start_y + 40
    slogan_text = "快来测测你的\n中医学 MBTI 人格吧~"
    draw.text((text_left_x, slogan_y), slogan_text, font=font_slogan, fill="#FF4B4B", spacing=12)

    # 免责声明
    disclaimer_y = slogan_y + 100
    disclaimer_text = "声明：本测试结果未经医学论证，无临床诊断意义。\n如有身体不适，请前往正规医院就诊。"
    draw.text((text_left_x, disclaimer_y), disclaimer_text, font=font_disclaimer, fill="#999999", spacing=6)

    # 版权信息
    copyright_y = disclaimer_y + 60
    copyright_text = "Generated by Cyber NJ AI System  |  2026 Edition"
    draw.text((text_left_x, copyright_y), copyright_text, font=font_copyright, fill="#CCCCCC")

    return img