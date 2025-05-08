
import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from branca.colormap import linear
from folium.features import DivIcon
from branca.element import Template, MacroElement
from branca.colormap import StepColormap
from streamlit.components.v1 import html
import base64


# 🚗 붕붕 로고 + 타이틀
st.set_page_config(layout="centered")
st.markdown("<p style='text-align: left; font-size: 20px; color: gray;'>🚗 붕붕</p>", unsafe_allow_html=True)
st.title("😴 졸음운전 차량별 조회 시스템")

# ✅ 데이터 불러오기
df = pd.read_csv("drowsy_눈감은시간추가.csv")
gdf = gpd.read_file("sleep_data.geojson")
df["drowsy time"] = pd.to_datetime(df["drowsy time"])
df["지역"] = df["address"].str.extract(r"(.*?[도|시])")

# ✅ 전역 설정 - 사이드바
st.sidebar.markdown("⚙️ 전역 설정")

# 날짜 범위 선택
min_date = df["drowsy time"].min().date()
max_date = df["drowsy time"].max().date()
date_range = st.sidebar.date_input("📅 분석 날짜 범위", [min_date, max_date])

# 지역 필터
unique_regions = ["전체"] + sorted(df["지역"].dropna().unique().tolist())
selected_region = st.sidebar.selectbox("🗺️ 지역 필터", unique_regions)

# ✅ 필터 적용
df_filtered = df[(df["drowsy time"].dt.date >= date_range[0]) & (df["drowsy time"].dt.date <= date_range[1])]
if selected_region != "전체":
    df_filtered = df_filtered[df_filtered["지역"] == selected_region]

# ✅ 탭
tab1, tab2 = st.tabs(["📊 졸음운전 패턴 분석", "🚗 차량번호별 조회"])

with tab1:
    st.subheader("⏰ 사용자 평균별 시간대별 졸음운전 차트")

    df["시간대"] = pd.to_datetime(df["drowsy time"]).dt.hour
    df_chart = df.groupby("시간대")["user_id"].count().reset_index()
    df_chart = df_chart.rename(columns={"user_id": "졸음운전 건수"})

    max_count = df_chart["졸음운전 건수"].max()
    df_chart["color"] = df_chart["졸음운전 건수"].apply(lambda x: "red" if x == max_count else "lightskyblue")

    fig = px.bar(df_chart, x="시간대", y="졸음운전 건수", color="color",
                 color_discrete_map="identity", template="plotly_white")
    st.markdown("<p style='text-align:center;'>🚨 시간대별 졸음운전 발생 건수</p>", unsafe_allow_html=True)


    fig.update_layout(
        xaxis_title="시간대",
        yaxis_title="발생 건수",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)


    st.subheader("📍 졸음운전 발생 위치")
    if "건수" not in gdf.columns:
        gdf["건수"] = df_filtered.groupby("address").size().reindex(gdf["address"]).fillna(0).astype(int).values

    map1 = folium.Map(location=[37.4, 127.0], zoom_start=10, tiles="CartoDB positron")
    # 🔴 색상 범위 기반 컬러맵 생성
    # ✅ 색상 단계별 수동 컬러맵 정의
    colormap = StepColormap(
        colors=["#fee5d9", "#fcae91", "#fb6a4a", "#cb181d"],
        index=[0, 5, 10, 15, 20],  # 색상 구간 기준
        vmin=0, vmax=20
    )
    colormap.caption = ""  # 👉 숫자 눈금 제거
    colormap.add_to(map1)  # 🎯 이건 꼭 있어야 색상 반영됨!

    # ✅ 마커 추가
    for idx, row in gdf.iterrows():
        if row.geometry is not None and row.geometry.geom_type == "Point":
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=max(7, min(row["건수"] / 5, 10)),
                color="black", weight=1.5,
                fill=True, fill_color=colormap(row["건수"]),
                fill_opacity=0.9,
                tooltip=folium.Tooltip(f"{row['address']}<br>건수: {row['건수']}건")
            ).add_to(map1)

    # ✅ 이모지 범례 (우측 하단 고정)
    legend_html = """
    {% macro html(this, kwargs) %}
    <div style="
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index:9999;
        background-color: white;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 0 8px rgba(0,0,0,0.3);
        font-size: 14px;
    ">
        <b>● 색상 범례</b><br>
        <i style="background:#fee5d9;width:20px;height:10px;display:inline-block;"></i> 적음<br>
        <i style="background:#fcae91;width:20px;height:10px;display:inline-block;"></i> 보통<br>
        <i style="background:#fb6a4a;width:20px;height:10px;display:inline-block;"></i> 많음<br>
        <i style="background:#cb181d;width:20px;height:10px;display:inline-block;"></i> 매우 많음
    </div>
    {% endmacro %}
    """
    legend = MacroElement()
    legend._template = Template(legend_html)
    map1.get_root().add_child(legend)

    # ✅ Streamlit에 표시
    st_folium(map1, width=700, height=550, returned_objects=[])


with tab2:
    st.subheader("🔍 차량별 졸음운전 기록 조회")
    vehicle_number = st.text_input("🚗 조회할 차량번호(4자리) 입력:")

    if vehicle_number:
        if vehicle_number.isdigit() and len(vehicle_number) == 4:
            vehicle_number = int(vehicle_number)
            vehicle_data = df_filtered[df_filtered["user_id"] == vehicle_number].copy()

            if not vehicle_data.empty:
                st.success(f"✅ 차량번호 {str(vehicle_number).zfill(4)}의 졸음운전 기록 {len(vehicle_data)}건을 찾았습니다!")
                
                with st.expander("📋 졸음운전 기록 목록", expanded=False):
                    sorted_df = vehicle_data.sort_values("drowsy time", ascending=False).reset_index(drop=True)
                    sorted_df["번호"] = range(1, len(sorted_df) + 1)

                    # 컬럼명 변경
                    sorted_df.rename(columns={"address": "도로명", "drowsy time": "졸음 시간"}, inplace=True)

                    # 번호 컬럼을 가장 앞으로 배치
                    display_df = sorted_df[["번호", "도로명", "졸음 시간"]]

                    # ✅ 인덱스 숨기기
                    st.dataframe(display_df, hide_index=True)





                # 분석 기간 선택
                st.markdown("### 📅 분석 기간 선택")
                period = st.radio("", ["1일", "1주", "1개월"], horizontal=True, label_visibility="collapsed")
                period_days = {"1일": 1, "1주": 7, "1개월": 30}
                selected_days = period_days[period]

                # 필터링
                end_date = vehicle_data["drowsy time"].max()
                filtered = vehicle_data[
                    (vehicle_data["drowsy time"] >= end_date - pd.Timedelta(days=selected_days))
                ]

                # 🔄 NaN 제외한 데이터로 분석 통일
                # NaN 제외 + 날짜 포함된 컬럼만 따로 선택
                # 🔄 NaN 제외한 데이터로 분석 통일
                filtered_valid = filtered[filtered["eye_closed_time"].notna()].copy()
                filtered_valid["drowsy_time_str"] = filtered_valid["drowsy time"].dt.strftime("%Y-%m-%d %H:%M:%S")

                if not filtered.empty:
                    st.markdown(f"#### 🚦 {period} 운전 중 눈 감은 시간")

                    # 히스토그램
                    fig = px.histogram(
                        filtered_valid,
                        x="eye_closed_time",
                        histfunc="count",
                        nbins=20,
                        labels={"eye_closed_time": "눈 감은 시간 (초)", "count": "횟수"},
                        color_discrete_sequence=["#007acc"],
                        text_auto=True
                    )

                    # ✅ customdata에 날짜 추가
                    fig.update_traces(
                        xbins=dict(start=0, end=4, size=0.2),
                        customdata=filtered_valid[["drowsy_time_str"]].to_numpy(),
                        hovertemplate=(
                            "눈 감은 시간: %{x}초<br>"
                            "횟수: %{y}회<br>"
                            "발생 시각: %{customdata[0]}"
                        )
                    )

                    st.markdown(f"<p style='text-align:center;'> {period} (졸음 운전 마지막날 기준)</p>", unsafe_allow_html=True)

                    fig.update_layout(
                        xaxis=dict(title="눈 감은 시간 (초)", tick0=0, dtick=0.5, range=[0, 4]),
                        yaxis=dict(title="횟수", tick0=0, dtick=1, range=[0, 7]),
                    )


                    st.plotly_chart(fig, use_container_width=True)


                    # ⚠ 경고/위험 텍스트
                    warn_count = ((filtered["eye_closed_time"] > 2) & (filtered["eye_closed_time"] < 3)).sum()
                    danger_count = (filtered["eye_closed_time"] >= 3).sum()


                    # 카드 스타일 경고/위험 표시
                    # 이미지 불러오기
                    # from PIL import Image

                    # warning_img = Image.open("001.png")  # 경고 이미지
                    # danger_img = Image.open("002.png")   # 위험 이미지
                    warning_img = "001.png"
                    danger_img = "002.png"


                    # 📌 가운데 정렬 + 이미지만 살짝 오른쪽 이동
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.markdown(
                            f"""
                            <div style='text-align: center; margin-top: 50px; margin-bottom: 60px;'>
                                <img src='data:image/png;base64,{base64.b64encode(open(warning_img, "rb").read()).decode()}' width='130' style='margin-left: 5px;'/><br>
                                <div style='font-size: 15px; font-weight: bold; color: #333;'>졸음 경고 횟수</div>
                                <div style='font-size: 26px; color: orange; font-weight: bold;'>{warn_count}회</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    with col2:
                        st.markdown(
                            f"""
                            <div style='text-align: center; margin-top: 50px; margin-bottom: 60px;'>
                                <img src='data:image/png;base64,{base64.b64encode(open(danger_img, "rb").read()).decode()}' width='130' style='margin-left: 5px;'/><br>
                                <div style='font-size: 15px; font-weight: bold; color: #333;'>졸음 위험 횟수</div>
                                <div style='font-size: 26px; color: red; font-weight: bold;'>{danger_count}회</div>
                            """,
                            unsafe_allow_html=True
                        
                        )



                else:
                    st.info(f"{period} 내 졸음운전 데이터가 없습니다.")

                # 지도
                st.markdown(
                    "<h3 style='font-size:22px;'>🗺️ 졸음운전 발생 위치</h3>",
                    unsafe_allow_html=True
                )

                address_time_map = vehicle_data.set_index("address")["drowsy time"].to_dict()
                m = folium.Map(location=[37.5665, 126.9780], zoom_start=10, tiles="CartoDB positron")
                for _, row in gdf.iterrows():
                    geom = row.geometry  # geometry를 먼저 변수로 저장
                    if (
                        row.get("address") in address_time_map and 
                        geom is not None and 
                        geom.geom_type == "Point"
                    ):
                        drowsy_str = pd.to_datetime(address_time_map[row["address"]]).strftime("%Y-%m-%d (%H시)")
                        popup_html = f"""
                        <div style="font-size:13px; width:200px; white-space: normal;">
                        <b>도로명:</b> {row['address']}<br>
                        <b>발생시간:</b> {drowsy_str}
                        </div>
                        """
                        folium.Marker(
                            location=[row.geometry.y, row.geometry.x],
                            popup=folium.Popup(popup_html, max_width=250),
                            icon=folium.Icon(color="blue", icon="car", prefix="fa")
                        ).add_to(m)

                st_folium(m, width=700, height=500, returned_objects=[])

            else:
                st.warning("😥 해당 차량번호의 졸음운전 기록이 없습니다.")
        else:
            st.error("🚨 차량번호는 반드시 **4자리 숫자**로 입력해주세요 (예: 0101, 0505).")
    else:
        st.info("👆 차량번호를 입력하고 Enter를 눌러보세요!")
