import json
from pathlib import Path
from config import BASE_DIR

DASHBOARD_FILE = BASE_DIR / "dashboard.html"

def generate_dashboard_html(pending: list, flagged: list, commitments: list, digest: dict, followups: list):
    """
    Renders the dashboard with an executive, consultant-grade UI/UX.
    Features premium typography, FontAwesome icons, and a strict grid system.
    """
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>inboxHero | Executive Brief</title>
        
        <!-- Premium Typography & Icons -->
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Merriweather:wght@700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        
        <style>
            :root {{
                --mck-navy: #051C2C;
                --mck-blue: #005F9E;
                --bg-body: #F4F6F8;
                --bg-card: #FFFFFF;
                --border: #E2E8F0;
                --text-main: #1E293B;
                --text-muted: #64748B;
                --danger: #D32F2F;
                --success: #2E7D32;
                --warning: #ED6C02;
            }}
            
            body {{
                font-family: 'Inter', sans-serif;
                background-color: var(--bg-body);
                color: var(--text-main);
                margin: 0;
                padding: 0;
                -webkit-font-smoothing: antialiased;
            }}
            
            /* Top Executive Header */
            .header-bar {{
                background-color: var(--mck-navy);
                color: white;
                padding: 1.5rem 3rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .header-bar h1 {{
                font-family: 'Merriweather', serif;
                margin: 0;
                font-size: 1.5rem;
                letter-spacing: 0.5px;
            }}
            .header-bar .meta {{
                font-size: 0.85rem;
                color: #94A3B8;
                display: flex;
                gap: 20px;
                align-items: center;
            }}
            
            .container {{ padding: 2rem 3rem; max-width: 1600px; margin: 0 auto; }}
            
            /* KPI Summary Row */
            .kpi-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}
            .kpi-card {{
                background: var(--bg-card);
                border-left: 4px solid var(--mck-blue);
                padding: 1.25rem;
                border-radius: 4px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}
            .kpi-card.danger {{ border-left-color: var(--danger); }}
            .kpi-card.success {{ border-left-color: var(--success); }}
            .kpi-info h3 {{ margin: 0 0 5px 0; font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
            .kpi-info .value {{ font-size: 1.75rem; font-weight: 600; font-family: 'Merriweather', serif; color: var(--mck-navy); margin: 0; }}
            .kpi-icon {{ font-size: 2rem; color: var(--border); opacity: 0.5; }}
            
            /* Main Content Grids */
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 1.5rem;
                margin-bottom: 1.5rem;
            }}
            .card {{
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 6px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.02);
                overflow: hidden;
            }}
            .card-full {{ grid-column: 1 / -1; }}
            
            .card-header {{
                padding: 1.25rem 1.5rem;
                border-bottom: 1px solid var(--border);
                background: #F8FAFC;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .card-header h2 {{ margin: 0; font-size: 1rem; color: var(--mck-navy); font-weight: 600; display: flex; align-items: center; gap: 8px; width: 100%; }}
            .card-header h2 i {{ color: var(--mck-blue); }}
            .badge {{ margin-left: auto; background: var(--border); padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; color: var(--text-main); }}
            
            /* Table Styling */
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 1rem 1.5rem; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.875rem; }}
            th {{ font-weight: 600; color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; background: #FFFFFF; }}
            
            .interactive-row {{ cursor: pointer; transition: background 0.2s ease; }}
            .interactive-row:hover {{ background-color: #F8FAFC; }}
            .interactive-row td:first-child {{ font-weight: 500; color: var(--mck-navy); }}
            
            .details-content {{ display: none; padding: 1.5rem; background: #F1F5F9; border-left: 3px solid var(--mck-blue); font-size: 0.875rem; color: var(--text-main); line-height: 1.5; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02); }}
            .pill {{ display: inline-flex; align-items: center; gap: 5px; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }}
            .pill.blue {{ background: #E0F2FE; color: #0284C7; }}
            .pill.red {{ background: #FEE2E2; color: #DC2626; }}
            .pill.green {{ background: #DCFCE7; color: #16A34A; }}
            
            /* Terminal Input Generator */
            .terminal-box {{ padding: 1.5rem; }}
            .input-group {{ display: flex; gap: 10px; }}
            .input-group input {{ flex: 1; padding: 12px 15px; border: 1px solid var(--border); border-radius: 4px; font-size: 0.95rem; font-family: 'Inter', sans-serif; outline: none; transition: border 0.2s; }}
            .input-group input:focus {{ border-color: var(--mck-blue); }}
            .input-group button {{ background: var(--mck-navy); color: white; border: none; border-radius: 4px; padding: 0 25px; cursor: pointer; font-weight: 500; font-family: 'Inter', sans-serif; transition: background 0.2s; }}
            .input-group button:hover {{ background: var(--mck-blue); }}
            
            #cmd-output-container {{ display: none; margin-top: 15px; padding: 15px; background: #0F172A; border-radius: 6px; border-left: 4px solid var(--mck-blue); }}
            #cmd-output {{ color: #38BDF8; font-family: 'Courier New', Courier, monospace; font-size: 0.95rem; font-weight: 600; }}
            .cmd-label {{ color: #94A3B8; font-size: 0.8rem; margin: 10px 0 0 0; display: flex; align-items: center; gap: 5px; }}
        </style>
    </head>
    <body>
        
        <!-- Header -->
        <div class="header-bar">
            <h1><i class="fa-solid fa-layer-group" style="margin-right: 10px; opacity: 0.8;"></i>inboxHero Executive Brief</h1>
            <div class="meta">
                <span><i class="fa-solid fa-server"></i> System: Local Agent</span>
                <span id="timestamp"><i class="fa-regular fa-clock"></i> </span>
            </div>
        </div>

        <div class="container">
            <!-- KPI Summary Row -->
            <div class="kpi-grid">
                <div class="kpi-card success">
                    <div class="kpi-info">
                        <h3>Auto-Archived</h3>
                        <p class="value">{digest['archived']}</p>
                    </div>
                    <i class="fa-solid fa-check-double kpi-icon"></i>
                </div>
                <div class="kpi-card">
                    <div class="kpi-info">
                        <h3>Pending Actions</h3>
                        <p class="value">{len(pending)}</p>
                    </div>
                    <i class="fa-solid fa-hourglass-half kpi-icon"></i>
                </div>
                <div class="kpi-card {'danger' if flagged else ''}">
                    <div class="kpi-info">
                        <h3>Security Threats</h3>
                        <p class="value">{len(flagged)}</p>
                    </div>
                    <i class="fa-solid fa-shield-halved kpi-icon"></i>
                </div>
                <div class="kpi-card">
                    <div class="kpi-info">
                        <h3>Active Commitments</h3>
                        <p class="value">{len(commitments)}</p>
                    </div>
                    <i class="fa-solid fa-handshake kpi-icon"></i>
                </div>
            </div>
            
            <div class="grid">
                <!-- X2: Morning Digest -->
                <div class="card">
                    <div class="card-header">
                        <h2><i class="fa-solid fa-mug-hot"></i> X2: Morning Digest</h2>
                    </div>
                    <table>
                        <tr><th>Priority Unread Item</th></tr>
    """
    
    if not digest['needs_me']:
        html += "<tr><td style='color: var(--text-muted);'><i class='fa-solid fa-leaf' style='color: var(--success); margin-right: 8px;'></i> Inbox Zero achieved. No pending unread items.</td></tr>"
    else:
        for m in digest['needs_me']:
            html += f"<tr><td><div style='font-weight: 600; margin-bottom: 3px;'>{m['from']}</div><div style='color: var(--text-muted); font-size: 0.8rem;'>{m['subject']}</div></td></tr>"

    html += f"""
                    </table>
                </div>

                <!-- R3: Pending Approvals -->
                <div class="card">
                    <div class="card-header">
                        <h2><i class="fa-solid fa-clipboard-check"></i> R3: Pending Approvals <span class="badge">{len(pending)}</span></h2>
                    </div>
                    <table>
                        <tr><th>Target ID</th><th>Action</th><th style="width: 40px;"></th></tr>
    """
    if not pending:
        html += "<tr><td colspan='3' style='color: var(--text-muted);'>No items require human approval.</td></tr>"
    else:
        for p in pending:
            html += f"""
                        <tr class="interactive-row" onclick="toggleDetails('pending-{p['msg_id']}')">
                            <td style="font-family: monospace;">{p['msg_id']}</td>
                            <td><span class="pill blue"><i class="fa-solid fa-paper-plane"></i> {p['action']}</span></td>
                            <td style="color: var(--border); text-align: center;"><i class="fa-solid fa-chevron-down"></i></td>
                        </tr>
                        <tr><td colspan="3" style="padding:0; border:none;"><div id="pending-{p['msg_id']}" class="details-content"><strong>Context:</strong> {p['reason']}</div></td></tr>
            """

    html += f"""
                    </table>
                </div>

                <!-- R5: Security & Flags -->
                <div class="card">
                    <div class="card-header">
                        <h2><i class="fa-solid fa-user-shield" style="color: var(--danger);"></i> R5: Security & Flags <span class="badge">{len(flagged)}</span></h2>
                    </div>
                    <table>
                        <tr><th>Message ID</th><th>System Action</th><th style="width: 40px;"></th></tr>
    """
    
    if not flagged:
        html += "<tr><td colspan='3' style='color: var(--text-muted);'><i class='fa-solid fa-check-circle' style='color: var(--success); margin-right: 8px;'></i> No threats detected in this run.</td></tr>"
    else:
        for f in flagged:
            html += f"""
                        <tr class="interactive-row" onclick="toggleDetails('flagged-{f['msg_id']}')">
                            <td style="font-family: monospace;">{f['msg_id']}</td>
                            <td><span class="pill red"><i class="fa-solid fa-ban"></i> {f['action_taken']}</span></td>
                            <td style="color: var(--border); text-align: center;"><i class="fa-solid fa-chevron-down"></i></td>
                        </tr>
                        <tr><td colspan="3" style="padding:0; border:none;"><div id="flagged-{f['msg_id']}" class="details-content" style="border-left-color: var(--danger);"><strong>Detected Threat:</strong> {f['threat']}</div></td></tr>
            """

    html += f"""
                    </table>
                </div>
                
                <!-- X3: Follow-up Tracker -->
                <div class="card">
                    <div class="card-header">
                        <h2><i class="fa-solid fa-reply-all"></i> X3: Awaiting Reply <span class="badge">{len(followups)}</span></h2>
                    </div>
                    <table>
                        <tr><th>Sent To</th><th>Subject</th></tr>
    """
    if not followups:
        html += "<tr><td colspan='2' style='color: var(--text-muted);'>No outstanding outbound threads.</td></tr>"
    else:
        for f_msg in followups:
            html += f"<tr><td style='font-weight: 500;'>{f_msg['to']}</td><td style='color: var(--text-muted);'>{f_msg['subject']}</td></tr>"

    html += f"""
                    </table>
                </div>
            </div>

            <!-- R6: Commitments -->
            <div class="card card-full" style="margin-bottom: 1.5rem;">
                <div class="card-header">
                    <h2><i class="fa-solid fa-calendar-check"></i> R6: Forward Commitments & Schedule <span class="badge">{len(commitments)}</span></h2>
                </div>
                <table>
                    <tr><th>Date & Time</th><th>Commitment Description</th><th>Source Trace</th><th>Status Notes</th><th style="width: 40px;"></th></tr>
    """
    for idx, c in enumerate(commitments):
        is_conflict = c.get('conflict')
        notes_html = f"<span style='color: var(--danger); font-weight: 600;'><i class='fa-solid fa-triangle-exclamation'></i> Conflict Detected</span>" if is_conflict else "<span style='color: var(--success);'><i class='fa-solid fa-check'></i> Clear</span>"
        border_color = 'var(--danger)' if is_conflict else 'var(--mck-blue)'
        
        html += f"""
                    <tr class="interactive-row" onclick="toggleDetails('commit-{idx}')">
                        <td style="white-space: nowrap; font-weight: 600; color: var(--mck-navy);"><i class="fa-regular fa-clock" style="color: var(--text-muted); margin-right: 5px;"></i> {c['datetime']}</td>
                        <td style="font-weight: 500;">{c['desc']}</td>
                        <td style="font-family: monospace; color: var(--text-muted); font-size: 0.8rem;">{c['sources']}</td>
                        <td>{notes_html}</td>
                        <td style="color: var(--border); text-align: center;"><i class="fa-solid fa-chevron-down"></i></td>
                    </tr>
                    <tr><td colspan="5" style="padding:0; border:none;"><div id="commit-{idx}" class="details-content" style="border-left-color: {border_color};"><strong>Resolution Notes:</strong> {c.get('notes', 'No additional notes.')}</div></td></tr>
        """

    html += f"""
                </table>
            </div>

            <!-- X1: Inbox Q&A Command Generator -->
            <div class="card card-full">
                <div class="card-header">
                    <h2><i class="fa-solid fa-terminal"></i> X1: Inbox Intelligence Query Engine</h2>
                </div>
                <div class="terminal-box">
                    <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 0; margin-bottom: 1.25rem;">
                        Translate natural language questions into executable pipeline commands for the local LLM to evaluate.
                    </p>
                    
                    <div class="input-group">
                        <input type="text" id="x1-input" placeholder="e.g., What time is my dental appointment with Dr. Osei?">
                        <button onclick="generateCommand()"><i class="fa-solid fa-microchip" style="margin-right: 8px;"></i> Compile Command</button>
                    </div>
                    
                    <div id="cmd-output-container">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="color: #64748B; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; letter-spacing: 1px;">Ready for Execution</span>
                            <i class="fa-regular fa-copy" style="color: #64748B; cursor: pointer;" onclick="navigator.clipboard.writeText(document.getElementById('cmd-output').innerText); alert('Copied to clipboard');"></i>
                        </div>
                        <code id="cmd-output"></code>
                        <div class="cmd-label"><i class="fa-solid fa-circle-info"></i> Execute this string in your terminal environment to query the live system.</div>
                    </div>
                </div>
            </div>

        </div>

        <script>
            // Set timestamp
            const options = {{ weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }};
            document.getElementById('timestamp').innerHTML += new Date().toLocaleDateString('en-US', options);
            
            // Accordion Logic
            function toggleDetails(id) {{
                const el = document.getElementById(id);
                el.style.display = el.style.display === "block" ? "none" : "block";
            }}
            
            // X1 Command Generator
            function generateCommand() {{
                const input = document.getElementById('x1-input').value;
                if (!input) return;
                
                document.getElementById('cmd-output').innerText = `python demo.py --cap X1 --query "${{input}}"`;
                document.getElementById('cmd-output-container').style.display = 'block';
            }}
            
            document.getElementById('x1-input').addEventListener('keypress', function (e) {{
                if (e.key === 'Enter') generateCommand();
            }});
        </script>
    </body>
    </html>
    """

    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[DASHBOARD] Successfully rendered executive dashboard to {DASHBOARD_FILE.name}")