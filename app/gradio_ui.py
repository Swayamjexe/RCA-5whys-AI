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
        
        return session_state, history, gr.update(value=""), gr.update(visible=True)
        
    except Exception as e:
        raise gr.Error(f"Connection failed: {str(e)}")

def process_user_input(user_msg, history, session):
    """Handle user answer submission"""
    
    # 1. Check if session is active
    if not session or not session.get("id"):
        raise gr.Error("No active session.")

    # 2. STOP if analysis is already done
    if session.get("completed", False):
        return history, session, gr.update()

    is_improving = session.get("awaiting_improvement", False)

    # 3. Validate Input (Allow empty ONLY if improving)
    if not user_msg.strip():
        if not is_improving:
            gr.Warning("Please provide an answer.")
            return history, session, gr.update()
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
                gr.update(value="", placeholder="Enter improved answer (or press Enter to skip)...")
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
                gr.update(value="", placeholder="Type your answer here...")
            )

        # Case C: Root Cause Extracted (Analysis Complete)
        if data.get("root_cause_extracted"):
            root_cause = data["root_cause"]
            
            # NEW: Check if early stopping occurred
            early_stop_msg = ""
            if data.get("why_no") < 5:
                early_stop_msg = f"\n\n🎯 **Early Termination at Why {data['why_no']}**\nSystematic root cause identified - no need to continue to Why 5.\n"
            
            history.append({"role": "assistant", "content": f"✅ **Root Cause Identified!**{early_stop_msg}\n### 🎯 Root Cause\n{root_cause}\n\n📄 Generating comprehensive report..."})
            
            # Set flag to True so the next event knows to generate report
            session["root_cause_found"] = True
            
            return (
                history,
                session,
                gr.update(value="", placeholder="Analysis complete.")
            )

    except Exception as e:
        history.append({"role": "assistant", "content": f"❌ Error: {str(e)}"})
        return history, session, gr.update()

def generate_final_report(session, history):
    """Trigger final report generation and switch to report view"""
    
    # STRICT CHECK: Only generate if the flag is set
    if not session or not session.get("root_cause_found", False):
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), "chat", session
        
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
        
        # Add final message to chat
        history.append({"role": "assistant", "content": "✅ **Report Generated Successfully!** View the complete analysis report."})
            
        return (
            gr.update(visible=False),  # chat_view - Hide chat
            gr.update(visible=True),   # report_view - Show report
            gr.update(value=report_content),  # report_display
            gr.update(visible=True, value=abs_path),  # download_btn
            history,  # Updated chat history
            "report",  # view_state
            session
        )
        
    except Exception as e:
        history.append({"role": "assistant", "content": f"❌ Error generating report: {e}"})
        return (
            gr.update(),  # chat_view
            gr.update(),  # report_view
            gr.update(),  # report_display
            gr.update(),  # download_btn
            history,
            "chat",  # Stay in chat view
            session
        )

def toggle_chat_drawer(current_visibility, history):
    """Toggle the chat history drawer visibility"""
    new_visibility = not current_visibility
    return gr.update(visible=new_visibility), history

def reset_to_new_analysis():
    """Reset everything for a new analysis"""
    return (
        {},  # Reset session
        [],  # Clear chat history
        gr.update(value="", placeholder="Describe the incident to start..."),  # Reset input
        gr.update(visible=True),  # Show chat view
        gr.update(visible=False),  # Hide report view
        gr.update(visible=False),  # Hide chat drawer
        [],  # Clear drawer history
        "chat"  # Reset view state
    )

# --- UI Construction ---

def create_gradio_interface():
    with gr.Blocks(title="AI Root Cause Analysis", theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"), css="""
        .chat-container {transition: all 0.3s ease;}
        .report-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .report-content {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
    """) as demo:
        
        session_state = gr.State({})
        view_state = gr.State("chat")  # "chat" or "report"
        
        # CHAT VIEW (Full Width)
        with gr.Column(visible=True, elem_classes=["chat-container"]) as chat_view:
            gr.Markdown(
                """
                # 🔍 Intelligent Root Cause Analysis
                ### Automated 5 Whys Investigation & Reporting
                """
            )
            
            chatbot = gr.Chatbot(
                height=400,
                type="messages",
                avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/4712/4712009.png"),
                show_label=False
            )
            
            with gr.Group():
                with gr.Row():
                    msg_input = gr.Textbox(
                        show_label=False,
                        placeholder="Describe the incident to start...",
                        container=False,
                        lines=2,
                        scale=8
                    )
                    submit_btn = gr.Button("➤", variant="primary", scale=1, min_width=50)
        
        # REPORT VIEW (Full Width, Initially Hidden)
        with gr.Column(visible=False) as report_view:
            with gr.Group(elem_classes=["report-header"]):
                gr.Markdown("# 📋 Root Cause Analysis Report")
                with gr.Row():
                    toggle_chat_btn = gr.Button("💬 View Chat History", size="sm", scale=1)
                    download_btn = gr.DownloadButton("📥 Download Report", size="sm", scale=1, visible=False)
                    new_analysis_btn = gr.Button("🔄 New Analysis", size="sm", variant="secondary", scale=1)
            
            with gr.Group(elem_classes=["report-content"]):
                report_display = gr.Markdown(value="", container=True)
        
        # CHAT HISTORY DRAWER (Overlay/Modal)
        with gr.Column(visible=False) as chat_drawer:
            with gr.Group():
                with gr.Row():
                    gr.Markdown("### 💬 Chat History")
                    close_drawer_btn = gr.Button("✖ Close", size="sm", variant="secondary")
                
                chat_history_display = gr.Chatbot(
                    height=400,
                    type="messages",
                    avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/4712/4712009.png"),
                    show_label=False
                )

        # --- Event Wiring ---
        
        def handle_submit(user_input, history, session):
            if not session or not session.get("id"):
                return start_analysis(user_input, history)
            else:
                return session, history, gr.update(), gr.update()

        # Chain: User submits input (Enter or Button)
        submit_event = msg_input.submit(
            fn=handle_submit,
            inputs=[msg_input, chatbot, session_state],
            outputs=[session_state, chatbot, msg_input, chat_view]
        ).then(
            fn=process_user_input,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, session_state, msg_input]
        ).then(
            fn=lambda s, h: generate_final_report(s, h) if s.get("root_cause_found") else (
                gr.update(), gr.update(), gr.update(), gr.update(), h, "chat", s
            ),
            inputs=[session_state, chatbot],
            outputs=[chat_view, report_view, report_display, download_btn, chatbot, view_state, session_state]
        )
        
        # Button click does the same
        submit_btn.click(
            fn=handle_submit,
            inputs=[msg_input, chatbot, session_state],
            outputs=[session_state, chatbot, msg_input, chat_view]
        ).then(
            fn=process_user_input,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, session_state, msg_input]
        ).then(
            fn=lambda s, h: generate_final_report(s, h) if s.get("root_cause_found") else (
                gr.update(), gr.update(), gr.update(), gr.update(), h, "chat", s
            ),
            inputs=[session_state, chatbot],
            outputs=[chat_view, report_view, report_display, download_btn, chatbot, view_state, session_state]
        )
        
        # Toggle chat history drawer
        drawer_visible = gr.State(False)
        
        toggle_chat_btn.click(
            fn=lambda v, h: (gr.update(visible=not v), h, not v),
            inputs=[drawer_visible, chatbot],
            outputs=[chat_drawer, chat_history_display, drawer_visible]
        )
        
        close_drawer_btn.click(
            fn=lambda: (gr.update(visible=False), False),
            outputs=[chat_drawer, drawer_visible]
        )
        
        # New analysis button
        new_analysis_btn.click(
            fn=reset_to_new_analysis,
            outputs=[
                session_state,
                chatbot,
                msg_input,
                chat_view,
                report_view,
                chat_drawer,
                chat_history_display,
                view_state
            ]
        )

    return demo

def launch_gradio():
    demo = create_gradio_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)

if __name__ == "__main__":
    launch_gradio()