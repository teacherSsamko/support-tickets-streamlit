import datetime
import requests
import random

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# Show app title and description.
st.set_page_config(page_title="Support tickets", page_icon="🎫")
st.title("🎫 Support tickets")
st.write(
    """
    This app shows how you can build an internal tool in Streamlit. Here, we are 
    implementing a support ticket workflow. The user can create a ticket, edit 
    existing tickets, and view some statistics.
    """
)

# GitHub API 설정
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]  # GitHub 토큰을 Streamlit secrets에서 가져옴
REPO_OWNER = "teacherSsamko"
REPO_NAME = "tech-blog"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"

# GitHub API 헤더 설정
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


# GitHub 이슈를 가져오는 함수
def fetch_github_issues():
    response = requests.get(GITHUB_API_URL, headers=headers)
    if response.status_code == 200:
        issues = response.json()
        data = {
            "ID": [f"ISSUE-{issue['number']}" for issue in issues],
            "Issue": [issue["title"] for issue in issues],
            "Status": [
                "Closed" if issue["state"] == "closed" else "Open" for issue in issues
            ],
            "Label": [
                issue["labels"][0]["name"] if issue["labels"] else "enhancement"
                for issue in issues
            ],
            "Date Submitted": [issue["created_at"].split("T")[0] for issue in issues],
        }
        return pd.DataFrame(data)
    return pd.DataFrame()


# 세션 상태 초기화
if "df" not in st.session_state:
    st.session_state.df = fetch_github_issues()

# Show a section to add a new ticket.
st.header("Add a ticket")

# We're adding tickets via an `st.form` and some input widgets. If widgets are used
# in a form, the app will only rerun once the submit button is pressed.
with st.form("add_ticket_form"):
    issue = st.text_area("Describe the issue")
    label = st.selectbox("Label", ["bug", "credential", "feature", "enhancement"])
    submitted = st.form_submit_button("Submit")

if submitted:
    # GitHub에 새 이슈 생성
    new_issue_data = {"title": issue, "body": issue, "labels": [label]}
    response = requests.post(GITHUB_API_URL, headers=headers, json=new_issue_data)

    if response.status_code == 201:
        issue_data = response.json()
        df_new = pd.DataFrame(
            [
                {
                    "ID": f"ISSUE-{issue_data['number']}",
                    "Issue": issue_data["title"],
                    "Status": "Open",
                    "Label": label,
                    "Date Submitted": issue_data["created_at"].split("T")[0],
                }
            ]
        )
        st.write("이슈가 생성되었습니다! 이슈 상세:")
        st.dataframe(df_new, use_container_width=True, hide_index=True)
        st.session_state.df = pd.concat([df_new, st.session_state.df], axis=0)
    else:
        st.error("이슈 생성 중 오류가 발생했습니다.")

# Show section to view and edit existing tickets in a table.
st.header("Existing tickets")
st.write(f"Number of tickets: `{len(st.session_state.df)}`")

st.info(
    "You can edit the tickets by double clicking on a cell. Note how the plots below "
    "update automatically! You can also sort the table by clicking on the column headers.",
    icon="✍️",
)


# GitHub 이슈 상태 업데이트 함수
def update_github_issue(issue_number, state=None, title=None, labels=None):
    issue_number = int(issue_number.replace("ISSUE-", ""))
    update_url = f"{GITHUB_API_URL}/{issue_number}"
    update_data = {}

    if state:
        # GitHub는 'closed'와 'open' 상태만 지원
        update_data["state"] = "closed" if state == "Closed" else "open"
    if title:
        update_data["title"] = title
    if labels:
        update_data["labels"] = [labels]

    response = requests.patch(update_url, headers=headers, json=update_data)
    return response.status_code == 200


# 데이터프레임 변경 감지 및 GitHub 이슈 업데이트
if "previous_df" not in st.session_state:
    st.session_state.previous_df = st.session_state.df.copy()


# 변경사항 감지 및 업데이트 함수
def update_issues(edited_df):
    if len(edited_df) == len(st.session_state.previous_df):
        for i in range(len(edited_df)):
            current_row = edited_df.iloc[i]
            previous_row = st.session_state.previous_df.iloc[i]

            # 변경사항 확인
            if (
                current_row["Status"] != previous_row["Status"]
                or current_row["Issue"] != previous_row["Issue"]
                or current_row["Label"] != previous_row["Label"]
            ):

                # GitHub 이슈 업데이트
                success = update_github_issue(
                    current_row["ID"],
                    state=current_row["Status"],
                    title=current_row["Issue"],
                    labels=current_row["Label"],
                )

                if success:
                    st.success(f"이슈 {current_row['ID']}가 업데이트되었습니다.")
                else:
                    st.error(
                        f"이슈 {current_row['ID']} 업데이트 중 오류가 발생했습니다."
                    )
                    # 업데이트 실패 시 이전 상태로 복원
                    return st.session_state.previous_df

    # 성공적으로 업데이트된 경우 현재 상태 저장
    st.session_state.previous_df = edited_df.copy()
    return edited_df


# 데이터 에디터 표시 및 변경사항 처리
edited_df = st.data_editor(
    st.session_state.df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Status": st.column_config.SelectboxColumn(
            "Status",
            help="Ticket status",
            options=["Open", "In Progress", "Closed"],
            required=True,
        ),
        "Label": st.column_config.SelectboxColumn(
            "Label",
            help="Issue Label",
            options=["bug", "credential", "feature", "enhancement"],
            required=True,
        ),
    },
    disabled=["ID", "Date Submitted"],
    key="issue_editor",
)

# 변경사항 감지 및 업데이트
if st.session_state.get("issue_editor_changed", False):
    edited_df = update_issues(edited_df)
    st.session_state.df = edited_df

# 새로고침 버튼
if st.button("이슈 새로고침"):
    st.session_state.df = fetch_github_issues()
    st.session_state.previous_df = st.session_state.df.copy()
    st.rerun()

# Show some metrics and charts about the ticket.
st.header("Statistics")

# Show metrics side by side using `st.columns` and `st.metric`.
col1, col2, col3 = st.columns(3)
num_open_tickets = len(st.session_state.df[st.session_state.df.Status == "Open"])
col1.metric(label="Number of open tickets", value=num_open_tickets, delta=10)
col2.metric(label="First response time (hours)", value=5.2, delta=-1.5)
col3.metric(label="Average resolution time (hours)", value=16, delta=2)

# Show two Altair charts using `st.altair_chart`.
st.write("")
st.write("##### Ticket status per month")
status_plot = (
    alt.Chart(edited_df)
    .mark_bar()
    .encode(
        x="month(Date Submitted):O",
        y="count():Q",
        xOffset="Status:N",
        color="Status:N",
    )
    .configure_legend(
        orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5
    )
)
st.altair_chart(status_plot, use_container_width=True, theme="streamlit")

st.write("##### Current ticket labels")
label_plot = (
    alt.Chart(edited_df)
    .mark_arc()
    .encode(theta="count():Q", color="Label:N")
    .properties(height=300)
    .configure_legend(
        orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5
    )
)
st.altair_chart(label_plot, use_container_width=True, theme="streamlit")
