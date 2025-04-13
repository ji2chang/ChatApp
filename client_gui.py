import re
from collections import defaultdict
import dearpygui.dearpygui as dpg
import ChatApp

current_chat_with = None
chat_history = defaultdict(list)
api = None

def send_friend_request():
    username = dpg.get_value("friend_request_input")
    if username:
        response = api.add_friend(username)
        if response["status"] == "success":
            dpg.set_value("friend_request_status", f"Friend request sent to {username}!")
            api.get_friends()
            update_user_list()
        else:
            dpg.set_value("friend_request_status", f"Error: {response.get('message', 'Failed to send request')}")
        dpg.set_value("friend_request_input", "")  # Clear input box

# 服务器地址配置回调
def server_config_callback():
    global api
    address = dpg.get_value("server_address_input")

    if not address:
        dpg.set_value("server_config_status", "Error: Server address cannot be empty!")
        return
    pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    # 简单验证地址格式 (IP:Port 或 Domain:Port)
    if not re.match(pattern, address):
        dpg.set_value("server_config_status", "Error: Format must be IP")
        return

    api = ChatApp.APIClient(server_ip=address)
    dpg.delete_item("server_config_window")
    create_login_interface()


def update_user_list():
    """Refresh the user list display in the left sidebar"""
    # First, delete the existing user list items
    if dpg.does_item_exist("user_list_group"):
        dpg.delete_item("user_list_group")

    # Then recreate the user list
    with dpg.group(parent="chat_window", tag="user_list_group"):
        dpg.add_text(f"Hello, {api.current_user['nickname']}!")
        dpg.add_separator()

        # Add friend section
        dpg.add_text("Add Friend:")
        with dpg.group(horizontal=True):
            dpg.add_input_text(tag="friend_request_input", width=120)
            dpg.add_button(label="Add", callback=send_friend_request, width=50)
        dpg.add_text(tag="friend_request_status", color=[255, 255, 0])
        dpg.add_separator()

        dpg.add_text("Online Users:")

        for user in api.friends:
            status_color = (0, 255, 0) if api.friends[user]["info"]["online"] else (150, 150, 150)
            with dpg.group(horizontal=True):
                dpg.add_text("● ", color=status_color)
                dpg.add_button(
                    label=api.friends[user]["info"]["nickname"],
                    callback=select_user,
                    user_data=api.friends[user]["username"],
                    width=150
                )

# 创建服务器配置界面
def create_server_config_interface():
    with dpg.window(label="Server Configuration", tag="server_config_window", width=400, height=300):
        dpg.add_text("Welcome to Chat App", pos=[120, 30])
        dpg.add_text("Please enter server address:", pos=[50, 80])

        # 默认值可以是你的测试服务器地址
        dpg.add_input_text(
            tag="server_address_input",
            default_value="127.0.0.1",
            width=200,
            pos=[120, 120]
        )

        dpg.add_text("Format: IP", pos=[50, 150])
        dpg.add_button(
            label="Connect",
            callback=server_config_callback,
            pos=[150, 200],
            width=100
        )

        dpg.add_text(tag="server_config_status", pos=[50, 250], color=[255, 0, 0])
# Login verification function
def login_callback():
    username = dpg.get_value("username_input")
    password = dpg.get_value("password_input")

    response = api.login(username, password)
    if response["status"] == "success":
        dpg.set_value("login_status", "Login successful, redirecting...")
        dpg.delete_item("login_window")  # Remove login window
        create_chat_interface()  # Create chat interface
    else:
        dpg.set_value("login_status", "Error: Incorrect username or password!")

# Message sending function
def send_message():
    message = dpg.get_value("message_input")
    if message:
        chat_history[current_chat_with].append(message)
        api.chat(current_chat_with, message)
        dpg.set_value("message_input", "")  # Clear input box

def select_user(sender, app_data, user_data):
    global current_chat_with
    current_chat_with = user_data
    nickname = api.get_user_info(current_chat_with)["info"]["nickname"]
    dpg.set_value("current_chat_label", f"Chatting with {nickname}")
    update_chat_display()

# Update chat display
def update_chat_display():
    if not current_chat_with:
        return
    history = "\n".join(chat_history[current_chat_with])
    dpg.set_value("chat_history", history or "No messages yet")
    dpg.set_y_scroll("chat_history_container", dpg.get_y_scroll_max("chat_history_container"))

# Create chat interface
def create_chat_interface():
    api.get_friends()
    with dpg.window(label="Chat Room", tag="chat_window", width=1000, height=700):
        # Left sidebar - user list
        update_user_list()

        # Right side - chat area
        with dpg.group(pos=(210, 10)):
            dpg.add_text(tag="current_chat_label", default_value="Please select a chat partner")
            dpg.add_separator()

            # Chat history area
            with dpg.child_window(
                    tag="chat_history_container",
                    width=780,
                    height=500,
                    horizontal_scrollbar=True
            ):
                dpg.add_input_text(
                    tag="chat_history",
                    multiline=True,
                    width=760,
                    height=490,
                    readonly=True
                )

            # Message input area
            with dpg.group(horizontal=True):
                dpg.add_input_text(tag="message_input", width=700)
                dpg.add_button(label="Send", callback=send_message)

            # Settings area
            with dpg.collapsing_header(label="Display Settings"):
                dpg.add_checkbox(label="Show timestamp", tag="timestamp_checkbox", default_value=True)
                dpg.add_text("Time format:")
                dpg.add_input_text(tag="time_display", default_value="[%H:%M]")

# Create login interface
def create_login_interface():
    with dpg.window(label="Login Window", tag="login_window", width=400, height=300):
        dpg.add_text("Welcome", pos=[150, 30])

        # Username input
        dpg.add_text("Username:", pos=[50, 80])
        dpg.add_input_text(tag="username_input", width=200, pos=[120, 80])

        # Password input
        dpg.add_text("Password:", pos=[50, 120])
        dpg.add_input_text(tag="password_input", password=True, width=200, pos=[120, 120])

        # Login button
        dpg.add_button(label="Login", callback=login_callback, pos=[150, 170], width=100)

        # Login status
        dpg.add_text(tag="login_status", pos=[50, 220], color=[255, 0, 0])

# Initialization
if __name__ == "__main__":
    dpg.create_context()
    dpg.create_viewport(title='Chat Application', width=800, height=600)
    create_server_config_interface()

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()