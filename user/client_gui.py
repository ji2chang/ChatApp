import re
import threading
import time

import dearpygui.dearpygui as dpg
import ChatApp

current_chat_with = None
api = ChatApp.APIClient()
DEFAULT_GRAY = [37,37,39]
message_cnt = 0
def center_window(window_tag, width, height):
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()

    x_pos = (viewport_width - width) // 2
    y_pos = (viewport_height - height) // 2

    dpg.configure_item(window_tag, pos=(x_pos, y_pos), width=width, height=height)

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

    api.connect_server(address)
    dpg.delete_item("server_config_window")
    create_login_interface()


def update_user_list():
    if not dpg.does_item_exist("chat_window"):
        return
    """Refresh the user list display in the left sidebar"""
    # First, delete the existing user list items
    if dpg.does_item_exist("user_list_group"):
        dpg.delete_item("user_list_group")
    api.get_friends()
    # Then recreate the user list
    with dpg.group(parent="left_panel", tag="user_list_group"):
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
                with dpg.drawlist(width=20, height=20):
                    dpg.draw_circle(
                        center=(10, 10),
                        radius=5,
                        color=status_color,
                        fill=status_color
                    )
                dpg.add_button(
                    label=api.friends[user]["info"]["nickname"],
                    callback=select_user,
                    user_data=api.friends[user]["username"],
                    width=150
                )

# Login verification function
def login_callback():
    username = dpg.get_value("username_input")
    password = dpg.get_value("password_input")

    response = api.login(username, password)
    if response["status"] == "success":
        dpg.set_value("login_status", "Login successful, redirecting...")
        dpg.delete_item("login_window")
        create_chat_interface()
    else:
        dpg.set_value("login_status", "Error: Incorrect username or password!")

def register_callback():
    username = dpg.get_value("reg_username_input")
    password = dpg.get_value("reg_password_input")
    confirm_password = dpg.get_value("reg_confirm_password_input")
    nickname = dpg.get_value("reg_nickname_input")
    if not password == confirm_password:
        dpg.set_value("register_status", "Error: password do not match!")
        return
    response = api.register(username, password, {"nickname": nickname})
    if response["status"] == "success":
        dpg.set_value("register_status", "Registration successful, redirecting...")
        create_login_interface()
    else:
        dpg.set_value("register_status", "Error: register failed!")

# Message sending function
def send_message():
    message = dpg.get_value("message_input")
    if message:
        api.chat(current_chat_with, message)
        dpg.set_value("message_input", "")
        update_chat_display()


def select_user(sender, app_data, user_data):
    global current_chat_with
    current_chat_with = user_data
    nickname = api.get_user_info(current_chat_with)["info"]["nickname"]
    dpg.set_value("current_chat_label", f"Chatting with {nickname}")
    update_chat_display()


# Update chat display
def update_chat_display():
    if not current_chat_with or not dpg.does_item_exist("chat_window"):
        return
    history = "\n".join(api.get_messages(current_chat_with))
    dpg.set_value("chat_history", history or "No messages yet")
    dpg.set_y_scroll("chat_history_container", dpg.get_y_scroll_max("chat_history_container"))

# 创建服务器配置界面
def create_server_config_interface():
    with dpg.window(label="Server Configuration", tag="server_config_window", width=400, height=300, no_resize=True,
                    no_move=True, no_collapse=True,no_title_bar=True):
        dpg.add_text("Welcome to Chat App", pos=[120, 30])
        dpg.add_text("Please enter server address:", pos=[50, 80])

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
    update_window()

# Create chat interface
def create_chat_interface():
    api.get_friends()
    with dpg.window(label="Chat Room", tag="chat_window", width=1000, height=700, no_resize=True, no_move=True,
                    no_collapse=True,no_title_bar=True):
        # Left sidebar - user list
        with dpg.child_window(tag="left_panel", width=200, height=680, pos=(5, 5)):
            update_user_list()

        # Right side - chat area
        with dpg.group(pos=(210, 5)):
            dpg.add_text(tag="current_chat_label", default_value="Please select a chat partner")
            dpg.add_separator()

            # Chat history area
            with dpg.child_window(
                    tag="chat_history_container",
                    width=780,
                    height=600,
                    horizontal_scrollbar=True
            ):
                dpg.add_input_text(
                    tag="chat_history",
                    multiline=True,
                    width=760,
                    height=590,
                    readonly=True
                )

            # Message input area
            with dpg.group(horizontal=True):
                dpg.add_input_text(tag="message_input", width=700)
                dpg.add_button(label="Send", callback=send_message)
    update_window()


# Create login interface
def create_login_interface():
    # First delete any existing windows to avoid duplicates
    if dpg.does_item_exist("login_window"):
        dpg.delete_item("login_window")
    if dpg.does_item_exist("register_window"):
        dpg.delete_item("register_window")

    with dpg.window(label="Login Window", tag="login_window", width=400, height=300,
                    no_resize=True, no_move=True, no_collapse=True, no_title_bar=True):
        dpg.add_text("Welcome", pos=[150, 30])

        # Username input
        dpg.add_text("Username:", pos=[50, 80])
        dpg.add_input_text(tag="username_input", width=200, pos=[120, 80])

        # Password input
        dpg.add_text("Password:", pos=[50, 120])
        dpg.add_input_text(tag="password_input", password=True, width=200, pos=[120, 120])

        # Login button
        dpg.add_button(label="Login", callback=login_callback, pos=[150, 170], width=100)

        # Register button - switches to register interface
        dpg.add_button(label="Register Account", callback=create_register_interface,
                       pos=[260, 270], width=130)

        # Login status
        dpg.add_text(tag="login_status", pos=[50, 250], color=[255, 0, 0])
    update_window()


def create_register_interface():
    # First delete any existing windows to avoid duplicates
    if dpg.does_item_exist("register_window"):
        dpg.delete_item("register_window")
    if dpg.does_item_exist("login_window"):
        dpg.delete_item("login_window")

    with dpg.window(label="Register Window", tag="register_window", width=400, height=350,
                    no_resize=True, no_move=True, no_collapse=True, no_title_bar=True):
        dpg.add_text("Register", pos=[150, 30])

        # Username input
        dpg.add_text("Username:", pos=[50, 80])
        dpg.add_input_text(tag="reg_username_input", width=200, pos=[140, 80])

        # Password input
        dpg.add_text("Password:", pos=[50, 120])
        dpg.add_input_text(tag="reg_password_input", password=True, width=200, pos=[140, 120])

        # Confirm Password input
        dpg.add_text("Confirm \nPassword:", pos=[50, 155])
        dpg.add_input_text(tag="reg_confirm_password_input", password=True, width=200, pos=[140, 160])

        # nickname input
        dpg.add_text("Nickname:", pos=[50, 200])
        dpg.add_input_text(tag="reg_nickname_input", width=200, pos=[140, 200])

        # Register button
        dpg.add_button(label="Register", callback=register_callback, pos=[150, 240], width=100)

        # Back to login button
        dpg.add_button(label="Back to Login", callback=create_login_interface,
                       pos=[290, 270], width=100)

        # Registration status
        dpg.add_text(tag="register_status", pos=[50, 320], color=[255, 0, 0])
    update_window()

# Viewport resize handler
def update_window():
    if dpg.does_item_exist("server_config_window"):
        center_window("server_config_window",400,300)
    elif dpg.does_item_exist("login_window"):
        center_window("login_window",400,300)
    elif dpg.does_item_exist("chat_window"):
        center_window("chat_window", 1000, 700)
    elif dpg.does_item_exist("register_window"):
        center_window("register_window", 400, 350)

# Initialization
if __name__ == "__main__":
    dpg.create_context()

    viewport_width = 800
    viewport_height = 600
    dpg.create_viewport(title='Chat Application', width=viewport_width, height=viewport_height)

    dpg.set_viewport_clear_color(DEFAULT_GRAY)
    dpg.set_viewport_min_width(1000)
    dpg.set_viewport_min_height(700)
    dpg.set_viewport_max_width(1200)
    dpg.set_viewport_max_height(800)
    with dpg.theme() as window_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 3.0)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (255,255,255,100))
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, DEFAULT_GRAY)

    def _daemon():
        global message_cnt
        while True:
            cnt = api.tot_update
            if not cnt == message_cnt:
                update_chat_display()
                update_user_list()
                message_cnt = cnt
            time.sleep(1)

    updater = threading.Thread(target=_daemon,daemon=True)
    updater.start()
    dpg.bind_theme(window_theme)

    create_server_config_interface()
    dpg.set_exit_callback(api.close)
    dpg.set_viewport_resize_callback(update_window)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()