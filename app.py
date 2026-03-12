import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Daily Liquidity Dashboard", layout="wide")

st.markdown("Upload an Excel file and analyze trends by date / time period.")

excel_file = pd.ExcelFile("Daily_Liquidity_Indicators.xlsx")
    sheet_names = excel_file.sheet_names

    selected_sheet = st.sidebar.selectbox("Select Sheet", sheet_names)

    df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)

    df.columns = [str(col).strip() for col in df.columns]

    first_col = df.columns[0]
    if first_col != "Date":
        df.rename(columns={first_col: "Date"}, inplace=True)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    is_monthly_volume_sheet = selected_sheet == "M-Bills Secondary Market Volume"

    # Dynamic title with latest available date
    latest_title_date = df["Date"].max()
    if is_monthly_volume_sheet:
        formatted_title_date = latest_title_date.strftime("%b %Y")
    else:
        day = latest_title_date.day
        if 11 <= day <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        formatted_title_date = f"{day}{suffix} {latest_title_date.strftime('%B %Y')}"

    st.title(f"Daily Liquidity Dashboard (As of {formatted_title_date})")

    for col in df.columns:
        if col != "Date":
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace(" ", "", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    numeric_columns = [
        col for col in df.columns
        if col != "Date" and pd.api.types.is_numeric_dtype(df[col])
    ]

    st.sidebar.header("Filters")

    filtered_df = df.copy()

    if not filtered_df.empty:
        if is_monthly_volume_sheet:
            month_df = filtered_df.copy()
            month_df["YearMonth"] = month_df["Date"].dt.to_period("M")
            available_periods = sorted(month_df["YearMonth"].unique())

            start_period_default = available_periods[0]
            end_period_default = available_periods[-1]

            month_names = {
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            }

            st.sidebar.markdown("**Select Start Month / Year**")
            col_m1, col_y1 = st.sidebar.columns(2)
            start_month = col_m1.selectbox(
                "Month",
                list(month_names.keys()),
                index=start_period_default.month - 1,
                format_func=lambda x: month_names[x],
                key="start_month"
            )
            start_year_options = sorted(list({p.year for p in available_periods}))
            start_year = col_y1.selectbox(
                "Year",
                start_year_options,
                index=start_year_options.index(start_period_default.year),
                key="start_year"
            )

            st.sidebar.markdown("**Select End Month / Year**")
            col_m2, col_y2 = st.sidebar.columns(2)
            end_month = col_m2.selectbox(
                "Month",
                list(month_names.keys()),
                index=end_period_default.month - 1,
                format_func=lambda x: month_names[x],
                key="end_month"
            )
            end_year = col_y2.selectbox(
                "Year",
                start_year_options,
                index=start_year_options.index(end_period_default.year),
                key="end_year"
            )

            start_period = pd.Period(year=start_year, month=start_month, freq="M")
            end_period = pd.Period(year=end_year, month=end_month, freq="M")

            if start_period > end_period:
                st.sidebar.error("Start month/year cannot be after end month/year.")
            else:
                filtered_df = filtered_df[
                    (filtered_df["Date"].dt.to_period("M") >= start_period) &
                    (filtered_df["Date"].dt.to_period("M") <= end_period)
                ]

        else:
            min_date = filtered_df["Date"].min().date()
            max_date = filtered_df["Date"].max().date()

            date_range = st.sidebar.date_input(
                "Select Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )

            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
                filtered_df = filtered_df[
                    (filtered_df["Date"].dt.date >= start_date) &
                    (filtered_df["Date"].dt.date <= end_date)
                ]

    st.sidebar.header("Reference Lines")
    vertical_line_date = pd.to_datetime("2026-02-28")
    show_vertical_line = st.sidebar.checkbox("Conflict Started", value=True)
    show_mean_line = st.sidebar.checkbox("Mean", value=True)

    st.sidebar.header("Chart Settings")
    chart_type = st.sidebar.selectbox(
        "Select Chart Type",
        ["Line Chart", "Scatter Plot"]
    )

    default_cols = numeric_columns[:3] if len(numeric_columns) >= 3 else numeric_columns
    selected_columns = st.sidebar.multiselect(
        "Select Column(s) to Plot / Analyze",
        numeric_columns,
        default=default_cols
    )

    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Charts", "Data Preview", "Analysis"])

    with tab1:
        st.subheader("KPI Cards")
        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Rows", f"{len(filtered_df):,}")
        c2.metric("Columns", len(filtered_df.columns))
        if not filtered_df.empty:
            if is_monthly_volume_sheet:
                c3.metric("Start Period", filtered_df["Date"].min().strftime("%b-%y"))
                c4.metric("End Period", filtered_df["Date"].max().strftime("%b-%y"))
            else:
                c3.metric("Start Date", str(filtered_df["Date"].min().date()))
                c4.metric("End Date", str(filtered_df["Date"].max().date()))
        else:
            c3.metric("Start", "-")
            c4.metric("End", "-")

        st.markdown("---")
        st.subheader("Available Metrics")
        st.write(numeric_columns)

    with tab2:
        st.subheader("Charts")

        if not numeric_columns:
            st.warning("No numeric columns found for charting.")
        elif filtered_df.empty:
            st.warning("No data available for the selected date range.")
        elif not selected_columns:
            st.warning("Please select at least one column from the sidebar.")
        else:
            color_sequence = [
                "#1f77b4",
                "#000000",
                "#2ca02c",
                "#9467bd",
                "#ff7f0e",
                "#17becf",
                "#8c564b",
                "#e377c2",
                "#7f7f7f",
                "#bcbd22"
            ]

            vertical_line_color = "black"
            mean_line_color = "darkgray"

            if selected_sheet == "M-Bills Yields":
                chart_df = filtered_df[["Date"] + selected_columns].dropna().sort_values("Date")

                long_df = chart_df.melt(
                    id_vars="Date",
                    value_vars=selected_columns,
                    var_name="Metric",
                    value_name="Yield %"
                )

                if chart_type == "Line Chart":
                    fig = px.line(
                        long_df,
                        x="Date",
                        y="Yield %",
                        color="Metric",
                        title="M-Bills Yields - Combined Graph",
                        color_discrete_sequence=color_sequence
                    )
                    fig.update_traces(line=dict(width=1.5))
                else:
                    fig = px.scatter(
                        long_df,
                        x="Date",
                        y="Yield %",
                        color="Metric",
                        title="M-Bills Yields - Combined Graph",
                        color_discrete_sequence=color_sequence
                    )

                y_min = long_df["Yield %"].min()
                y_max = long_df["Yield %"].max()

                if show_vertical_line:
                    fig.add_shape(
                        type="line",
                        x0=vertical_line_date,
                        x1=vertical_line_date,
                        y0=y_min,
                        y1=y_max,
                        line=dict(color=vertical_line_color, width=1, dash="dash")
                    )

                if show_mean_line:
                    mean_value = long_df["Yield %"].mean()
                    fig.add_hline(
                        y=mean_value,
                        line_width=1,
                        line_dash="dash",
                        line_color=mean_line_color
                    )
                    fig.add_annotation(
                        x=long_df["Date"].max(),
                        y=mean_value,
                        text=f"Mean: {mean_value:.2f}",
                        showarrow=False,
                        font=dict(color=mean_line_color),
                        xanchor="left",
                        yanchor="bottom"
                    )

                for metric in selected_columns:
                    metric_df = long_df[long_df["Metric"] == metric].dropna().sort_values("Date")
                    if not metric_df.empty:
                        last_row = metric_df.iloc[-1]
                        fig.add_annotation(
                            x=last_row["Date"],
                            y=last_row["Yield %"],
                            text=f"{last_row['Yield %']:.2f}",
                            showarrow=False,
                            font=dict(color="black"),
                            xanchor="left",
                            yanchor="middle"
                        )

                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Yield %"
                )

                st.plotly_chart(fig, use_container_width=True)

            else:
                for i, col in enumerate(selected_columns):
                    st.markdown(f"### {col}")

                    chart_df = filtered_df[["Date", col]].dropna().sort_values("Date")

                    if chart_df.empty:
                        continue

                    if chart_type == "Line Chart":
                        fig = px.line(
                            chart_df,
                            x="Date",
                            y=col,
                            title=f"{col} vs Date"
                        )
                        fig.update_traces(
                            line=dict(
                                color=color_sequence[i % len(color_sequence)],
                                width=1.5
                            )
                        )
                    else:
                        fig = px.scatter(
                            chart_df,
                            x="Date",
                            y=col,
                            title=f"{col} vs Date",
                            color_discrete_sequence=[color_sequence[i % len(color_sequence)]]
                        )

                    y_min = chart_df[col].min()
                    y_max = chart_df[col].max()

                    if show_vertical_line:
                        fig.add_shape(
                            type="line",
                            x0=vertical_line_date,
                            x1=vertical_line_date,
                            y0=y_min,
                            y1=y_max,
                            line=dict(color=vertical_line_color, width=1, dash="dash")
                        )

                    if show_mean_line:
                        mean_value = chart_df[col].mean()
                        fig.add_hline(
                            y=mean_value,
                            line_width=1,
                            line_dash="dash",
                            line_color=mean_line_color
                        )
                        fig.add_annotation(
                            x=chart_df["Date"].max(),
                            y=mean_value,
                            text=f"Mean: {mean_value:,.2f}",
                            showarrow=False,
                            font=dict(color=mean_line_color),
                            xanchor="left",
                            yanchor="bottom"
                        )

                    last_row = chart_df.iloc[-1]
                    fig.add_annotation(
                        x=last_row["Date"],
                        y=last_row[col],
                        text=f"{last_row[col]:,.2f}",
                        showarrow=False,
                        font=dict(color="black"),
                        xanchor="left",
                        yanchor="middle"
                    )

                    fig.update_layout(
                        xaxis_title="Date",
                        yaxis_title=col
                    )

                    st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("Data Preview")

        preview_df = filtered_df.copy()
        if is_monthly_volume_sheet:
            preview_df["Date"] = preview_df["Date"].dt.strftime("%b-%y")
        else:
            preview_df["Date"] = preview_df["Date"].dt.strftime("%Y-%m-%d")

        preview_df.index = range(1, len(preview_df) + 1)

        preview_format_dict = {col: "{:,.2f}" for col in preview_df.columns if col != "Date"}

        st.dataframe(
            preview_df.style.format(preview_format_dict),
            use_container_width=True
        )

    with tab4:
        st.subheader("Analysis")

        if filtered_df.empty:
            st.warning("No data available for analysis.")
        elif not selected_columns:
            st.warning("Please select at least one column from the sidebar for analysis.")
        else:
            analysis_rows = []

            if is_monthly_volume_sheet:
                for col in selected_columns:
                    full_series = filtered_df[["Date", col]].dropna().sort_values("Date")

                    if full_series.empty:
                        continue

                    start_value = full_series.iloc[0][col]
                    start_date = full_series.iloc[0]["Date"]
                    latest_value = full_series.iloc[-1][col]
                    latest_date = full_series.iloc[-1]["Date"]

                    selected_mean = full_series[col].mean()
                    selected_min = full_series[col].min()
                    selected_max = full_series[col].max()

                    range_abs_change = latest_value - start_value
                    range_pct_change = (range_abs_change / start_value) * 100 if start_value != 0 else None

                    latest_vs_mean_abs = latest_value - selected_mean
                    latest_vs_mean_pct = (latest_vs_mean_abs / selected_mean) * 100 if selected_mean != 0 else None

                    analysis_rows.append({
                        "Metric": col,
                        "Selected Range Start Date": start_date,
                        "Selected Range Start Value": start_value,
                        "Latest Date": latest_date,
                        "Latest": latest_value,
                        "Range Absolute Change": range_abs_change,
                        "Range % Change": range_pct_change,
                        "Selected Range Mean": selected_mean,
                        "Latest vs Mean Absolute": latest_vs_mean_abs,
                        "Latest vs Mean %": latest_vs_mean_pct,
                        "Selected Range Min": selected_min,
                        "Selected Range Max": selected_max
                    })

                analysis_df = pd.DataFrame(analysis_rows)

                st.subheader("Current Latest Level")
                for _, row in analysis_df.iterrows():
                    latest_text = f"{row['Latest']:,.2f}" if pd.notna(row["Latest"]) else "N/A"
                    latest_date_text = row["Latest Date"].strftime("%b-%y") if pd.notna(row["Latest Date"]) else "N/A"
                    st.write(f"**{row['Metric']}**: {latest_text} (latest date: {latest_date_text})")

                st.markdown("---")
                st.subheader("Key Comparison Bullets")

                for _, row in analysis_df.iterrows():
                    metric_full_name = row["Metric"]
                    metric_name = metric_full_name.replace("(AED Million)", "").replace("(AED million)", "").strip()

                    st.markdown(f"### {metric_full_name}")

                    if pd.notna(row["Selected Range Start Value"]) and pd.notna(row["Latest"]):
                        direction = "increased" if row["Range Absolute Change"] > 0 else "decreased"
                        start_period_text = row["Selected Range Start Date"].strftime("%b-%y")
                        latest_period_text = row["Latest Date"].strftime("%b-%y")
                        st.write(
                            f"- From **{start_period_text}** to the latest available period **{latest_period_text}**, "
                            f"**{metric_name}** {direction} from **{row['Selected Range Start Value']:,.2f}** "
                            f"to **{row['Latest']:,.2f}**, a move of "
                            f"**{row['Range Absolute Change']:,.2f} ({row['Range % Change']:.2f}%)**."
                        )

                    if pd.notna(row["Selected Range Mean"]) and pd.notna(row["Latest"]):
                        latest_vs_mean_direction = "above" if row["Latest vs Mean Absolute"] > 0 else "below"
                        st.write(
                            f"- The latest **{metric_name}** reading of **{row['Latest']:,.2f}** is "
                            f"**{abs(row['Latest vs Mean Absolute']):,.2f} ({abs(row['Latest vs Mean %']):.2f}%) "
                            f"{latest_vs_mean_direction}** the selected-range average of **{row['Selected Range Mean']:,.2f}**."
                        )

                    if pd.notna(row["Selected Range Min"]) and pd.notna(row["Selected Range Max"]):
                        st.write(
                            f"- Across the selected range, **{metric_name}** traded between "
                            f"**{row['Selected Range Min']:,.2f}** and **{row['Selected Range Max']:,.2f}**."
                        )

                    st.markdown("---")

                st.subheader("Analysis Table")

                analysis_display_df = analysis_df.copy()
                analysis_display_df.index = range(1, len(analysis_display_df) + 1)

                date_cols = ["Selected Range Start Date", "Latest Date"]
                for date_col in date_cols:
                    if date_col in analysis_display_df.columns:
                        analysis_display_df[date_col] = pd.to_datetime(
                            analysis_display_df[date_col], errors="coerce"
                        ).dt.strftime("%b-%y")

                def safe_number_format(x):
                    if pd.isna(x):
                        return ""
                    try:
                        return f"{float(x):,.2f}"
                    except Exception:
                        return x

                format_cols = [
                    col for col in analysis_display_df.columns
                    if col not in ["Metric", "Selected Range Start Date", "Latest Date"]
                ]

                st.dataframe(
                    analysis_display_df.style.format(
                        {col: safe_number_format for col in format_cols}
                    ),
                    use_container_width=True
                )

            else:
                conflict_date = pd.to_datetime("2026-02-28")
                pre_conflict_point_date = pd.to_datetime("2026-02-27")

                pre_df = filtered_df[filtered_df["Date"] < conflict_date].copy()
                post_df = filtered_df[filtered_df["Date"] >= conflict_date].copy()

                for col in selected_columns:
                    pre_series = pre_df[["Date", col]].dropna().sort_values("Date")
                    post_series = post_df[["Date", col]].dropna().sort_values("Date")
                    full_series = filtered_df[["Date", col]].dropna().sort_values("Date")

                    latest_value = full_series[col].iloc[-1] if not full_series.empty else None
                    latest_date = full_series["Date"].iloc[-1] if not full_series.empty else None

                    pre_mean = pre_series[col].mean() if not pre_series.empty else None
                    post_mean = post_series[col].mean() if not post_series.empty else None

                    pre_max = pre_series[col].max() if not pre_series.empty else None
                    post_max = post_series[col].max() if not post_series.empty else None
                    pre_min = pre_series[col].min() if not pre_series.empty else None
                    post_min = post_series[col].min() if not post_series.empty else None

                    pre_point_df = full_series[full_series["Date"] <= pre_conflict_point_date]
                    pre_conflict_value = pre_point_df.iloc[-1][col] if not pre_point_df.empty else None

                    point_abs_change = None
                    point_pct_change = None
                    if pre_conflict_value is not None and latest_value is not None:
                        point_abs_change = latest_value - pre_conflict_value
                        if pre_conflict_value != 0:
                            point_pct_change = (point_abs_change / pre_conflict_value) * 100

                    mean_abs_change = None
                    mean_pct_change = None
                    if pre_mean is not None and post_mean is not None:
                        mean_abs_change = post_mean - pre_mean
                        if pre_mean != 0:
                            mean_pct_change = (mean_abs_change / pre_mean) * 100

                    latest_vs_pre_mean_abs = None
                    latest_vs_pre_mean_pct = None
                    if pre_mean is not None and latest_value is not None:
                        latest_vs_pre_mean_abs = latest_value - pre_mean
                        if pre_mean != 0:
                            latest_vs_pre_mean_pct = (latest_vs_pre_mean_abs / pre_mean) * 100

                    analysis_rows.append({
                        "Metric": col,
                        "Pre-Conflict (27-Feb-2026)": pre_conflict_value,
                        "Latest Date": latest_date,
                        "Latest": latest_value,
                        "Point Absolute Change": point_abs_change,
                        "Point % Change": point_pct_change,
                        "Pre Mean": pre_mean,
                        "Post Mean": post_mean,
                        "Mean Absolute Change": mean_abs_change,
                        "Mean % Change": mean_pct_change,
                        "Latest vs Pre Mean Absolute": latest_vs_pre_mean_abs,
                        "Latest vs Pre Mean %": latest_vs_pre_mean_pct,
                        "Pre Min": pre_min,
                        "Pre Max": pre_max,
                        "Post Min": post_min,
                        "Post Max": post_max
                    })

                analysis_df = pd.DataFrame(analysis_rows)

                st.subheader("Current Latest Level")
                for _, row in analysis_df.iterrows():
                    latest_text = f"{row['Latest']:,.2f}" if pd.notna(row["Latest"]) else "N/A"
                    latest_date_text = row["Latest Date"].date() if pd.notna(row["Latest Date"]) else "N/A"
                    st.write(f"**{row['Metric']}**: {latest_text} (latest date: {latest_date_text})")

                st.markdown("---")
                st.subheader("Key Comparison Bullets")

                for _, row in analysis_df.iterrows():
                    metric_full_name = row["Metric"]
                    metric_name = metric_full_name.replace("(AED Million)", "").replace("(AED million)", "").strip()

                    st.markdown(f"### {metric_full_name}")

                    if pd.notna(row["Pre-Conflict (27-Feb-2026)"]) and pd.notna(row["Latest"]):
                        direction = "increased" if row["Point Absolute Change"] > 0 else "decreased"
                        st.write(
                            f"- From **27-Feb-2026** to the latest available date, **{metric_name}** {direction} "
                            f"from **{row['Pre-Conflict (27-Feb-2026)']:,.2f}** to **{row['Latest']:,.2f}**, "
                            f"a move of **{row['Point Absolute Change']:,.2f} ({row['Point % Change']:.2f}%)**."
                        )
                    else:
                        st.write(f"- **{metric_name}** does not have a valid pre-conflict observation for point-in-time comparison.")

                    if pd.notna(row["Pre Mean"]) and pd.notna(row["Post Mean"]):
                        mean_direction = "increased" if row["Mean Absolute Change"] > 0 else "decreased"
                        st.write(
                            f"- On an average basis, **{metric_name}** {mean_direction} from **{row['Pre Mean']:,.2f}** "
                            f"pre-conflict to **{row['Post Mean']:,.2f}** post-conflict, "
                            f"a move of **{row['Mean Absolute Change']:,.2f} ({row['Mean % Change']:.2f}%)**."
                        )
                    else:
                        st.write(f"- **{metric_name}** does not have enough data for pre-vs-post mean comparison.")

                    if pd.notna(row["Pre Mean"]) and pd.notna(row["Latest"]):
                        latest_vs_pre_direction = "above" if row["Latest vs Pre Mean Absolute"] > 0 else "below"
                        st.write(
                            f"- The latest **{metric_name}** reading of **{row['Latest']:,.2f}** is "
                            f"**{abs(row['Latest vs Pre Mean Absolute']):,.2f} ({abs(row['Latest vs Pre Mean %']):.2f}%) "
                            f"{latest_vs_pre_direction}** the pre-conflict average of **{row['Pre Mean']:,.2f}**."
                        )
                    else:
                        st.write(f"- **{metric_name}** does not have enough data for pre-conflict average versus latest comparison.")

                    if pd.notna(row["Pre Min"]) and pd.notna(row["Pre Max"]) and pd.notna(row["Post Min"]) and pd.notna(row["Post Max"]):
                        st.write(
                            f"- The **pre-conflict range** was **{row['Pre Min']:,.2f} to {row['Pre Max']:,.2f}**, "
                            f"while the **post-conflict range** was **{row['Post Min']:,.2f} to {row['Post Max']:,.2f}**."
                        )

                    st.markdown("---")

                if selected_sheet not in ["M-Bills Yields", "M-Bills Secondary Market Volume"]:
                    st.subheader("Biggest Movers")
                    movers_df = analysis_df.dropna(subset=["Point % Change"]).copy()

                    if not movers_df.empty:
                        movers_df["Abs Point % Change"] = movers_df["Point % Change"].abs()
                        movers_df = movers_df.sort_values("Abs Point % Change", ascending=False)

                        top_movers = movers_df.head(3)

                        for _, row in top_movers.iterrows():
                            direction = "up" if row["Point % Change"] > 0 else "down"
                            st.write(
                                f"- **{row['Metric']}** is one of the biggest movers, moving **{direction} {abs(row['Point % Change']):.2f}%** "
                                f"from **27-Feb-2026** to the latest available level."
                            )
                    else:
                        st.write("No sufficient data available to calculate biggest movers from 27-Feb-2026 to latest.")

                    st.markdown("---")

                st.subheader("Analysis Table")

                analysis_display_df = analysis_df.copy()
                analysis_display_df.index = range(1, len(analysis_display_df) + 1)

                if "Latest Date" in analysis_display_df.columns:
                    analysis_display_df["Latest Date"] = pd.to_datetime(
                        analysis_display_df["Latest Date"], errors="coerce"
                    ).dt.strftime("%Y-%m-%d")

                def safe_number_format(x):
                    if pd.isna(x):
                        return ""
                    try:
                        return f"{float(x):,.2f}"
                    except Exception:
                        return x

                format_cols = [
                    col for col in analysis_display_df.columns
                    if col not in ["Metric", "Latest Date"]
                ]

                st.dataframe(
                    analysis_display_df.style.format(
                        {col: safe_number_format for col in format_cols}
                    ),
                    use_container_width=True
                )

else:
    st.title("Daily Liquidity Dashboard")

    st.info("Upload an Excel file to begin.")
