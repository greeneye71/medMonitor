"""Chart components for temperature visualization."""

import plotly.graph_objects as go


def temperature_line_chart(
    readings: list[dict],
    thresholds: dict | None = None,
    title: str = "Temperature ultime 24h",
) -> go.Figure:
    """Create a line chart with temperature readings and threshold bands.

    Args:
        readings: List of reading dicts with temperature, timestamp, sensor_id
        thresholds: Dict of sensor_id -> (min, max) for threshold bands
        title: Chart title
    """
    fig = go.Figure()

    # Group readings by sensor
    sensors: dict[str, list] = {}
    for r in readings:
        sid = r.get("sensor_id", "unknown")
        if sid not in sensors:
            sensors[sid] = []
        sensors[sid].append(r)

    colors = ["#1D9E75", "#3B82F6", "#A855F7", "#F59E0B", "#EF4444"]

    for i, (sensor_id, data) in enumerate(sensors.items()):
        data.sort(key=lambda r: r.get("timestamp", ""))
        times = [r.get("timestamp", "") for r in data]
        temps = [r.get("temperature", 0) for r in data]
        color = colors[i % len(colors)]

        fig.add_trace(go.Scatter(
            x=times,
            y=temps,
            name=sensor_id,
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=4),
        ))

        # Add threshold bands if available
        if thresholds and sensor_id in thresholds:
            t_min, t_max = thresholds[sensor_id]
            fig.add_hrect(
                y0=t_min, y1=t_max,
                fillcolor="rgba(29, 158, 117, 0.1)",
                line=dict(color="rgba(29, 158, 117, 0.3)", width=1, dash="dash"),
                annotation_text=f"Soglia {sensor_id}",
                annotation_position="top left",
            )

    fig.update_layout(
        title=title,
        xaxis_title="Tempo",
        yaxis_title="Temperatura (°C)",
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color="#0f172a",
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(orientation="h", y=-0.2),
        hovermode="x unified",
    )

    return fig


def empty_chart(message: str = "Nessun dato disponibile") -> go.Figure:
    """Create an empty chart with a message."""
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color="#0f172a",
        annotations=[dict(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6c757d"),
        )],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
