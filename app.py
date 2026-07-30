import streamlit as st
import pandas as pd
import math
import subprocess
import sys
import os
import tempfile
import json

st.set_page_config(
    page_title="Sekhar Smart Attendance",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --bg: #07111f;
        --card: rgba(15, 32, 54, 0.90);
        --primary: #38bdf8;
        --secondary: #22d3ee;
        --accent: #a78bfa;
        --text: #f8fafc;
        --muted: #b6c2d1;
        --border: rgba(148, 163, 184, 0.22);
    }

    .stApp {
        background:
            radial-gradient(circle at 15% 10%, rgba(56,189,248,.16), transparent 28%),
            radial-gradient(circle at 85% 15%, rgba(167,139,250,.14), transparent 28%),
            linear-gradient(135deg, #06101d 0%, #0a1728 50%, #101c31 100%);
        color: var(--text);
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container { max-width: 1220px; padding-top: 1.4rem; padding-bottom: 3rem; }

    .hero {
        position: relative;
        overflow: hidden;
        padding: 2.2rem 2rem;
        margin-bottom: 1.4rem;
        border: 1px solid var(--border);
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(10,29,50,.97), rgba(20,46,76,.86));
        box-shadow: 0 24px 70px rgba(0,0,0,.28);
    }

    .hero::after {
        content: "";
        position: absolute;
        width: 260px;
        height: 260px;
        right: -80px;
        top: -120px;
        border-radius: 50%;
        background: rgba(56,189,248,.18);
    }

    .badge {
        display: inline-block;
        padding: .4rem .8rem;
        margin-bottom: .9rem;
        border: 1px solid rgba(56,189,248,.35);
        border-radius: 999px;
        background: rgba(56,189,248,.08);
        color: #7dd3fc;
        font-size: .8rem;
        font-weight: 800;
        letter-spacing: .08em;
        text-transform: uppercase;
    }

    .hero h1 {
        margin: 0;
        color: var(--text);
        font-size: clamp(2rem, 5vw, 4rem);
        line-height: 1.05;
        letter-spacing: -.045em;
    }

    .gradient-text {
        background: linear-gradient(90deg, #38bdf8, #22d3ee, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero p {
        max-width: 780px;
        margin: 1rem 0 0;
        color: var(--muted);
        font-size: 1.02rem;
        line-height: 1.75;
    }

    div[data-testid="stMetric"] {
        padding: 1rem 1.1rem;
        border: 1px solid var(--border);
        border-radius: 20px;
        background: linear-gradient(145deg, rgba(17,38,64,.94), rgba(12,27,47,.92));
        box-shadow: 0 14px 30px rgba(0,0,0,.18);
    }

    div[data-testid="stMetricLabel"] { color: var(--muted); }
    div[data-testid="stMetricValue"] { color: var(--text); }

    .stButton > button, .stDownloadButton > button {
        min-height: 3rem;
        border: 0;
        border-radius: 14px;
        background: linear-gradient(90deg, #0284c7, #06b6d4);
        color: white;
        font-weight: 800;
        box-shadow: 0 10px 25px rgba(6,182,212,.2);
    }

    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-1px);
        color: white;
        box-shadow: 0 14px 30px rgba(6,182,212,.3);
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="base-input"] > div {
        border-radius: 13px !important;
        border-color: var(--border) !important;
        background: rgba(8,22,39,.92) !important;
    }

    div[data-testid="stDataFrame"] {
        overflow: hidden;
        border: 1px solid var(--border);
        border-radius: 18px;
    }

    .footer-card {
        margin-top: 2rem;
        padding: 1.35rem;
        text-align: center;
        border: 1px solid var(--border);
        border-radius: 22px;
        background: rgba(9,24,42,.84);
        color: var(--muted);
    }

    .footer-card strong { color: var(--text); }
    .footer-card a { color: #67e8f9; font-weight: 700; text-decoration: none; }

    @media (max-width: 700px) {
        .block-container { padding-left: .8rem; padding-right: .8rem; }
        .hero { padding: 1.6rem 1.2rem; border-radius: 22px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def create_scraper_script():
    return r'''
import asyncio
import sys
import json

from playwright.async_api import async_playwright


async def scrape_attendance_async(roll, password):
    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security'
                ]
            )
            page = await browser.new_page()

            await page.goto("http://mitsims.in/", wait_until="load", timeout=30000)
            await page.wait_for_timeout(2000)
            await page.click("a#studentLink")
            await page.wait_for_timeout(3000)
            await page.wait_for_selector("#stuLogin input.login_box", timeout=15000)

            inputs = page.locator("#stuLogin input.login_box")
            await inputs.nth(0).fill(roll)
            await inputs.nth(1).fill(password)
            await page.click("#stuLogin button[type='submit']")

            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass

            await page.wait_for_timeout(8000)
            page_text = await page.inner_text("body")

            if "invalid" in page_text.lower() or "incorrect" in page_text.lower():
                return {"error": "Invalid credentials", "success": False}

            attendance_data = await page.evaluate("""
                () => {
                    const text = document.body.innerText;
                    const lines = text.split("\\n").map(line => line.trim()).filter(Boolean);

                    let startIndex = -1;
                    for (let i = 1; i < lines.length - 1; i++) {
                        if (
                            lines[i] === "CLASSES ATTENDED" &&
                            lines[i - 1] === "SUBJECT CODE" &&
                            lines[i + 1] === "TOTAL CONDUCTED"
                        ) {
                            startIndex = i + 3;
                            break;
                        }
                    }

                    if (startIndex === -1) return [];

                    const data = [];
                    for (let i = startIndex; i < lines.length; i += 5) {
                        const sno = lines[i];
                        const subject = lines[i + 1];
                        const attended = lines[i + 2];
                        const conducted = lines[i + 3];
                        const percentage = lines[i + 4];

                        if (!sno || !subject || !attended || !conducted || !percentage) break;
                        if (sno.includes("Note") || subject.includes("Note") || sno.includes("@") || subject.includes("@")) break;

                        if (
                            /^\\d+$/.test(sno) &&
                            /^\\d+$/.test(attended) &&
                            /^\\d+$/.test(conducted) &&
                            /^\\d+\\.?\\d*$/.test(percentage)
                        ) {
                            data.push({
                                s_no: sno,
                                subject,
                                attended,
                                conducted,
                                percentage: percentage + "%"
                            });
                        }
                    }
                    return data;
                }
            """)

            if not attendance_data:
                return {"error": "No attendance data found. The portal layout may have changed.", "success": False}

            return {"data": attendance_data, "success": True}

        except Exception as error:
            return {"error": str(error), "success": False}
        finally:
            if browser:
                await browser.close()


if __name__ == "__main__":
    payload = json.loads(sys.stdin.read())
    result = asyncio.run(scrape_attendance_async(payload["roll"], payload["password"]))
    print(json.dumps(result))
'''


def scrape_attendance(roll, password):
    script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as file:
            file.write(create_scraper_script())
            script_path = file.name

        env = os.environ.copy()
        browser = await p.chromium.launch(
    headless=True,
    executable_path="/usr/bin/chromium",
    args=[
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu"
    ]
)

        proc = subprocess.run(
            [sys.executable, script_path],
            input=json.dumps({"roll": roll, "password": password}),
            capture_output=True,
            text=True,
            timeout=120,
            env=env
        )

        if proc.returncode != 0:
            error_msg = proc.stderr.strip() if proc.stderr else "Unknown scraper error"
            raise RuntimeError(error_msg[:500])

        try:
            result = json.loads(proc.stdout.strip())
        except json.JSONDecodeError as exc:
            raise RuntimeError("Could not parse the scraper response") from exc

        if not result.get("success", False):
            raise RuntimeError(result.get("error", "Unknown error"))

        return result.get("data", [])

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Timeout: scraping took too long") from exc
    finally:
        if script_path and os.path.exists(script_path):
            os.unlink(script_path)


def calculate_classes_needed(attended, conducted, target_percentage):
    if target_percentage <= 0 or target_percentage > 100:
        return "Invalid"
    if conducted <= 0:
        return 0

    current_percentage = (attended / conducted) * 100
    if current_percentage >= target_percentage:
        return 0
    if target_percentage >= 100:
        return float("inf")

    numerator = target_percentage * conducted - 100 * attended
    denominator = 100 - target_percentage
    return max(0, math.ceil(numerator / denominator))


def calculate_classes_can_skip(attended, conducted, min_percentage):
    if min_percentage < 0 or min_percentage > 100:
        return "Invalid"
    if conducted <= 0:
        return 0

    current_percentage = (attended / conducted) * 100
    if current_percentage < min_percentage:
        return 0
    if min_percentage <= 0:
        return float("inf")

    numerator = 100 * attended - min_percentage * conducted
    return max(0, math.floor(numerator / min_percentage))


if "attendance_data" not in st.session_state:
    st.session_state.attendance_data = None
if "last_roll" not in st.session_state:
    st.session_state.last_roll = ""
if "show_overall_calc" not in st.session_state:
    st.session_state.show_overall_calc = False

st.markdown(
    """
    <section class="hero">
        <div class="badge">⚡ Smart campus utility</div>
        <h1>Sekhar <span class="gradient-text">Smart Attendance</span></h1>
        <p>
            A modern attendance dashboard created by <strong>Chandra Sekhar</strong>.
            View MITS IMS attendance, compare subjects and plan future classes
            from one clean, mobile-friendly dashboard.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)

st.warning(
    "Privacy notice: This unofficial app logs into the MITS IMS portal only to fetch attendance. "
    "Do not use it unless you trust the deployment owner. The portal currently uses HTTP rather than HTTPS."
)

with st.form("attendance_form"):
    col1, col2 = st.columns(2)
    with col1:
        roll = st.text_input("Roll Number", value=st.session_state.last_roll, placeholder="Enter your roll number")
    with col2:
        password = st.text_input("Password", type="password", placeholder="Enter your password")
    submit_button = st.form_submit_button("Get Attendance", use_container_width=True)

if submit_button:
    if not roll or not password:
        st.error("Please enter both roll number and password")
    else:
        st.session_state.last_roll = roll
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🔍 Initializing browser...")
            progress_bar.progress(20)
            status_text.text("🔐 Logging in...")
            progress_bar.progress(45)
            status_text.text("📊 Scraping attendance...")
            progress_bar.progress(75)

            attendance_data = scrape_attendance(roll, password)

            progress_bar.progress(100)
            progress_bar.empty()
            status_text.empty()

            if attendance_data:
                st.session_state.attendance_data = attendance_data
                st.success(f"✅ Found {len(attendance_data)} subjects!")
            else:
                st.warning("No attendance data found")
        except Exception as exc:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Error: {exc}")

if st.session_state.attendance_data:
    df = pd.DataFrame(st.session_state.attendance_data)
    df.columns = ["S.No", "Subject", "Attended", "Conducted", "Percentage"]
    df["Attended"] = pd.to_numeric(df["Attended"], errors="coerce").fillna(0).astype(int)
    df["Conducted"] = pd.to_numeric(df["Conducted"], errors="coerce").fillna(0).astype(int)
    df["Percentage_Float"] = pd.to_numeric(df["Percentage"].str.rstrip("%"), errors="coerce").fillna(0)
    df["Calculated_Percentage"] = (
        df["Attended"] / df["Conducted"].replace(0, pd.NA) * 100
    ).fillna(0).astype(float)

    total_attended = int(df["Attended"].sum())
    total_conducted = int(df["Conducted"].sum())
    overall_attendance = total_attended / total_conducted * 100 if total_conducted else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Overall Attendance", f"{overall_attendance:.1f}%")
    col2.metric("Total Attended", total_attended)
    col3.metric("Total Conducted", total_conducted)

    with st.expander("📌 Percentage calculation details"):
        st.write("Overall attendance is weighted using total attended and total conducted classes.")
        st.caption(f"Weighted overall = ({total_attended}/{total_conducted}) × 100 = {overall_attendance:.2f}%")
        st.caption(f"Unweighted subject mean = {df['Percentage_Float'].mean():.2f}%")

    st.subheader("📊 Attendance Details")
    st.subheader("🎛️ Interactive Filters")

    fc1, fc2, fc3 = st.columns([1, 2, 1])
    with fc1:
        threshold = st.slider("Highlight below (%)", 0, 100, 75)
    with fc2:
        selected_subjects = st.multiselect(
            "Subjects",
            options=df["Subject"].tolist(),
            default=df["Subject"].tolist()
        )
    with fc3:
        sort_by = st.selectbox("Sort by", ["Subject", "Percentage", "Attended", "Conducted"])

    filtered_df = df[df["Subject"].isin(selected_subjects)].copy()
    sort_col = "Calculated_Percentage" if sort_by == "Percentage" else sort_by
    filtered_df = filtered_df.sort_values(sort_col, ascending=(sort_by == "Subject"))

    def color_percentage(value):
        try:
            percentage = float(str(value).rstrip("%"))
        except ValueError:
            return ""
        if percentage >= 75:
            return "background-color: #d4edda; color: #155724"
        if percentage >= 60:
            return "background-color: #fff3cd; color: #856404"
        return "background-color: #f8d7da; color: #721c24"

    display_df = filtered_df[["S.No", "Subject", "Attended", "Conducted", "Percentage"]].copy()
    st.dataframe(
        display_df.style.map(color_percentage, subset=["Percentage"]),
        use_container_width=True,
        hide_index=True
    )

    st.write("#### Subject-wise attendance")
    progress_cols = st.columns(2)
    for index, row in filtered_df.reset_index(drop=True).iterrows():
        with progress_cols[index % 2]:
            pct = float(row["Calculated_Percentage"])
            status = "✅" if pct >= threshold else "⚠️"
            st.write(f"{status} **{row['Subject']}** — {pct:.1f}%")
            st.progress(min(max(pct / 100, 0), 1))

    st.write("#### Attendance comparison chart")
    st.bar_chart(filtered_df[["Subject", "Calculated_Percentage"]].set_index("Subject"))

    st.subheader("🎯 Attendance Calculator")
    if st.button("🔢 Open Calculator", use_container_width=True, type="primary"):
        st.session_state.show_overall_calc = not st.session_state.show_overall_calc

    if st.session_state.show_overall_calc:
        st.markdown("---")
        calc_type = st.radio("Calculate:", ("📈 Classes to Attend", "📉 Classes to Skip"), horizontal=True)
        desired_percentage = st.number_input("Desired Attendance Percentage (%)", 0, 100, 75, 1)

        if st.button("Calculate", use_container_width=True):
            current_overall = total_attended / total_conducted * 100 if total_conducted else 0

            if calc_type == "📈 Classes to Attend":
                classes_needed = calculate_classes_needed(total_attended, total_conducted, desired_percentage)
                if current_overall >= desired_percentage:
                    st.success(f"You already have {current_overall:.2f}% attendance.")
                elif classes_needed == float("inf"):
                    st.warning(f"It is impossible to reach {desired_percentage}% unless no class has ever been missed.")
                else:
                    future_attended = total_attended + classes_needed
                    future_conducted = total_conducted + classes_needed
                    future_overall = future_attended / future_conducted * 100
                    st.success(f"You need to attend {int(classes_needed)} more classes.")
                    st.info(f"Current: {current_overall:.2f}% → After: {future_overall:.2f}%")
            else:
                classes_can_skip = calculate_classes_can_skip(total_attended, total_conducted, desired_percentage)
                if current_overall < desired_percentage:
                    st.error(f"Your current attendance is {current_overall:.2f}%, so you cannot skip classes.")
                elif classes_can_skip == float("inf"):
                    st.success("Theoretical result: unlimited classes can be skipped when the minimum is 0%.")
                elif classes_can_skip > 0:
                    future_conducted = total_conducted + classes_can_skip
                    future_overall = total_attended / future_conducted * 100
                    st.success(f"You can skip {int(classes_can_skip)} classes.")
                    st.info(f"Current: {current_overall:.2f}% → After: {future_overall:.2f}%")
                else:
                    st.warning(f"You cannot skip any classes while maintaining {desired_percentage}%.")

    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download CSV",
        csv,
        f"attendance_{st.session_state.last_roll}.csv",
        "text/csv",
        use_container_width=True
    )

with st.expander("ℹ️ How to use"):
    st.markdown(
        """
1. Enter your MITS IMS roll number and password.
2. Wait while the app opens the portal and fetches attendance.
3. Review subject-wise and overall attendance.
4. Use the calculator to plan future attendance.
5. Download the filtered table as CSV.

**Calculator formulas**

- To attend: `x = (T × C - 100 × A) / (100 - T)`
- To skip: `x = (100 × A - T × C) / T`

Where `A` is attended classes, `C` is conducted classes, and `T` is the target percentage.
        """
    )

st.markdown(
    """
    <div class="footer-card">
        <strong>Sekhar Smart Attendance</strong><br>
        Designed and developed by <strong>Chandra Sekhar</strong><br><br>
        <a href="https://www.linkedin.com/in/chandra-sekhar-talari-38040832b"
           target="_blank" rel="noopener noreferrer">LinkedIn</a>
        &nbsp; • &nbsp;
        <a href="https://www.instagram.com/urs_sekhar18"
           target="_blank" rel="noopener noreferrer">Instagram</a>
        <br><br>© 2026 Chandra Sekhar
    </div>
    """,
    unsafe_allow_html=True,
)
