import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="小B学习中断服务任务台", layout="wide")

@st.cache_data
def load_data():
    return (pd.read_csv("data/students.csv"), pd.read_csv("data/learning_logs.csv"),
            pd.read_csv("data/rules.csv"), pd.read_csv("data/tasks.csv"),
            pd.read_csv("data/feedback.csv"))

students, logs, rules, tasks, feedback = load_data()

if "tasks" not in st.session_state:
    st.session_state.tasks = tasks.copy()

st.title("小B学习中断服务任务台（全链路枢纽 Demo)")
st.caption("Demo 数据为模拟生成，仅用于验证 S2B2C 全链路闭环与指标口径。")

page = st.sidebar.radio("页面", ["总览看板", "任务工作台", "复盘与机制闭环"])

if page == "总览看板":
    df = st.session_state.tasks
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("任务总数", len(df))
    c2.metric("待处理", len(df[df["status"] == "待处理"]))
    c3.metric("已关闭", len(df[df["status"] == "已关闭"]))
    closed = len(df[df["status"] == "已关闭"])
    recovered = len(df[(df["status"] == "已关闭") & (df["recovered_booking"] == 1)])
    rate = recovered / closed if closed else 0
    c4.metric("7日恢复约课率", f"{rate:.0%}")
    c5.metric("误承诺拦截数", int(df["miscommit_flag"].sum()))

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(df["status"].value_counts().reset_index(), names="status", values="count", hole=0.5, title="任务状态分布")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df["signal"].value_counts().reset_index(), x="signal", y="count", title="信号类型分布（预警来源）", color="signal")
        st.plotly_chart(fig, use_container_width=True)

elif page == "任务工作台":
    df = st.session_state.tasks
    st.subheader("任务列表")
    selected_label = st.selectbox("选择要处理的任务", (df["task_id"] + " | " + df["student_name"] + " | " + df["signal"] + " | " + df["status"]).tolist())
    selected_id = selected_label.split(" | ")[0]
    task = df[df["task_id"] == selected_id].iloc[0]

    st.divider()
    left, right = st.columns([2, 1])

    with left:
        st.markdown(f"### 正在处理：{task['task_id']} · {task['student_name']}")
        st.markdown("#### ① 全链路证据聚合")
        st.info(f"🔵 **S端AI学情 & 🟢 C端社群行为**\n\n{task['evidence']}")
        
        student_logs = logs[logs["student_id"] == task["student_id"]]
        fig = px.line(student_logs, x="date", y=["booked", "hours_consumed"], title="近14天约课与耗课轨迹", markers=True)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### ② AI 原因诊断与动作建议")
        st.write(f"**系统推测原因**：{task['reason_hypothesis']}")
        
        col_a, col_b = st.columns(2)
        if col_a.button("🤖 一键执行 AI 动作（发轻量任务/报告）"):
            st.success("已触发 C 端 AI 伴学，向家长推送轻量练习与周报。")
        if col_b.button("👤 呼叫真人协同（排课/社群老师）"):
            st.warning(f"已向【{task['collaborator']}】派发协同工单,SLA 计时开始。")

        st.markdown("#### ③ 跟进话术与合规拦截")
        script = st.text_area("输入将发送给家长的话术：")
        if script:
            hit = [w for w in ["随时退", "保证固定外教", "保证提分", "保证效果"] if w in script]
            if hit:
                st.error(f"❌ 触发合规红线！禁止向家长承诺：{', '.join(hit)}。已阻止发送。")
            else:
                st.success("✅ 话术合规，可以发送。")

    with right:
        st.markdown("### ④ 结果回填与机制结算")
        st.write(f"当前状态：**{task['status']}**")
        st.write(f"SLA 要求：**{task['sla_hours']} 小时**")
        
        with st.form("feedback_form"):
            recovered = st.selectbox("学员是否恢复约课？", ["否", "是"])
            escalated = st.selectbox("是否需升级主管？", ["否", "是"])
            submitted = st.form_submit_button("提交回填")

            if submitted:
                idx = st.session_state.tasks[st.session_state.tasks["task_id"] == selected_id].index[0]
                st.session_state.tasks.at[idx, "status"] = "已升级" if escalated == "是" else "已关闭"
                st.session_state.tasks.at[idx, "recovered_booking"] = 1 if recovered == "是" else 0
                if recovered == "是":
                    st.success("✅ 任务关闭！\n\n📈 **触发渠道机制**：该学员耗课里程碑推进，自动计提增量激励 **+0.8%** 至渠道账户。")
                    st.info("🔄 **数据回流**：本次跟进记录已同步回 S 端 AI,用于优化后续同类学员的诊断准确率。")
                else:
                    st.warning("任务已记录。已进入【流失风险】名单，等待后续 RPA+AI 进行二次唤醒。")

else:
    st.subheader("复盘与全链路机制闭环")
    st.write("这一部分用来向评委证明：小B在端上的动作,直接支撑了全链路的指标。")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(x=["学员A", "学员B", "学员C"], y=[[20,22,25],[6,7,8]], barmode="group", labels={"x":"学员", "value":"处理耗时(分钟)", "variable":"方式"}, title="小B处理中断任务耗时对比（模拟）")
        fig.for_each_trace(lambda t: t.update(name = "传统手工查数据" if t.name == "wide_variable_0" else "任务台一键聚合"))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        closed = len(st.session_state.tasks[st.session_state.tasks["status"] == "已关闭"])
        recovered = len(st.session_state.tasks[(st.session_state.tasks["status"] == "已关闭") & (st.session_state.tasks["recovered_booking"] == 1)])
        fig = px.funnel(x=[len(st.session_state.tasks), closed, recovered], y=["触发中断任务", "小B处理完毕", "恢复约课"], title="服务交付转化漏斗")
        st.plotly_chart(fig, use_container_width=True)
    st.info("💡 **全链路意义**：小B处理时间缩短 60%+，误承诺降为 0,耗课率的提升直接拉动渠道续费分成的增加,真正实现了‘交付计账’的机制闭环。")