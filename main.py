"""
Montreal Travel Companion - Android App Client
Production UI with Real API Integration + WebSocket Notifications
RESPONSIVE VERSION - Adapts to all screen sizes
"""

import os
import logging
import threading
import json
from datetime import datetime
import requests

# --- 1. Environment Configuration ---
from kivy.config import Config

# Use native keyboard on mobile devices (must be set before importing other kivy modules)
Config.set('kivy', 'keyboard_mode', '')  # Empty string = use system keyboard
Config.set('kivy', 'keyboard_layout', '')
Config.set('kivy', 'log_level', 'info')

# Desktop-specific settings
from kivy.utils import platform
if platform not in ('android', 'ios'):
    Config.set('kivy', 'keyboard_mode', 'systemanddock')
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

# --- 2. Critical Font Fix (Robust Version) ---
from kivy.core.text import LabelBase
try:
    import kivymd
    base_path = os.path.dirname(kivymd.__file__)
    
    possible_paths = [
        os.path.join(base_path, 'fonts', 'materialdesignicons-webfont.ttf'),
        os.path.join(base_path, 'fonts', 'MaterialIcons-Regular.ttf'),
    ]
    
    font_path = None
    for path in possible_paths:
        if os.path.exists(path):
            font_path = path
            break
            
    if font_path:
        LabelBase.register(name='MaterialIcons', fn_regular=font_path)
        LabelBase.register(name='Icon', fn_regular=font_path)
    else:
        print(f"[WARNING] Could not find icon font in {base_path}/fonts/")

except ImportError:
    print("[CRITICAL] KivyMD is not installed. Please run: pip install kivymd")

# --- 3. Imports ---
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDRectangleFlatButton, MDIconButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.dialog import MDDialog
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.widget import MDWidget
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.snackbar import Snackbar

from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, DictProperty, ListProperty, BooleanProperty
from kivy.utils import platform
from kivy.app import App

# --- 4. Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GPS Support
try:
    from plyer import gps
    if platform == 'android':
        from android.permissions import request_permissions, Permission
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False

# WebSocket Support
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("websocket-client not installed. Install with: pip install websocket-client")

# --- 5. Responsive Window Size (Desktop Testing Only) ---
# On Android, the window automatically uses the full screen
if platform not in ('android', 'ios'):
    Window.size = (400, 800)
else:
    # On mobile, configure soft keyboard behavior
    # 'pan' mode moves the window up when keyboard appears
    # 'below_target' resizes the window to fit above keyboard
    from kivy.core.window import Window
    Window.softinput_mode = 'below_target'

# API URL Configuration
# ============================================================
# For LOCAL TESTING (desktop):
# API_BASE_URL = "http://localhost:8000"
# WS_BASE_URL = "ws://localhost:8000"

# For ANDROID EMULATOR:
API_BASE_URL = "http://10.0.2.2:8000"
WS_BASE_URL = "ws://10.0.2.2:8000"

# For PHYSICAL ANDROID DEVICE (replace with your Windows IP):
# 1. Open PowerShell on Windows and run: ipconfig
# 2. Find your Wi-Fi adapter's IPv4 Address (e.g., 192.168.1.105)
# 3. Replace the IP below with your IP
#API_BASE_URL = "http://192.168.2.18:8000"
#WS_BASE_URL = "ws://192.168.2.18:8000"
# ============================================================


# --- 6. Responsive Helper Functions ---

def get_responsive_font_size(base_size):
    """Calculate responsive font size based on screen width."""
    width = Window.width
    if width < 360:
        return sp(base_size * 0.85)
    elif width < 400:
        return sp(base_size * 0.95)
    elif width > 600:
        return sp(base_size * 1.1)
    return sp(base_size)

def get_responsive_padding():
    """Calculate responsive padding based on screen width."""
    width = Window.width
    if width < 360:
        return dp(10)
    elif width < 400:
        return dp(12)
    elif width > 600:
        return dp(20)
    return dp(15)

def get_responsive_spacing():
    """Calculate responsive spacing based on screen width."""
    width = Window.width
    if width < 360:
        return dp(8)
    elif width < 400:
        return dp(10)
    elif width > 600:
        return dp(15)
    return dp(10)


# --- 7. WebSocket Notification Client ---

class NotificationClient:
    """WebSocket client for receiving real-time notifications from server."""
    
    def __init__(self, user_id, on_notification_callback, on_connection_change_callback=None):
        self.user_id = user_id
        self.on_notification = on_notification_callback
        self.on_connection_change = on_connection_change_callback
        self.ws = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 3
        self._stop_flag = False
        self._thread = None
    
    def connect(self):
        """Start WebSocket connection in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("WebSocket thread already running")
            return
        
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run_websocket, daemon=True)
        self._thread.start()
        logger.info(f"WebSocket connection thread started for user {self.user_id}")
    
    def disconnect(self):
        """Stop WebSocket connection."""
        self._stop_flag = True
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        self.connected = False
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(False), 0)
    
    def _run_websocket(self):
        """Main WebSocket loop running in background thread."""
        while not self._stop_flag and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                ws_url = f"{WS_BASE_URL}/ws/notifications/{self.user_id}"
                logger.info(f"Connecting to WebSocket: {ws_url}")
                
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
                
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
            
            if not self._stop_flag:
                self.reconnect_attempts += 1
                logger.info(f"Reconnecting in {self.reconnect_delay}s... (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
                import time
                time.sleep(self.reconnect_delay)
        
        logger.info("WebSocket thread stopped")
    
    def _on_open(self, ws):
        """Called when WebSocket connection is established."""
        self.connected = True
        self.reconnect_attempts = 0
        logger.info(f"WebSocket connected for user {self.user_id}")
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(True), 0)
    
    def _on_message(self, ws, message):
        """Called when a message is received from server."""
        try:
            data = json.loads(message)
            logger.info(f"Notification received: {data.get('type', 'unknown')}")
            Clock.schedule_once(lambda dt: self.on_notification(data), 0)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse notification: {e}")
    
    def _on_error(self, ws, error):
        """Called when WebSocket error occurs."""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Called when WebSocket connection is closed."""
        self.connected = False
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(False), 0)


# --- 8. Responsive UI Components ---

class ResponsiveCard(MDCard):
    """Responsive Card Component that adapts to screen size."""
    
    def __init__(self, title="", show_title=True, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.adaptive_height = True
        self.size_hint_x = 1
        self.size_hint_y = None
        self.padding = get_responsive_padding()
        self.spacing = get_responsive_spacing()
        self.radius = [dp(12)]
        self.elevation = 2
        self.md_bg_color = [1, 1, 1, 1]
        
        self.bind(minimum_height=self.setter('height'))
        
        if show_title and title:
            self.add_widget(MDLabel(
                text=title,
                font_style='H6',
                font_size=sp(16),
                theme_text_color='Primary',
                size_hint_y=None,
                height=dp(30),
                halign='left',
                adaptive_height=True
            ))


class NotificationBanner(MDCard):
    """A responsive notification banner that appears at the top of the screen."""
    
    def __init__(self, title, message, notif_type="info", on_dismiss=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint = (0.95, None)
        self.pos_hint = {'center_x': 0.5, 'top': 0.98}
        self.radius = [dp(12)]
        self.elevation = 4
        self.on_dismiss_callback = on_dismiss
        
        # Responsive height
        self.height = dp(70) if Window.width < 400 else dp(80)
        
        # Set color based on notification type
        type_colors = {
            "location_change": (0.2, 0.6, 0.9, 1),
            "weather_change": (0.9, 0.7, 0.2, 1),
            "time_period_change": (0.5, 0.3, 0.7, 1),
            "meal_time": (0.3, 0.7, 0.4, 1),
            "temperature_change": (0.9, 0.4, 0.3, 1),
            "preferences_updated": (0.4, 0.7, 0.9, 1),
            "connection_established": (0.3, 0.7, 0.4, 1),
            "info": (0.5, 0.5, 0.5, 1),
        }
        self.md_bg_color = type_colors.get(notif_type, type_colors["info"])
        
        # Icon mapping
        icon_map = {
            "location_change": "📍",
            "weather_change": "🌤️",
            "time_period_change": "🕐",
            "meal_time": "🍽️",
            "temperature_change": "🌡️",
            "preferences_updated": "⚙️",
            "connection_established": "✅",
        }
        icon = icon_map.get(notif_type, "🔔")
        
        # Content layout
        padding = dp(8) if Window.width < 400 else dp(10)
        content = MDBoxLayout(orientation='horizontal', padding=padding, spacing=dp(8))
        
        # Icon
        content.add_widget(MDLabel(
            text=icon,
            font_size=sp(24),
            size_hint_x=None,
            width=dp(35),
            halign='center',
            valign='center'
        ))
        
        # Text content
        text_box = MDBoxLayout(orientation='vertical', spacing=dp(2))
        
        # Truncate message based on screen width
        max_chars = 60 if Window.width < 400 else 80
        truncated_msg = message[:max_chars] + "..." if len(message) > max_chars else message
        
        text_box.add_widget(MDLabel(
            text=title,
            font_size=sp(14),
            bold=True,
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(22)
        ))
        text_box.add_widget(MDLabel(
            text=truncated_msg,
            font_size=sp(12),
            theme_text_color='Custom',
            text_color=(1, 1, 1, 0.9),
            size_hint_y=None,
            height=dp(30)
        ))
        content.add_widget(text_box)
        
        # Close button
        close_btn = MDIconButton(
            icon="close",
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            size_hint_x=None,
            width=dp(35),
            on_release=self.dismiss
        )
        content.add_widget(close_btn)
        
        self.add_widget(content)
    
    def dismiss(self, *args):
        """Animate and remove the banner."""
        from kivy.animation import Animation
        anim = Animation(opacity=0, duration=0.3)
        anim.bind(on_complete=lambda *x: self._remove())
        anim.start(self)
    
    def _remove(self):
        if self.parent:
            self.parent.remove_widget(self)
        if self.on_dismiss_callback:
            self.on_dismiss_callback()


# --- 9. Screen Classes ---

class WelcomeScreen(MDScreen):
    """Responsive landing screen with branding."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(
            orientation='vertical',
            padding=get_responsive_padding() * 2,
            spacing=get_responsive_spacing() * 2,
        )
        
        # Set background color after app is running
        Clock.schedule_once(lambda x: setattr(layout, 'md_bg_color', 
            MDApp.get_running_app().theme_cls.primary_color if MDApp.get_running_app() else (0.3, 0.3, 0.8, 1)), 0)

        # Top spacer
        layout.add_widget(MDWidget(size_hint_y=0.15))

        # App icon (using emoji for compatibility)
        icon_size = sp(70) if Window.width < 400 else sp(90)
        layout.add_widget(MDLabel(
            text='🗺️',
            halign='center',
            font_size=icon_size,
            size_hint_y=None,
            height=dp(100)
        ))
        
        # App title - responsive font size
        title_size = sp(28) if Window.width < 400 else sp(34)
        layout.add_widget(MDLabel(
            text='Montreal\nTravel Companion',
            font_size=title_size,
            bold=True,
            halign='center',
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(90)
        ))
        
        # Subtitle
        layout.add_widget(MDLabel(
            text='Your AI-powered travel guide',
            font_size=sp(14),
            halign='center',
            theme_text_color='Custom',
            text_color=(1, 1, 1, 0.8),
            size_hint_y=None,
            height=dp(30)
        ))
        
        # Middle spacer
        layout.add_widget(MDWidget(size_hint_y=0.2))
        
        # Start button - responsive width
        btn_width = 0.9 if Window.width < 400 else 0.75
        btn = MDRaisedButton(
            text='START EXPLORING',
            font_size=sp(16),
            size_hint_x=btn_width,
            size_hint_y=None,
            height=dp(50),
            pos_hint={'center_x': 0.5},
            elevation=4,
            on_release=self.go_to_preferences
        )
        Clock.schedule_once(lambda x: setattr(btn, 'md_bg_color', 
            MDApp.get_running_app().theme_cls.accent_color if MDApp.get_running_app() else (1, 0.4, 0.7, 1)), 0)
        
        layout.add_widget(btn)
        
        # Bottom spacer
        layout.add_widget(MDWidget(size_hint_y=0.15))
        
        self.add_widget(layout)

    def go_to_preferences(self, instance):
        self.manager.transition.direction = 'left'
        self.manager.current = 'preferences'


class PreferencesScreen(MDScreen):
    """Responsive User Preference Input Screen."""
    activity_type = StringProperty("outdoor")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Toolbar
        self.toolbar = MDTopAppBar(
            title="Your Preferences",
            elevation=4,
            pos_hint={"top": 1},
            left_action_items=[["arrow-left", lambda x: self.go_back()]]
        )
        layout.add_widget(self.toolbar)
        
        # Scrollable content
        scroll = MDScrollView()
        content = MDBoxLayout(
            orientation='vertical', 
            spacing=get_responsive_spacing(),
            padding=get_responsive_padding(),
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter('height'))
        
        # 1. User ID Card
        card_id = ResponsiveCard(title="👤 Profile")
        self.user_id_input = MDTextField(
            hint_text="User ID (e.g., traveler1)",
            mode="rectangle",
            text="traveler1",
            size_hint_x=1
        )
        card_id.add_widget(self.user_id_input)
        content.add_widget(card_id)
        
        # 2. Meal Times Card
        card_meals = ResponsiveCard(title="🍽️ Meal Times (HH:MM)")
        
        # Responsive grid - 3 columns on wide screens, 1 on narrow
        cols = 3 if Window.width >= 400 else 1
        meals_grid = MDGridLayout(
            cols=cols, 
            spacing=get_responsive_spacing(), 
            size_hint_y=None,
            adaptive_height=True
        )
        meals_grid.bind(minimum_height=meals_grid.setter('height'))

        self.input_breakfast = MDTextField(
            text="08:00", 
            hint_text="Breakfast", 
            mode="rectangle",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(48)
        )
        self.input_lunch = MDTextField(
            text="12:00", 
            hint_text="Lunch", 
            mode="rectangle",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(48)
        )
        self.input_dinner = MDTextField(
            text="19:00", 
            hint_text="Dinner", 
            mode="rectangle",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(48)
        )

        meals_grid.add_widget(self.input_breakfast)
        meals_grid.add_widget(self.input_lunch)
        meals_grid.add_widget(self.input_dinner)
        
        card_meals.add_widget(meals_grid)
        content.add_widget(card_meals)

        # 3. Activity Type Card
        card_act = ResponsiveCard(title="🎯 Preferred Vibe")
        btn_box = MDBoxLayout(
            spacing=get_responsive_spacing(), 
            size_hint_y=None, 
            height=dp(50)
        )
        
        self.btn_indoor = MDRectangleFlatButton(
            text="🏠 Indoor", 
            size_hint_x=0.5,
            on_release=lambda x: self.set_activity("indoor")
        )
        self.btn_outdoor = MDRaisedButton(
            text="🌳 Outdoor", 
            size_hint_x=0.5,
            on_release=lambda x: self.set_activity("outdoor")
        )
        
        btn_box.add_widget(self.btn_indoor)
        btn_box.add_widget(self.btn_outdoor)
        card_act.add_widget(btn_box)
        content.add_widget(card_act)
        
        # 4. Cuisines Card
        card_food = ResponsiveCard(title="🍴 Favorite Cuisines")
        self.cuisines = ['Italian', 'French', 'Japanese', 'Mexican', 'Burgers', 'Cafe', 'Seafood']
        self.cuisine_checks = {}
        
        # Responsive columns - 2 on wide, 1 on narrow
        cuisine_cols = 2 if Window.width >= 360 else 1
        grid = MDGridLayout(
            cols=cuisine_cols, 
            spacing=get_responsive_spacing(), 
            size_hint_y=None,
            adaptive_height=True
        )
        grid.bind(minimum_height=grid.setter('height'))
        
        cuisine_emojis = {
            'Italian': '🍝', 'French': '🥐', 'Japanese': '🍣', 
            'Mexican': '🌮', 'Burgers': '🍔', 'Cafe': '☕', 'Seafood': '🦐'
        }
        
        for c in self.cuisines:
            row = MDBoxLayout(size_hint_y=None, height=dp(45))
            chk = MDCheckbox(
                size_hint=(None, None), 
                size=(dp(45), dp(45))
            )
            if c == 'French':
                chk.active = True
            self.cuisine_checks[c] = chk
            row.add_widget(chk)
            row.add_widget(MDLabel(
                text=f"{cuisine_emojis.get(c, '')} {c}", 
                theme_text_color="Primary",
                font_size=sp(14)
            ))
            grid.add_widget(row)
            
        card_food.add_widget(grid)
        content.add_widget(card_food)
        
        # Save Button
        save_btn = MDRaisedButton(
            text="SAVE & CONTINUE",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(50),
            md_bg_color=(0.2, 0.7, 0.3, 1),
            font_size=sp(16),
            on_release=self.save_prefs_thread
        )
        content.add_widget(save_btn)
        
        # Bottom padding
        content.add_widget(MDWidget(size_hint_y=None, height=dp(30)))
        
        scroll.add_widget(content)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def set_activity(self, mode):
        self.activity_type = mode
        theme = MDApp.get_running_app().theme_cls
        if mode == "indoor":
            self.btn_indoor.md_bg_color = theme.primary_color
            self.btn_indoor.text_color = (1, 1, 1, 1)
            self.btn_outdoor.md_bg_color = (0, 0, 0, 0)
            self.btn_outdoor.text_color = theme.primary_color
        else:
            self.btn_outdoor.md_bg_color = theme.primary_color
            self.btn_outdoor.text_color = (1, 1, 1, 1)
            self.btn_indoor.md_bg_color = (0, 0, 0, 0)
            self.btn_indoor.text_color = theme.primary_color

    def go_back(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'welcome'

    def save_prefs_thread(self, instance):
        if not self.user_id_input.text.strip():
            dialog = MDDialog(
                title="Error", 
                text="User ID cannot be empty",
                buttons=[MDRectangleFlatButton(text="OK", on_release=lambda x: dialog.dismiss())]
            )
            dialog.open()
            return
        
        self.show_loading()
        threading.Thread(target=self.save_prefs_api, daemon=True).start()

    def save_prefs_api(self):
        user_id = self.user_id_input.text.strip()
        
        meal_times = {
            "breakfast": self.input_breakfast.text.strip(),
            "lunch": self.input_lunch.text.strip(),
            "dinner": self.input_dinner.text.strip()
        }
        
        payload = {
            "user_id": user_id,
            "activity_type": self.activity_type,
            "preferred_cuisines": [k for k, v in self.cuisine_checks.items() if v.active],
            "meal_times": meal_times
        }
        
        app = App.get_running_app()
        app.user_id = user_id
        app.preferences = payload
        
        try:
            response = requests.post(f"{API_BASE_URL}/api/preferences", json=payload, timeout=5)
            if response.status_code == 200:
                Clock.schedule_once(self.on_save_success, 0)
            else:
                Clock.schedule_once(lambda dt: self.on_save_error(f"Server Error: {response.status_code}"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.on_save_error(str(e)), 0)

    def show_loading(self):
        self.dialog = MDDialog(
            text="Connecting to server...",
            type="custom",
            content_cls=MDProgressBar(type="indeterminate"),
        )
        self.dialog.open()

    def on_save_success(self, dt):
        if hasattr(self, 'dialog'):
            self.dialog.dismiss()
        self.manager.transition.direction = 'left'
        self.manager.current = 'main'
        
    def on_save_error(self, error_msg):
        if hasattr(self, 'dialog'):
            self.dialog.dismiss()
        
        dialog = MDDialog(
            title="Connection Failed", 
            text=f"Could not save to API.\n{error_msg}\n\nEnsure server.py is running.",
            buttons=[MDRectangleFlatButton(text="OK", on_release=lambda x: dialog.dismiss())]
        )
        dialog.open()


class MainScreen(MDScreen):
    """Responsive Dashboard showing Context and Recommendations with Real-Time Notifications."""
    
    notification_count = NumericProperty(0)
    ws_connected = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.notification_client = None
        self.current_banner = None
        self.notification_history = []
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Toolbar
        self.toolbar = MDTopAppBar(
            title="Explore Montreal",
            right_action_items=[
                ["refresh", lambda x: self.refresh_data()],
                ["bell-outline", lambda x: self.show_notification_history()],
                ["cog", lambda x: self.go_to_settings()]
            ],
            elevation=4
        )
        layout.add_widget(self.toolbar)
        
        # Connection Status Bar
        self.status_bar = MDBoxLayout(
            size_hint_y=None,
            height=dp(25),
            md_bg_color=(0.95, 0.95, 0.95, 1),
            padding=(get_responsive_padding(), 0)
        )
        self.status_label = MDLabel(
            text="● Disconnected",
            font_size=sp(11),
            theme_text_color="Custom",
            text_color=(0.7, 0.2, 0.2, 1),
            valign='center'
        )
        self.status_bar.add_widget(self.status_label)
        layout.add_widget(self.status_bar)
        
        # Scrollable Content
        self.scroll = MDScrollView()
        self.content = MDBoxLayout(
            orientation='vertical', 
            spacing=get_responsive_spacing(), 
            padding=get_responsive_padding(), 
            size_hint_y=None
        )
        self.content.bind(minimum_height=self.content.setter('height'))
        
        # Context Card
        self.context_card = ResponsiveCard(title="📍 Current Context")
        self.context_label = MDLabel(
            text="Loading context...", 
            theme_text_color="Secondary", 
            size_hint_y=None, 
            height=dp(50),
            font_size=sp(14)
        )
        self.context_card.add_widget(self.context_label)
        self.content.add_widget(self.context_card)
        
        # Recommendations Header
        self.content.add_widget(MDLabel(
            text="🎯 Recommended for You", 
            font_size=sp(18),
            bold=True,
            size_hint_y=None, 
            height=dp(35)
        ))
        
        # Recommendations Container
        self.recs_box = MDBoxLayout(
            orientation='vertical', 
            spacing=get_responsive_spacing(), 
            size_hint_y=None
        )
        self.recs_box.bind(minimum_height=self.recs_box.setter('height'))
        self.content.add_widget(self.recs_box)
        
        self.scroll.add_widget(self.content)
        layout.add_widget(self.scroll)
        self.add_widget(layout)

    def on_enter(self):
        """Called when screen is displayed."""
        app = App.get_running_app()
        
        if app.user_id and WEBSOCKET_AVAILABLE:
            self.start_notification_client()
        
        self.context_update_event = Clock.schedule_interval(self.send_context_update, 60)
        self.refresh_data()
    
    def on_leave(self):
        """Called when leaving screen."""
        if hasattr(self, 'context_update_event'):
            self.context_update_event.cancel()
    
    def start_notification_client(self):
        """Initialize and start WebSocket notification client."""
        app = App.get_running_app()
        
        if self.notification_client:
            self.notification_client.disconnect()
        
        if not WEBSOCKET_AVAILABLE:
            logger.warning("WebSocket not available, using polling fallback")
            return
        
        self.notification_client = NotificationClient(
            user_id=app.user_id,
            on_notification_callback=self.handle_notification,
            on_connection_change_callback=self.on_ws_connection_change
        )
        self.notification_client.connect()
    
    def on_ws_connection_change(self, connected):
        """Handle WebSocket connection status changes."""
        self.ws_connected = connected
        if connected:
            self.status_label.text = "● Connected (Live)"
            self.status_label.text_color = (0.2, 0.7, 0.2, 1)
            self.status_bar.md_bg_color = (0.92, 1, 0.92, 1)
        else:
            self.status_label.text = "● Disconnected"
            self.status_label.text_color = (0.7, 0.2, 0.2, 1)
            self.status_bar.md_bg_color = (1, 0.92, 0.92, 1)
    
    def handle_notification(self, notification):
        """Handle incoming notification from WebSocket."""
        notif_type = notification.get('type', 'info')
        title = notification.get('title', 'Notification')
        message = notification.get('message', '')
        
        logger.info(f"Handling notification: {title}")
        
        self.notification_history.append({
            'type': notif_type,
            'title': title,
            'message': message,
            'timestamp': notification.get('timestamp', datetime.now().isoformat())
        })
        
        if len(self.notification_history) > 50:
            self.notification_history = self.notification_history[-50:]
        
        self.notification_count = len(self.notification_history)
        self.update_bell_icon()
        
        if notif_type != 'connection_established' and notif_type != 'pong':
            self.show_notification_banner(title, message, notif_type)
            
            if notif_type in ['location_change', 'weather_change', 'preferences_updated', 'meal_time']:
                Clock.schedule_once(lambda dt: self.refresh_data(), 1)
    
    def show_notification_banner(self, title, message, notif_type="info"):
        """Display a notification banner at the top of the screen."""
        if self.current_banner and self.current_banner.parent:
            self.current_banner.parent.remove_widget(self.current_banner)
        
        self.current_banner = NotificationBanner(
            title=title,
            message=message,
            notif_type=notif_type,
            on_dismiss=lambda: setattr(self, 'current_banner', None)
        )
        
        self.add_widget(self.current_banner)
        Clock.schedule_once(lambda dt: self.current_banner.dismiss() if self.current_banner else None, 5)
    
    def update_bell_icon(self):
        """Update the bell icon to show notification count."""
        if self.notification_count > 0:
            self.toolbar.right_action_items[1] = ["bell", lambda x: self.show_notification_history()]
        else:
            self.toolbar.right_action_items[1] = ["bell-outline", lambda x: self.show_notification_history()]
    
    def send_context_update(self, dt=None):
        """Send current context to server for change detection."""
        app = App.get_running_app()
        
        if not app.user_id:
            return
        
        def _send():
            try:
                payload = {
                    "user_id": app.user_id,
                    "location": {
                        "latitude": app.latitude,
                        "longitude": app.longitude
                    },
                    "current_time": datetime.now().hour
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/api/context/update",
                    json=payload,
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Context updated: {data.get('notifications_generated', 0)} notifications")
                    
            except Exception as e:
                logger.error(f"Context update failed: {e}")
        
        threading.Thread(target=_send, daemon=True).start()

    def go_to_settings(self):
        """Navigate back to preference screen to change settings."""
        self.manager.transition.direction = 'right'
        self.manager.current = 'preferences'

    def refresh_data(self):
        app = App.get_running_app()
        
        if not app.user_id:
            def redirect_to_prefs(dt):
                self.manager.current = 'preferences'
            
            self.show_toast("Please sign in first")
            Clock.schedule_once(redirect_to_prefs, 1)
            return

        self.toolbar.title = "Updating..."
        threading.Thread(target=self.fetch_api_data, daemon=True).start()

    def fetch_api_data(self):
        app = App.get_running_app()
        
        payload = {
            "preferences": app.preferences,
            "location": {
                "latitude": app.latitude,
                "longitude": app.longitude
            }
        }
        
        try:
            response = requests.post(f"{API_BASE_URL}/api/recommendations", json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                Clock.schedule_once(lambda dt: self.update_ui(data), 0)
            else:
                err_msg = f"API Error {response.status_code}: {response.text}"
                Clock.schedule_once(lambda dt: self.show_error(err_msg), 0)
                
        except requests.exceptions.ConnectionError:
            Clock.schedule_once(lambda dt: self.show_error("Connection Refused.\nIs server.py running?"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(str(e)), 0)

    def update_ui(self, data):
        app = App.get_running_app()
        self.toolbar.title = "Explore Montreal"
        
        context = data.get("context", {})
        recs = data.get("recommendations", [])
        
        weather = context.get("weather", "Unknown").capitalize()
        temp = context.get("temperature", "N/A")
        period = context.get("time_period", "N/A")
        
        # Weather emoji
        weather_emoji = {"sunny": "☀️", "cloudy": "☁️", "rainy": "🌧️", "snowy": "❄️"}.get(context.get("weather", ""), "🌤️")
        
        self.context_label.text = f"{weather_emoji} {weather} ({temp}°C) | 🕐 {period}\n📍 {app.latitude:.4f}, {app.longitude:.4f}"
        
        self.recs_box.clear_widgets()
        
        if not recs:
            empty_card = ResponsiveCard(show_title=False)
            empty_card.add_widget(MDLabel(
                text="No recommendations found for this area/time.", 
                halign="center", 
                theme_text_color="Secondary",
                font_size=sp(14)
            ))
            self.recs_box.add_widget(empty_card)
            return
        
        for r in recs:
            card = self.create_recommendation_card(r)
            self.recs_box.add_widget(card)

    def create_recommendation_card(self, rec):
        """Create a responsive recommendation card."""
        # Responsive height based on content
        card_height = dp(120) if Window.width < 400 else dp(130)
        
        card = MDCard(
            orientation='vertical',
            padding=get_responsive_padding(),
            spacing=dp(5),
            size_hint_y=None,
            height=card_height,
            radius=[dp(10)],
            elevation=1,
            md_bg_color=(1, 1, 1, 1)
        )
        
        # Header row with name and rating
        header = MDBoxLayout(size_hint_y=None, height=dp(28))
        
        name = rec.get('name', 'Unknown')
        # Truncate name on small screens
        max_name_len = 25 if Window.width < 400 else 35
        if len(name) > max_name_len:
            name = name[:max_name_len] + "..."
        
        header.add_widget(MDLabel(
            text=name, 
            font_size=sp(15),
            bold=True,
            shorten=True,
            shorten_from='right'
        ))
        
        if rec.get('rating'):
            header.add_widget(MDLabel(
                text=f"⭐ {rec['rating']}", 
                halign='right', 
                theme_text_color="Secondary",
                size_hint_x=0.25,
                font_size=sp(13)
            ))
        card.add_widget(header)
        
        # Description
        desc = rec.get('description', '') or rec.get('type', '')
        card.add_widget(MDLabel(
            text=desc, 
            theme_text_color="Secondary", 
            font_size=sp(12),
            size_hint_y=None, 
            height=dp(18)
        ))
        
        # Reason
        reason = rec.get('reason', '')
        max_reason_len = 50 if Window.width < 400 else 70
        if len(reason) > max_reason_len:
            reason = reason[:max_reason_len] + "..."
        
        card.add_widget(MDLabel(
            text=f"💡 {reason}", 
            theme_text_color="Primary", 
            font_size=sp(11),
            size_hint_y=None, 
            height=dp(18)
        ))
        
        # Bottom row with distance and navigate button
        row = MDBoxLayout(size_hint_y=None, height=dp(35))
        dist = rec.get('distance', 0)
        if dist > 1000:
            dist_str = f"{dist/1000:.1f}km"
        else:
            dist_str = f"{dist}m"
            
        row.add_widget(MDLabel(
            text=f"📍 {dist_str}", 
            theme_text_color="Hint", 
            font_size=sp(12),
            valign='center'
        ))
        
        nav_btn = MDRectangleFlatButton(
            text="NAVIGATE", 
            font_size=sp(11),
            size_hint_x=None,
            width=dp(90)
        )
        row.add_widget(nav_btn)
        card.add_widget(row)
        
        return card

    def show_error(self, msg):
        self.toolbar.title = "Explore Montreal"
        self.show_toast(f"Error: {msg}")

    def show_notification_history(self):
        """Show notification history screen."""
        self.manager.transition.direction = 'left'
        self.manager.current = 'notifications'

    def show_toast(self, text):
        dialog = MDDialog(
            title="Info", 
            text=text, 
            buttons=[MDRectangleFlatButton(text="OK", on_release=lambda x: dialog.dismiss())]
        )
        dialog.open()


class NotificationHistoryScreen(MDScreen):
    """Responsive screen showing notification history."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Toolbar
        self.toolbar = MDTopAppBar(
            title="Notifications",
            elevation=4,
            left_action_items=[["arrow-left", lambda x: self.go_back()]],
            right_action_items=[["delete", lambda x: self.clear_notifications()]]
        )
        layout.add_widget(self.toolbar)
        
        # Notification List
        self.scroll = MDScrollView()
        self.list_container = MDBoxLayout(
            orientation='vertical',
            spacing=get_responsive_spacing(),
            padding=get_responsive_padding(),
            size_hint_y=None
        )
        self.list_container.bind(minimum_height=self.list_container.setter('height'))
        self.scroll.add_widget(self.list_container)
        layout.add_widget(self.scroll)
        
        self.add_widget(layout)
    
    def on_enter(self):
        """Refresh notification list when entering screen."""
        self.refresh_list()
    
    def refresh_list(self):
        """Populate the notification list."""
        self.list_container.clear_widgets()
        
        main_screen = self.manager.get_screen('main')
        notifications = main_screen.notification_history
        
        if not notifications:
            empty_card = ResponsiveCard(show_title=False)
            empty_card.add_widget(MDLabel(
                text="📭 No notifications yet",
                halign='center',
                font_size=sp(16),
                theme_text_color='Secondary'
            ))
            empty_card.add_widget(MDLabel(
                text="Context changes will appear here",
                halign='center',
                font_size=sp(12),
                theme_text_color='Hint'
            ))
            self.list_container.add_widget(empty_card)
            return
        
        # Emoji/icon mapping
        icon_map = {
            "location_change": "📍",
            "weather_change": "🌤️",
            "time_period_change": "🕐",
            "meal_time": "🍽️",
            "temperature_change": "🌡️",
            "preferences_updated": "⚙️",
            "connection_established": "✅",
        }
        
        # Color mapping
        color_map = {
            "location_change": (0.92, 0.96, 1, 1),
            "weather_change": (1, 0.97, 0.92, 1),
            "time_period_change": (0.96, 0.92, 1, 1),
            "meal_time": (0.92, 1, 0.94, 1),
            "temperature_change": (1, 0.94, 0.92, 1),
            "preferences_updated": (0.94, 0.97, 1, 1),
            "connection_established": (0.92, 1, 0.94, 1),
        }
        
        for notif in reversed(notifications):
            notif_type = notif.get('type', 'info')
            icon = icon_map.get(notif_type, "🔔")
            bg_color = color_map.get(notif_type, (0.96, 0.96, 0.96, 1))
            
            try:
                ts = datetime.fromisoformat(notif['timestamp'].replace('Z', '+00:00'))
                time_str = ts.strftime("%H:%M - %b %d")
            except:
                time_str = ""
            
            # Responsive card height
            card_height = dp(75) if Window.width < 400 else dp(85)
            
            card = MDCard(
                orientation='vertical',
                padding=get_responsive_padding(),
                spacing=dp(4),
                size_hint_y=None,
                height=card_height,
                radius=[dp(8)],
                md_bg_color=bg_color,
                elevation=1
            )
            
            # Header
            header = MDBoxLayout(size_hint_y=None, height=dp(22))
            header.add_widget(MDLabel(
                text=f"{icon}  {notif['title']}",
                font_size=sp(14),
                bold=True,
                theme_text_color='Primary'
            ))
            header.add_widget(MDLabel(
                text=time_str,
                font_size=sp(11),
                halign='right',
                theme_text_color='Hint',
                size_hint_x=0.35
            ))
            card.add_widget(header)
            
            # Message
            message = notif['message']
            max_msg_len = 60 if Window.width < 400 else 80
            if len(message) > max_msg_len:
                message = message[:max_msg_len] + "..."
            
            card.add_widget(MDLabel(
                text=message,
                font_size=sp(12),
                theme_text_color='Secondary',
                size_hint_y=None,
                height=dp(35)
            ))
            
            self.list_container.add_widget(card)
    
    def clear_notifications(self):
        """Clear all notifications."""
        main_screen = self.manager.get_screen('main')
        main_screen.notification_history = []
        main_screen.notification_count = 0
        main_screen.update_bell_icon()
        self.refresh_list()
        
        Snackbar(text="Notifications cleared").open()
    
    def go_back(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'main'


# --- 10. App Entry Point ---

class MontrealCompanionApp(MDApp):
    user_id = StringProperty(None)
    preferences = DictProperty({})
    latitude = NumericProperty(45.5017)
    longitude = NumericProperty(-73.5673)

    def build(self):
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.accent_palette = "Pink"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.material_style = "M3"

        sm = MDScreenManager()
        sm.add_widget(WelcomeScreen(name='welcome'))
        sm.add_widget(PreferencesScreen(name='preferences'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(NotificationHistoryScreen(name='notifications'))
        
        return sm

    def on_start(self):
        # Request permissions on Android
        if GPS_AVAILABLE:
            try:
                if platform == 'android':
                    request_permissions([Permission.ACCESS_FINE_LOCATION])
                gps.configure(on_location=self.on_gps_location)
                gps.start(minTime=10000, minDistance=10)
            except Exception as e:
                logging.warning(f"GPS Error: {e}")

    def on_gps_location(self, **kwargs):
        self.latitude = kwargs.get('lat', self.latitude)
        self.longitude = kwargs.get('lon', self.longitude)
    
    def on_stop(self):
        """Clean up when app closes."""
        try:
            main_screen = self.root.get_screen('main')
            if main_screen.notification_client:
                main_screen.notification_client.disconnect()
        except:
            pass


if __name__ == '__main__':
    MontrealCompanionApp().run()

