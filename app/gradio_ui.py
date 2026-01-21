"""
Gradio UI Module - MULTIMODAL VERSION
Interactive web interface with image upload support
"""

import gradio as gr
import requests
import mimetypes
import os

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
        
        session_state = {
            "id": data["session_id"],
            "why_no": data["why_no"],
            "completed": False,
            "awaiting_improvement": False,
            "last_answer": "",
            "root_cause_found": False,
            "uploaded_image": None
        }
        
        history = format_chat_history(history)
        history.append({"role": "user", "content": problem})
        history.append({"role": "assistant", "content": f"**Why {data['why_no']}:** {data['current_question']}\n\n💡 *You can optionally upload an image as evidence.*"})
        
        return session_state, history, gr.update(value=""), gr.update(visible=True), gr.update(value=None), ""
        
    except Exception as e:
        raise gr.Error(f"Connection failed: {str(e)}")

def upload_image_handler(image, session):
    """Handle image upload for current Why question"""
    if not session or not session.get("id"):
        gr.Warning("Please start an analysis first.")
        return session, "⚠️ No active session"
    
    if session.get("completed", False):
        gr.Warning("Analysis already completed.")
        return session, "⚠️ Analysis complete"
    
    if image is None:
        return session, "⚠️ No image selected"
    
    try:
        # Upload image to API
        mime_type, _ = mimetypes.guess_type(image)
        files = {
            "file": (
                os.path.basename(image),
                open(image, "rb"),
                mime_type or "image/png"
            )
        }
        response = requests.post(
            f"{API_BASE}/upload_image/{session['id']}",
            files=files
        )
        response.raise_for_status()
        data = response.json()
        
        session["uploaded_image"] = image  # Store local path for display
        return session, f"✅ Image uploaded: {data['filename']}\nImage will be analyzed when you submit your answer."
        
    except Exception as e:
        return session, f"❌ Upload failed: {str(e)}"

def process_user_input(user_msg, history, session):
    """Handle user answer submission"""
    
    if not session or not session.get("id"):
        raise gr.Error("No active session.")

    if session.get("completed", False):
        return history, session, gr.update(), gr.update(value=None), ""

    is_improving = session.get("awaiting_improvement", False)

    if not user_msg.strip():
        if not is_improving:
            gr.Warning("Please provide an answer.")
            return history, session, gr.update(), gr.update(value=None), ""
        else:
            pass
    
    history = format_chat_history(history)
    payload = {"session_id": session["id"]}
    
    if is_improving:
        if not user_msg.strip():
            original_answer = session.get("last_answer", "")
            payload["answer"] = original_answer
            payload["improved_answer"] = original_answer
            history.append({"role": "user", "content": "(No changes made)"})
        else:
            payload["answer"] = session.get("last_answer", "")
            payload["improved_answer"] = user_msg
            history.append({"role": "user", "content": user_msg})
            session["last_answer"] = user_msg
    else:
        payload["answer"] = user_msg
        session["last_answer"] = user_msg
        
        # Add image to chat history if uploaded
        if session.get("uploaded_image"):
            img_path = session["uploaded_image"]
            history.append({
                "role": "user",
                "content": {
                    "path": img_path,
                    "alt_text": f"Evidence image"
                }
            })
            history.append({"role": "user", "content": user_msg})
        else:
            history.append({"role": "user", "content": user_msg})

    try:
        response = requests.post(f"{API_BASE}/answer", json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Display image analysis if available
        image_analysis = data.get("image_analysis")
        if image_analysis:
            analysis_msg = f"🔍 **Image Analysis:**\n{image_analysis}\n\n---\n"
            history.append({"role": "assistant", "content": analysis_msg})
        
        # Clear uploaded image after processing
        session["uploaded_image"] = None
        upload_status = ""
        
        # Case A: Needs Improvement
        if data.get("needs_improvement"):
            suggestion = data.get("improvement_suggestion")
            
            # Check if image was requested
            if data.get("image_requested"):
                warning_msg = f"📷 **Image Evidence Requested**\n\n{suggestion}\n\n*Please upload an image to provide visual evidence, or provide more detailed text description.*"
            else:
                warning_msg = f"⚠️ **Please clarify:** {suggestion}"
            
            history.append({"role": "assistant", "content": warning_msg})
            session["awaiting_improvement"] = True
            
            return (
                history,
                session,
                gr.update(value="", placeholder="Enter improved answer or upload image evidence..."),
                gr.update(value=None),
                upload_status
            )

        session["awaiting_improvement"] = False

        # Case B: Next Why Question
        if not data.get("root_cause_extracted") and not data.get("completed"):
            next_q = f"**Why {data['why_no']}:** {data['current_question']}\n\n💡 *You can optionally upload an image as evidence.*"
            history.append({"role": "assistant", "content": next_q})
            session["why_no"] = data["why_no"]
            
            return (
                history,
                session,
                gr.update(value="", placeholder="Type your answer here..."),
                gr.update(value=None),
                upload_status
            )

        # Case C: Root Cause Extracted
        if data.get("root_cause_extracted"):
            root_cause = data["root_cause"]
            
            early_stop_msg = ""
            if data.get("why_no") < 5:
                early_stop_msg = f"\n\n🎯 **Early Termination at Why {data['why_no']}**\nSystematic root cause identified - no need to continue to Why 5.\n"
            
            history.append({"role": "assistant", "content": f"✅ **Root Cause Identified!**{early_stop_msg}\n### 🎯 Root Cause\n{root_cause}\n\n📄 Generating comprehensive report..."})
            
            session["root_cause_found"] = True
            
            return (
                history,
                session,
                gr.update(value="", placeholder="Analysis complete."),
                gr.update(value=None),
                upload_status
            )

    except Exception as e:
        history.append({"role": "assistant", "content": f"❌ Error: {str(e)}"})
        return history, session, gr.update(), gr.update(value=None), ""

def generate_final_report(session, history):
    """Trigger final report generation"""
    
    if not session or not session.get("root_cause_found", False):
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), "chat", session
        
    try:
        response = requests.post(f"{API_BASE}/generate_report", json={"session_id": session["id"]})
        response.raise_for_status()
        data = response.json()
        
        report_content = data["report"]
        
        filename = f"RCA_Report_{data['session_id'][:8]}.md"
        abs_path = os.path.abspath(filename)
        
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        session["completed"] = True
        
        history.append({"role": "assistant", "content": "✅ **Report Generated Successfully!** View the complete analysis report."})
            
        return (
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(value=report_content),
            gr.update(visible=True, value=abs_path),
            history,
            "report",
            session
        )
        
    except Exception as e:
        history.append({"role": "assistant", "content": f"❌ Error generating report: {e}"})
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            history,
            "chat",
            session
        )

def reset_to_new_analysis(session):
    """Reset everything for new analysis and cleanup old session"""
    if session and session.get("id"):
        try:
            requests.delete(f"{API_BASE}/cleanup/{session['id']}")
        except:
            pass
    
    return (
        {},
        [],
        gr.update(value="", placeholder="Describe the incident to start..."),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        [],
        "chat",
        gr.update(value=None),
        ""
    )

# --- UI Construction ---

def create_gradio_interface():
    with gr.Blocks(
        title="AI Root Cause Analysis - Multimodal",
        theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
        css="""
        .chat-container {
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
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
        .image-upload-box {
            border: 2px dashed #667eea;
            border-radius: 8px;
            padding: 8px;
            background: #f8f9fa;
        }
        .input-container {
            position: sticky;
            bottom: 0;
            background: white;
            padding: 10px 0;
            z-index: 100;
        }
        .compact-image {
            max-height: 100px !important;
        }
        """
    ) as demo:
        
        session_state = gr.State({})
        view_state = gr.State("chat")
        
        # CHAT VIEW
        with gr.Column(visible=True, elem_classes=["chat-container"]) as chat_view:
            gr.Markdown(
                """
                # 🔍 Intelligent Root Cause Analysis (Multimodal)
                ### Automated 5 Whys Investigation with Image Evidence Support
                """
            )
            
            chatbot = gr.Chatbot(
                height=500,
                type="messages",
                avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/4712/4712009.png"),
                show_label=False
            )
            
            # Input container stays at bottom
            with gr.Group(elem_classes=["input-container"]):
                # Compact image upload
                with gr.Row():
                    image_input = gr.Image(
                        type="filepath",
                        label="📷 Upload Evidence (Optional)",
                        height=80,
                        scale=2,
                        elem_classes=["compact-image"]
                    )
                    with gr.Column(scale=1):
                        upload_btn = gr.Button("📤 Upload", size="sm")
                        upload_status = gr.Textbox(
                            label="",
                            interactive=False,
                            max_lines=2,
                            show_label=False,
                            container=False
                        )
                
                # Larger text input
                with gr.Row():
                    msg_input = gr.Textbox(
                        show_label=False,
                        placeholder="Describe the incident to start...",
                        container=False,
                        lines=3,
                        scale=8
                    )
                    submit_btn = gr.Button("➤", variant="primary", scale=1, min_width=50)
        
        # REPORT VIEW
        with gr.Column(visible=False) as report_view:
            with gr.Group(elem_classes=["report-header"]):
                gr.Markdown("# 📋 Root Cause Analysis Report")
                with gr.Row():
                    toggle_chat_btn = gr.Button("💬 View Chat History", size="sm", scale=1)
                    download_btn = gr.DownloadButton("📥 Download Report", size="sm", scale=1, visible=False)
                    new_analysis_btn = gr.Button("🔄 New Analysis", size="sm", variant="secondary", scale=1)
            
            with gr.Group(elem_classes=["report-content"]):
                report_display = gr.Markdown(value="", container=True)
        
        # CHAT HISTORY DRAWER
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

        # --- Event Handlers ---
        
        def handle_submit(user_input, history, session):
            if not session or not session.get("id"):
                return start_analysis(user_input, history)
            else:
                return session, history, gr.update(), gr.update(), gr.update(value=None), ""

        # Image upload
        upload_btn.click(
            fn=upload_image_handler,
            inputs=[image_input, session_state],
            outputs=[session_state, upload_status]
        )
        
        # Submit answer
        submit_event = msg_input.submit(
            fn=handle_submit,
            inputs=[msg_input, chatbot, session_state],
            outputs=[session_state, chatbot, msg_input, chat_view, image_input, upload_status]
        ).then(
            fn=process_user_input,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, session_state, msg_input, image_input, upload_status]
        ).then(
            fn=lambda s, h: generate_final_report(s, h) if s.get("root_cause_found") else (
                gr.update(), gr.update(), gr.update(), gr.update(), h, "chat", s
            ),
            inputs=[session_state, chatbot],
            outputs=[chat_view, report_view, report_display, download_btn, chatbot, view_state, session_state]
        )
        
        submit_btn.click(
            fn=handle_submit,
            inputs=[msg_input, chatbot, session_state],
            outputs=[session_state, chatbot, msg_input, chat_view, image_input, upload_status]
        ).then(
            fn=process_user_input,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, session_state, msg_input, image_input, upload_status]
        ).then(
            fn=lambda s, h: generate_final_report(s, h) if s.get("root_cause_found") else (
                gr.update(), gr.update(), gr.update(), gr.update(), h, "chat", s
            ),
            inputs=[session_state, chatbot],
            outputs=[chat_view, report_view, report_display, download_btn, chatbot, view_state, session_state]
        )
        
        # Chat drawer toggle
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
        
        # New analysis
        new_analysis_btn.click(
            fn=reset_to_new_analysis,
            inputs=[session_state],
            outputs=[
                session_state,
                chatbot,
                msg_input,
                chat_view,
                report_view,
                chat_drawer,
                chat_history_display,
                view_state,
                image_input,
                upload_status
            ]
        )

    return demo

def launch_gradio():
    demo = create_gradio_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)

if __name__ == "__main__":
    launch_gradio()