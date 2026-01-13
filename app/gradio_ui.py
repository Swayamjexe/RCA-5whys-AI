"""
Gradio UI Module
Interactive web interface for RCA Analysis
"""

import gradio as gr
import requests
import os

# API base URL
API_BASE = "http://localhost:8000"

def format_chat_history(history):
    """Helper to ensure history is list of dicts for type='messages'"""
    if history is None:
        return []
    return history

def start_analysis(problem, history):
    """Initialize session and start chat"""
    if not problem.strip():
        raise gr.Error("Please describe the problem first.")
    
    try:
        response = requests.post(f"{API_BASE}/start", json={"problem": problem})
        response.raise_for_status()
        data = response.json()
        
        # Update session state with new tracking fields
        session_state = {
            "id": data["session_id"],
            "why_no": data["why_no"],
            "completed": False,
            "awaiting_improvement": False,
            "last_answer": "",
            "root_cause_found": False 
        }
        
        # Add bot welcome and first question
        history = format_chat_history(history)
        history.append({"role": "user", "content": problem})
        history.append({"role": "assistant", "content": f"**Why 1:** {data['current_question']}"})
        
        return session_state, history, gr.update(value="", interactive=True), gr.update(visible=True)
        
    except Exception as e:
        raise gr.Error(f"Connection failed: {str(e)}")

def process_user_input(user_msg, history, session):
    """Handle user answer submission"""
    
    # 1. Check if session is active
    if not session or not session.get("id"):
        raise gr.Error("No active session.")

    # 2. STOP if analysis is already done
    if session.get("completed", False):
        return history, session, gr.update(), gr.update(), gr.update(), gr.update(), gr.update()

    is_improving = session.get("awaiting_improvement", False)

    # 3. Validate Input (Allow empty ONLY if improving)
    if not user_msg.strip():
        if not is_improving:
            gr.Warning("Please provide an answer.")
            return history, session, gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
        else:
            # IMPROVEMENT SKIP: treating empty input as "keep old answer"
            pass 
    
    # 4. Prepare Payloads
    history = format_chat_history(history)
    payload = {"session_id": session["id"]}
    
    if is_improving:
        if not user_msg.strip():
            # SKIP CASE: Resend the LAST answer
            original_answer = session.get("last_answer", "")
            payload["answer"] = original_answer
            payload["improved_answer"] = original_answer
            history.append({"role": "user", "content": "(No changes made)"})
        else:
            # IMPROVE CASE: Send the new answer
            payload["answer"] = session.get("last_answer", "")
            payload["improved_answer"] = user_msg
            history.append({"role": "user", "content": user_msg})
            session["last_answer"] = user_msg
    else:
        # Normal Answer Case
        payload["answer"] = user_msg
        session["last_answer"] = user_msg
        history.append({"role": "user", "content": user_msg})

    # 5. Submit to API
    try:
        response = requests.post(f"{API_BASE}/answer", json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Case A: Needs Improvement
        if data.get("needs_improvement"):
            suggestion = data.get("improvement_suggestion")
            warning_msg = f"⚠️ **Please clarify:** {suggestion}"
            history.append({"role": "assistant", "content": warning_msg})
            session["awaiting_improvement"] = True
            
            return (
                history, 
                session, 
                gr.update(value="", placeholder="Enter improved answer (or press Enter to submit directly if no changes)..."),
                gr.update(visible=False), 
                gr.update(visible=False), 
                gr.update(visible=False), 
                gr.update(visible=False)
            )

        # Valid answer accepted
        session["awaiting_improvement"] = False

        # Case B: Next Why Question (Continue)
        if not data.get("root_cause_extracted") and not data.get("completed"):
            next_q = f"**Why {data['why_no']}:** {data['current_question']}"
            history.append({"role": "assistant", "content": next_q})
            session["why_no"] = data["why_no"]
            
            return (
                history, 
                session, 
                gr.update(value="", placeholder="Type your answer here..."),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False)
            )

        # Case C: Root Cause Extracted (Analysis Complete)
        if data.get("root_cause_extracted"):
            root_cause = data["root_cause"]
            history.append({"role": "assistant", "content": "✅ **Root Cause Identified!** Analyzing and generating report..."})
            
            # Set flag to True so the next event knows to generate report
            session["root_cause_found"] = True
            
            return (
                history,
                session,
                gr.update(value="", interactive=False, placeholder="Analysis complete."),
                gr.update(visible=True, value=f"### 🎯 Root Cause Found\n\n{root_cause}"),
                gr.update(visible=False), 
                gr.update(visible=True),  # Show loading
                gr.update(visible=False)
            )

    except Exception as e:
        history.append({"role": "assistant", "content": f"❌ Error: {str(e)}"})
        return history, session, gr.update(), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

def generate_final_report(session):
    """Trigger final report generation only if root cause is found"""
    
    # STRICT CHECK: Only generate if the flag is set
    if not session or not session.get("root_cause_found", False):
        return gr.update(), gr.update(), gr.update(), session
        
    try:
        response = requests.post(f"{API_BASE}/generate_report", json={"session_id": session["id"]})
        response.raise_for_status()
        data = response.json()
        
        report_content = data["report"]
        
        # Create an absolute path for the file to ensure Gradio can serve it
        filename = f"RCA_Report_{data['session_id'][:8]}.md"
        abs_path = os.path.abspath(filename)
        
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        # Mark session as fully completed to lock UI
        session["completed"] = True
            
        return (
            gr.update(visible=True, value=report_content), 
            gr.update(visible=False), 
            gr.update(visible=True, value=abs_path),
            session
        )
        
    except Exception as e:
        return gr.update(visible=True, value=f"Error generating report: {e}"), gr.update(visible=False), gr.update(visible=False), session

# --- UI Construction ---

def create_gradio_interface():
    with gr.Blocks(title="AI Root Cause Analysis", theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate")) as demo:
        
        session_state = gr.State({})
        
        gr.Markdown(
            """
            # 🔍 Intelligent Root Cause Analysis
            ### Automated 5 Whys Investigation & Reporting
            """
        )
        
        with gr.Row():
            # LEFT COLUMN: Chat Interface
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(
                    height=600,
                    type="messages",
                    avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/4712/4712009.png"),
                    show_label=False
                )
                
                with gr.Group():
                    msg_input = gr.Textbox(
                        show_label=False,
                        placeholder="Describe the incident to start...",
                        container=False,
                        lines=2,
                        scale=8
                    )
                    submit_btn = gr.Button("➤", variant="primary", scale=1, min_width=50)
            
            # RIGHT COLUMN: Results & Report
            with gr.Column(scale=1):
                with gr.Group(visible=False) as root_cause_group:
                    rc_markdown = gr.Markdown("Waiting for analysis...")
                
                with gr.Group(visible=False) as loading_group:
                    gr.HTML("""
                        <div style="text-align: center; padding: 20px;">
                            <div style="font-size: 24px;">📄</div>
                            <h3>Generating Comprehensive Report...</h3>
                            <p>Compiling Executive Summary, Analysis, and Actions.</p>
                        </div>
                    """)
                
                with gr.Group(visible=False) as report_group:
                    gr.Markdown("### 📋 Final Incident Report")
                    report_display = gr.Markdown(value="", elem_classes=["report-view"], container=True)
                    
                    with gr.Row():
                        download_btn = gr.DownloadButton(label="📥 Download Report (.md)", visible=False)

        # --- Event Wiring ---
        
        def handle_submit(user_input, history, session):
            if not session:
                return start_analysis(user_input, history)
            else:
                return session, history, gr.update(), gr.update()

        # Chain 1: User hits Enter
        msg_input.submit(
            fn=handle_submit,
            inputs=[msg_input, chatbot, session_state],
            outputs=[session_state, chatbot, msg_input, root_cause_group]
        ).then(
            fn=process_user_input,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, session_state, msg_input, root_cause_group, report_display, loading_group, download_btn]
        ).then(
            # FIX: Use root_cause_found flag instead of why_no
            fn=lambda v: generate_final_report(v) if v.get("root_cause_found") else (gr.update(), gr.update(), gr.update(), v),
            inputs=[session_state],
            outputs=[report_display, loading_group, download_btn, session_state]
        )
        
        # Chain 2: User clicks Button
        submit_btn.click(
            fn=handle_submit,
            inputs=[msg_input, chatbot, session_state],
            outputs=[session_state, chatbot, msg_input, root_cause_group]
        ).then(
            fn=process_user_input,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, session_state, msg_input, root_cause_group, report_display, loading_group, download_btn]
        ).then(
            # FIX: Use root_cause_found flag instead of why_no
            fn=lambda v: generate_final_report(v) if v.get("root_cause_found") else (gr.update(), gr.update(), gr.update(), v),
            inputs=[session_state],
            outputs=[report_display, loading_group, download_btn, session_state]
        )

    return demo

def launch_gradio():
    demo = create_gradio_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)

if __name__ == "__main__":
    launch_gradio()