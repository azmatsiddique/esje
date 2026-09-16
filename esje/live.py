"""Non-blocking Live Dashboard Widget manager with ipywidgets Play/Pause/Stop controls."""

import base64
import io
import threading
import time
import uuid
from typing import Any, Dict, Optional

from IPython.display import HTML, display

from esje.connection import manager as conn_manager
from esje.display import DisplayWrapper, format_result

try:
    import ipywidgets as widgets  # type: ignore
    HAS_IPYWIDGETS = True
except ImportError:
    widgets = None  # type: ignore
    HAS_IPYWIDGETS = False


def render_html_widget(
    widget_id: str,
    content_html: str,
    interval: float,
    status: str = "PLAYING",
) -> str:
    status_color = "#28a745" if status == "PLAYING" else ("#ffc107" if status == "PAUSED" else "#dc3545")
    status_text = "🟢 Live Dashboard" if status == "PLAYING" else ("🟡 PAUSED" if status == "PAUSED" else "🔴 STOPPED")

    js_bridge = f"""
    <script>
    if (typeof window.esjeExec !== 'function') {{
        window.esjeExec = function(cmd) {{
            try {{
                if (window.IPython && window.IPython.notebook && window.IPython.notebook.kernel) {{
                    window.IPython.notebook.kernel.execute(cmd);
                }} else if (window.Jupyter && window.Jupyter.notebook && window.Jupyter.notebook.kernel) {{
                    window.Jupyter.notebook.kernel.execute(cmd);
                }}
            }} catch(e) {{
                console.log('esjeExec error:', e);
            }}
        }};
    }}
    </script>
    """

    return f"""{js_bridge}
<div id="esje-widget-{widget_id}" style="
    border: 1px solid #e1e4e8;
    border-radius: 10px;
    padding: 14px;
    margin: 10px 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #ffffff;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
">
    <div style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 10px;
        margin-bottom: 12px;
        border-bottom: 1px solid #eaecef;
    ">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background-color: {status_color};
            "></span>
            <span style="font-weight: 600; font-size: 13px; color: #24292e;">
                {status_text} <code style="font-size: 11px; background: #f6f8fa; padding: 2px 5px; border-radius: 3px;">{widget_id}</code>
            </span>
            <span style="font-size: 12px; color: #586069; background: #f1f3f5; padding: 2px 8px; border-radius: 12px;">
                {interval}s refresh
            </span>
        </div>
        <div style="display: flex; gap: 6px;">
            <button onclick="window.esjeExec('import esje; esje.resume_live(\\'{widget_id}\\')')" style="
                background: #28a745; color: white; border: none; border-radius: 5px;
                padding: 5px 10px; font-size: 12px; font-weight: 600; cursor: pointer;
            ">▶️ Play</button>

            <button onclick="window.esjeExec('import esje; esje.pause_live(\\'{widget_id}\\')')" style="
                background: #ffc107; color: #212529; border: none; border-radius: 5px;
                padding: 5px 10px; font-size: 12px; font-weight: 600; cursor: pointer;
            ">⏸️ Pause</button>

            <button onclick="window.esjeExec('import esje; esje.stop_live(\\'{widget_id}\\')')" style="
                background: #dc3545; color: white; border: none; border-radius: 5px;
                padding: 5px 10px; font-size: 12px; font-weight: 600; cursor: pointer;
            ">⏹️ Stop</button>
        </div>
    </div>
    <div id="esje-content-{widget_id}">
        {content_html}
    </div>
</div>
"""


class LiveWidget:
    """Class managing a single background live dashboard widget."""

    def __init__(
        self,
        widget_id: str,
        conn_name: Optional[str],
        sql_query: str,
        python_code: str,
        target_var: str,
        interval: float,
        shell: Any,
    ) -> None:
        self.widget_id = widget_id
        self.conn_name = conn_name
        self.sql_query = sql_query
        self.python_code = python_code
        self.target_var = target_var
        self.interval = interval
        self.shell = shell

        self.status = "PLAYING"  # PLAYING, PAUSED, STOPPED
        self.display_handle = None
        self.content_widget = None
        self.status_widget = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Render widget and start background updater thread."""
        initial_html = self._generate_content()

        if HAS_IPYWIDGETS:
            try:
                self.content_widget = widgets.HTML(value=initial_html)
                self.status_widget = widgets.HTML(
                    value=(
                        f'<span style="color: #28a745; font-weight: bold;">🟢 Live Dashboard</span> '
                        f'<code>{self.widget_id}</code> <span style="color: #666; font-size: 12px;">({self.interval}s refresh)</span>'
                    )
                )

                btn_play = widgets.Button(
                    description="▶ Play",
                    button_style="success",
                    layout=widgets.Layout(width="70px", height="28px"),
                )
                btn_pause = widgets.Button(
                    description="⏸ Pause",
                    button_style="warning",
                    layout=widgets.Layout(width="70px", height="28px"),
                )
                btn_stop = widgets.Button(
                    description="⏹ Stop",
                    button_style="danger",
                    layout=widgets.Layout(width="70px", height="28px"),
                )

                btn_play.on_click(lambda b: self.resume())
                btn_pause.on_click(lambda b: self.pause())
                btn_stop.on_click(lambda b: self.stop())

                header_box = widgets.HBox(
                    [self.status_widget, widgets.HBox([btn_play, btn_pause, btn_stop])],
                    layout=widgets.Layout(
                        justify_content="space-between",
                        align_items="center",
                        width="100%",
                    ),
                )

                container = widgets.VBox(
                    [header_box, self.content_widget],
                    layout=widgets.Layout(
                        border="1px solid #e1e4e8",
                        border_radius="10px",
                        padding="12px",
                        margin="8px 0",
                        background_color="#ffffff",
                    ),
                )
                display(container)
            except Exception:
                full_widget_html = render_html_widget(
                    widget_id=self.widget_id,
                    content_html=initial_html,
                    interval=self.interval,
                    status=self.status,
                )
                self.display_handle = display(HTML(full_widget_html), display_id=True)
        else:
            full_widget_html = render_html_widget(
                widget_id=self.widget_id,
                content_html=initial_html,
                interval=self.interval,
                status=self.status,
            )
            self.display_handle = display(HTML(full_widget_html), display_id=True)

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _generate_content(self) -> str:
        """Execute query, update DataFrame in shell namespace, and generate HTML image or table."""
        conn = conn_manager.get(self.conn_name)
        raw_result = conn.execute(self.sql_query)
        formatted = format_result(raw_result)

        if self.shell:
            target_obj = formatted.df if isinstance(formatted, DisplayWrapper) else formatted
            self.shell.user_ns[self.target_var] = target_obj

        if self.python_code.strip():
            try:
                import matplotlib
                import matplotlib.pyplot as plt
                import warnings

                matplotlib.use("Agg", force=True)
                plt.close("all")

                original_show = plt.show
                plt.show = lambda *a, **kw: None

                try:
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
                        exec(self.python_code, self.shell.user_ns if self.shell else {})
                        fig = plt.gcf()

                        buf = io.BytesIO()
                        fig.savefig(buf, format="png", bbox_inches="tight")
                        buf.seek(0)
                        b64 = base64.b64encode(buf.read()).decode("utf-8")
                    return (
                        f'<div style="text-align: center; padding: 6px;">'
                        f'<img src="data:image/png;base64,{b64}" '
                        f'style="max-width: 100%; height: auto; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);" />'
                        f'</div>'
                    )
                finally:
                    plt.show = original_show
                    plt.close("all")
            except Exception as exc:
                return f'<div style="color: red; padding: 10px;">Error running plot: {exc}</div>'
        else:
            if isinstance(formatted, DisplayWrapper):
                return formatted._repr_html_()
            return f"<pre>{formatted}</pre>"

    def _run_loop(self) -> None:
        """Background thread execution loop."""
        while self.status != "STOPPED":
            time.sleep(self.interval)
            if self.status == "PLAYING":
                try:
                    content_html = self._generate_content()
                    self._update_display(content_html)
                except Exception as exc:
                    self._update_display(f'<div style="color: red;">Live error: {exc}</div>')

    def pause(self) -> None:
        self.status = "PAUSED"
        if self.status_widget:
            self.status_widget.value = (
                f'<span style="color: #ffc107; font-weight: bold;">🟡 Live Dashboard (PAUSED)</span> '
                f'<code>{self.widget_id}</code>'
            )
        self._update_display(self._generate_content())

    def resume(self) -> None:
        self.status = "PLAYING"
        if self.status_widget:
            self.status_widget.value = (
                f'<span style="color: #28a745; font-weight: bold;">🟢 Live Dashboard</span> '
                f'<code>{self.widget_id}</code> <span style="color: #666; font-size: 12px;">({self.interval}s refresh)</span>'
            )
        self._update_display(self._generate_content())

    def stop(self) -> None:
        self.status = "STOPPED"
        if self.status_widget:
            self.status_widget.value = (
                f'<span style="color: #dc3545; font-weight: bold;">🔴 Live Dashboard (STOPPED)</span> '
                f'<code>{self.widget_id}</code>'
            )
        if self.content_widget:
            self.content_widget.value = (
                f'<div style="padding: 10px; color: #666; font-style: italic;">Dashboard stopped.</div>'
            )
        elif self.display_handle:
            widget_html = render_html_widget(
                widget_id=self.widget_id,
                content_html='<div style="padding: 10px; color: #666; font-style: italic;">Dashboard stopped.</div>',
                interval=self.interval,
                status="STOPPED",
            )
            self.display_handle.update(HTML(widget_html))

    def _update_display(self, content_html: str) -> None:
        if HAS_IPYWIDGETS and self.content_widget:
            self.content_widget.value = content_html
        if self.display_handle:
            widget_html = render_html_widget(
                widget_id=self.widget_id,
                content_html=content_html,
                interval=self.interval,
                status=self.status,
            )
            self.display_handle.update(HTML(widget_html))



class LiveManager:
    """Registry managing active background live widgets."""

    def __init__(self) -> None:
        self._widgets: Dict[str, LiveWidget] = {}

    def create(
        self,
        conn_name: Optional[str],
        sql_query: str,
        python_code: str,
        target_var: str,
        interval: float,
        shell: Any,
    ) -> LiveWidget:
        widget_id = f"live_{uuid.uuid4().hex[:6]}"
        widget = LiveWidget(
            widget_id=widget_id,
            conn_name=conn_name,
            sql_query=sql_query,
            python_code=python_code,
            target_var=target_var,
            interval=interval,
            shell=shell,
        )
        self._widgets[widget_id] = widget
        widget.start()
        return widget

    def pause(self, widget_id: Optional[str] = None) -> None:
        if widget_id and widget_id in self._widgets:
            self._widgets[widget_id].pause()
        elif not widget_id and self._widgets:
            for w in self._widgets.values():
                w.pause()

    def resume(self, widget_id: Optional[str] = None) -> None:
        if widget_id and widget_id in self._widgets:
            self._widgets[widget_id].resume()
        elif not widget_id and self._widgets:
            for w in self._widgets.values():
                w.resume()

    def stop(self, widget_id: Optional[str] = None) -> None:
        if widget_id and widget_id in self._widgets:
            w = self._widgets.pop(widget_id)
            w.stop()
        elif not widget_id and self._widgets:
            for w in list(self._widgets.values()):
                w.stop()
            self._widgets.clear()

    def list_active(self) -> Dict[str, str]:
        return {wid: w.status for wid, w in self._widgets.items()}


live_manager = LiveManager()
