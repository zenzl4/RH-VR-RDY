import gradio as gr
from utils.config import Config
from utils.logging_setup import logger

# Example function for chatbot interaction
def chat(message, chatbot):
    response = f"Response to: {message}"  # Example response
    chatbot.append(("User", message))  # Add user message to the chat
    chatbot.append(("Bot", response))  # Add bot response to the chat
    return chatbot, message  # Return updated chat and reset message input

# Function to clear chat
def clear_chat():
    return [], ""  # Clear the chat and reset message input

# Function to export chat data to a JSON file
import json
import os

def export_results_to_json(chatbot):
    # Prepare data for export (example: converting chatbot history to a JSON format)
    chat_history = [{"role": role, "message": msg} for role, msg in chatbot]
    output_dir = Config.OUTPUT_DIR
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    export_file = os.path.join(output_dir, "chat_history.json")
    with open(export_file, 'w') as f:
        json.dump(chat_history, f, indent=4)
    
    return f"Chat history exported to {export_file}"

# Initialize the Gradio interface
with gr.Blocks() as demo:
    chatbot = gr.Chatbot(label="Chatbot")
    msg = gr.Textbox(label="Message", placeholder="Type your message here...")
    
    # Buttons for clear and export actions
    clear_btn = gr.Button("Clear Chat")
    export_btn = gr.Button("Export Chat History")

    # Set up button actions
    msg.submit(chat, inputs=[msg, chatbot], outputs=[chatbot, msg])  # When message is submitted
    clear_btn.click(clear_chat, outputs=[chatbot, msg])  # When clear button is clicked
    export_btn.click(export_results_to_json, inputs=[chatbot], outputs=[chatbot])  # When export button is clicked

# Launch the Gradio interface with configurations from Config class
if __name__ == "__main__":
    demo.launch(server_name=Config.GRADIO_HOST, server_port=Config.GRADIO_PORT, share=True)
