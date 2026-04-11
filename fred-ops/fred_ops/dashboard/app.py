"""
Streamlit dashboard entrypoint. Launched via: streamlit run .../app.py

Requires env: FRED_OPS_CONFIG_PATH, FRED_OPS_SQLITE_PATH (set by fred-ops CLI when dashboard is enabled).
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st
import yaml

from fred_ops.config import DashboardConfig, FredOpsConfig

# Zona horaria para mostrar instantes (IANA). Override: export FRED_OPS_DASHBOARD_TZ=UTC
_DASHBOARD_TZ = os.environ.get("FRED_OPS_DASHBOARD_TZ", "America/Bogota")


def _ts_series_to_display_datetimes(ts_series: pd.Series) -> pd.Series:
    """Convierte epoch float (s) a Timestamp con zona horaria legible."""
    dt_utc = pd.to_datetime(ts_series, unit="s", utc=True)
    try:
        return dt_utc.dt.tz_convert(_DASHBOARD_TZ)
    except Exception:
        return dt_utc


def _load_config() -> FredOpsConfig:
    path = os.environ.get("FRED_OPS_CONFIG_PATH")
    if not path or not Path(path).is_file():
        st.error("Set FRED_OPS_CONFIG_PATH to your fred-ops YAML config file.")
        st.stop()
    with open(path) as f:
        raw = yaml.safe_load(f)
    return FredOpsConfig.model_validate(raw)


def _sqlite_path() -> str:
    p = os.environ.get("FRED_OPS_SQLITE_PATH")
    if p:
        return p
    st.error("FRED_OPS_SQLITE_PATH is not set.")
    st.stop()
    return ""


def _flatten_payload_scalars(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Aplana JSON a columnas: números, texto, booleanos y listas serializadas (para tabla)."""
    out: dict[str, Any] = {}
    key = prefix.rstrip(".") if prefix else ""

    if isinstance(obj, bool):
        if key:
            out[key] = obj
        return out
    if isinstance(obj, int) and not isinstance(obj, bool):
        if key:
            out[key] = obj
        return out
    if isinstance(obj, float):
        if key:
            out[key] = obj
        return out
    if isinstance(obj, str):
        if key:
            out[key] = obj
        return out
    if obj is None:
        if key:
            out[key] = None
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            nk = f"{prefix}{k}."
            out.update(_flatten_payload_scalars(v, nk))
        return out
    if isinstance(obj, list):
        if key:
            out[key] = json.dumps(obj, ensure_ascii=False)
        return out
    if key:
        out[key] = str(obj)
    return out


def _numeric_columns_for_chart(df: pd.DataFrame) -> list[str]:
    skip = {"ts", "mode", "meta_mqtt_topic"}
    cols: list[str] = []
    for c in df.columns:
        if c in skip:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            cols.append(c)
    return cols


def _dataframe_column_config(df: pd.DataFrame) -> dict[str, Any]:
    """Tipos de columna para la tabla: fecha corta, números, texto, booleanos."""
    cfg: dict[str, Any] = {}
    for col in df.columns:
        if col == "ts":
            cfg[col] = st.column_config.DatetimeColumn(
                "Hora",
                format="DD/MM/YY HH:mm",
            )
        elif pd.api.types.is_bool_dtype(df[col]):
            cfg[col] = st.column_config.CheckboxColumn(col)
        elif pd.api.types.is_numeric_dtype(df[col]):
            cfg[col] = st.column_config.NumberColumn(col, format="%.6g")
        else:
            cfg[col] = st.column_config.TextColumn(col)
    return cfg


def _events_to_frame(conn: sqlite3.Connection, limit: int = 1000) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT ts, mode, input_json, output_json, meta_json FROM events ORDER BY ts DESC LIMIT ?",
        conn,
        params=(int(limit),),
    )
    if df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        r: dict[str, Any] = {"ts": row["ts"], "mode": row["mode"]}
        if row["input_json"]:
            inj = json.loads(row["input_json"])
            for k, v in _flatten_payload_scalars(inj).items():
                r[f"input_{k}"] = v
        if row["output_json"]:
            outj = json.loads(row["output_json"])
            for k, v in _flatten_payload_scalars(outj).items():
                r[f"output_{k}"] = v
        if row["meta_json"]:
            meta = json.loads(row["meta_json"])
            if isinstance(meta, dict) and "mqtt_topic" in meta:
                r["meta_mqtt_topic"] = meta["mqtt_topic"]
        rows.append(r)
    out_df = pd.DataFrame(rows)
    if not out_df.empty and "ts" in out_df.columns:
        out_df = out_df.sort_values("ts")
        out_df["ts"] = _ts_series_to_display_datetimes(out_df["ts"])
    return out_df


def main() -> None:
    st.set_page_config(page_title="fred-ops dashboard", layout="wide")
    cfg = _load_config()
    if cfg.dashboard is None or not cfg.dashboard.enabled:
        st.error(
            "El dashboard está desactivado. Añade una sección `dashboard` en el YAML con `enabled: true`."
        )
        st.stop()
    dashboard_cfg: DashboardConfig = cfg.dashboard
    db_path = _sqlite_path()

    st.title("fred-ops · dashboard")
    st.caption(f"Modo: **{cfg.mode}** · SQLite: `{db_path}`")

    if not Path(db_path).is_file():
        st.warning("Aún no hay base de datos. Arranca el procesador MQTT con `dashboard.enabled: true`.")
        return

    @st.cache_resource
    def _get_conn(p: str) -> sqlite3.Connection:
        return sqlite3.connect(p, check_same_thread=False)

    conn = _get_conn(db_path)

    @st.fragment(run_every=2.0)
    def _refresh() -> None:
        df = _events_to_frame(conn, limit=min(dashboard_cfg.max_rows, 2000))
        if df.empty:
            st.info("Sin eventos todavía. Cuando lleguen mensajes MQTT aparecerán aquí.")
            return

        numeric_cols = _numeric_columns_for_chart(df)
        st.subheader("Serie temporal")
        st.caption(f"Hora mostrada en **{_DASHBOARD_TZ}** · `FRED_OPS_DASHBOARD_TZ` en el entorno para otra zona IANA (p. ej. `UTC`).")
        if numeric_cols:
            y_choice = st.multiselect("Campos numéricos (eje Y)", numeric_cols, default=numeric_cols[: min(3, len(numeric_cols))])
            if y_choice:
                chart_df = df[["ts"] + y_choice].dropna(how="all", subset=y_choice)
                long_df = chart_df.melt(
                    id_vars=["ts"],
                    var_name="serie",
                    value_name="valor",
                )
                chart = (
                    alt.Chart(long_df)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X(
                            "ts:T",
                            title="Hora",
                            axis=alt.Axis(
                                format="%d/%m/%y %H:%M",
                                labelAngle=-35,
                                tickCount=8,
                            ),
                        ),
                        y=alt.Y("valor:Q", title="Valor"),
                        color=alt.Color("serie:N", title="Serie"),
                        tooltip=[
                            alt.Tooltip("ts:T", title="Hora", format="%d/%m/%y %H:%M:%S"),
                            alt.Tooltip("serie:N", title="Campo"),
                            alt.Tooltip("valor:Q", title="Valor", format=".6g"),
                        ],
                    )
                    .properties(height=320)
                    .interactive()
                )
                st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("No hay campos numéricos en los últimos registros; revisa el schema o el payload JSON.")

        st.subheader("Últimos registros")
        show = df.sort_values("ts", ascending=False).head(200)
        st.dataframe(
            show,
            use_container_width=True,
            height=280,
            column_config=_dataframe_column_config(show),
        )

    _refresh()


main()
