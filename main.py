"""
Montreal Travel Companion - Android App Client
Production UI with Real API Integration + WebSocket Notifications
"""

import os
import logging
import threading
import json
from datetime import datetime
import requests

# --- 1. Environment Configuration ---
#os.environ['KIVY_NO_CONSOLELOG'] = '0'

from kivy.config import Config
Config.set('kivy', 'log_level', 'info')
Config.set('kivy', 'keyboard_mode', 'systemanddock')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

# --- 2. Critical Font Fix (Robust Version) ---
from kivy.core.text import LabelBase
try:
    import kivymd
    base_path = os.path.dirname(kivymd.__file__)
    
    possible_paths = [
        os.path.join(base_path, 'fonts', 'materialdesignicons-webfont.ttf'), # KivyMD 1.2.0+
        os.path.join(base_path, 'fonts', 'MaterialIcons-Regular.ttf'),       # Older versions
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
from kivy.metrics import dp
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

Window.size = (400, 750)

# API URL
API_BASE_URL = "http://localhost:8000" 
WS_BASE_URL = "ws://localhost:8000"
# API_BASE_URL = "http://10.0.2.2:8000" # Uncomment for Android Emulator
# WS_BASE_URL = "ws://10.0.2.2:8000"    # Uncomment for Android Emulator


# --- 5. WebSocket Notification Client ---

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
        self.reconnect_delay = 3  # seconds
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
                
                # Run forever (blocking call)
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
            
            # Schedule UI update on main thread
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


# --- 6. UI Components ---

class CustomMDCard(MDCard):
    """Reusable Card Component with consistent styling."""
    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(15)
        self.spacing = dp(10)
        self.size_hint_y = None
        self.radius = [dp(16)]
        self.elevation = 2
        self.bind(minimum_height=self.setter('height'))
        self.md_bg_color = [1, 1, 1, 1]

        # Title
        self.add_widget(MDLabel(
            text=title,
            font_style='H6',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30),
            halign='left'
        ))


class NotificationBanner(MDCard):
    """A notification banner that appears at the top of the screen."""
    
    def __init__(self, title, message, notif_type="info", on_dismiss=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint = (0.95, None)
        self.height = dp(80)
        self.pos_hint = {'center_x': 0.5, 'top': 0.98}
        self.radius = [dp(12)]
        self.elevation = 4
        self.on_dismiss_callback = on_dismiss
        
        # Set color based on notification type
        type_colors = {
            "location_change": (0.2, 0.6, 0.9, 1),      # Blue
            "weather_change": (0.9, 0.7, 0.2, 1),       # Orange
            "time_period_change": (0.5, 0.3, 0.7, 1),   # Purple
            "meal_time": (0.3, 0.7, 0.4, 1),            # Green
            "temperature_change": (0.9, 0.4, 0.3, 1),   # Red
            "preferences_updated": (0.4, 0.7, 0.9, 1),  # Light Blue
            "connection_established": (0.3, 0.7, 0.4, 1), # Green
            "info": (0.5, 0.5, 0.5, 1),                 # Gray
        }
        self.md_bg_color = type_colors.get(notif_type, type_colors["info"])
        
        # Icon
        icon_map = {
            "location_change": "map-marker",
            "weather_change": "weather-cloudy",
            "time_period_change": "clock-outline",
            "meal_time": "food",
            "temperature_change": "thermometer",
            "preferences_updated": "cog",
            "connection_established": "check-circle",
        }
        icon_name = icon_map.get(notif_type, "bell")
        
        # Content layout
        content = MDBoxLayout(orientation='horizontal', padding=dp(10), spacing=dp(10))
        
        # Icon
        icon_label = MDLabel(
            text=icon_name,
            font_style="Icon",
            font_size=dp(28),
            size_hint_x=None,
            width=dp(40),
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            halign='center',
            valign='center'
        )
        content.add_widget(icon_label)
        
        # Text content
        text_box = MDBoxLayout(orientation='vertical', spacing=dp(2))
        text_box.add_widget(MDLabel(
            text=title,
            font_style='Subtitle1',
            bold=True,
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(25)
        ))
        text_box.add_widget(MDLabel(
            text=message[:80] + "..." if len(message) > 80 else message,
            font_style='Caption',
            theme_text_color='Custom',
            text_color=(1, 1, 1, 0.9),
            size_hint_y=None,
            height=dp(35)
        ))
        content.add_widget(text_box)
        
        # Close button
        close_btn = MDIconButton(
            icon="close",
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            size_hint_x=None,
            width=dp(40),
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


class WelcomeScreen(MDScreen):
    """Landing screen with branding."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        layout = MDBoxLayout(
            orientation='vertical',
            padding=dp(30),
            spacing=dp(30),
            md_bg_color=(0.2, 0.2, 0.8, 1)
        )
        Clock.schedule_once(lambda x: setattr(layout, 'md_bg_color', MDApp.get_running_app().theme_cls.primary_color), 0)

        layout.add_widget(MDWidget(size_hint_y=0.2))

        layout.add_widget(MDLabel(
            text='map-search',
            font_style="Icon",
            halign='center',
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            font_size=dp(90),
            size_hint_y=None,
            height=dp(100)
        ))
        
        layout.add_widget(MDLabel(
            text='Montreal\nTravel Companion',
            font_style='H4',
            bold=True,
            halign='center',
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(100)
        ))
        
        layout.add_widget(MDWidget(size_hint_y=0.2))
        
        btn = MDRaisedButton(
            text='START EXPLORING',
            font_size=dp(18),
            size_hint_x=0.8,
            pos_hint={'center_x': 0.5},
            elevation=4,
            on_release=self.go_to_preferences
        )
        Clock.schedule_once(lambda x: setattr(btn, 'md_bg_color', MDApp.get_running_app().theme_cls.accent_color), 0)
        
        layout.add_widget(btn)
        layout.add_widget(MDWidget())
        self.add_widget(layout)

    def go_to_preferences(self, instance):
        self.manager.transition.direction = 'left'
        self.manager.current = 'preferences'


class PreferencesScreen(MDScreen):
    """User Preference Input Screen."""
    activity_type = StringProperty("outdoor")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical')
        
        self.toolbar = MDTopAppBar(
            title="Your Preferences",
            elevation=4,
            pos_hint={"top": 1},
            left_action_items=[["arrow-left", lambda x: self.go_back()]]
        )
        layout.add_widget(self.toolbar)
        
        scroll = MDScrollView()
        content = MDBoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20), size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        
        # 1. User ID
        card_id = CustomMDCard(title="Profile")
        self.user_id_input = MDTextField(
            hint_text="User ID (e.g., traveler1)",
            mode="rectangle",
            text="traveler1"
        )
        card_id.add_widget(self.user_id_input)
        content.add_widget(card_id)
        
        # 2. Meal Times
        card_meals = CustomMDCard(title="Meal Times (HH:MM)")
        meals_grid = MDGridLayout(cols=3, spacing=dp(10), size_hint_y=None)
        meals_grid.bind(minimum_height=meals_grid.setter('height'))

        # Create inputs for Breakfast, Lunch, Dinner
        self.input_breakfast = MDTextField(
            text="08:00", hint_text="Breakfast", mode="rectangle", size_hint_x=0.3
        )
        self.input_lunch = MDTextField(
            text="12:00", hint_text="Lunch", mode="rectangle", size_hint_x=0.3
        )
        self.input_dinner = MDTextField(
            text="19:00", hint_text="Dinner", mode="rectangle", size_hint_x=0.3
        )

        meals_grid.add_widget(self.input_breakfast)
        meals_grid.add_widget(self.input_lunch)
        meals_grid.add_widget(self.input_dinner)
        
        card_meals.add_widget(meals_grid)
        content.add_widget(card_meals)

        # 3. Activity Type
        card_act = CustomMDCard(title="Preferred Vibe")
        btn_box = MDBoxLayout(spacing=dp(10), size_hint_y=None, height=dp(50))
        
        self.btn_indoor = MDRectangleFlatButton(text="Indoor", on_release=lambda x: self.set_activity("indoor"))
        self.btn_outdoor = MDRaisedButton(text="Outdoor", on_release=lambda x: self.set_activity("outdoor"))
        
        btn_box.add_widget(self.btn_indoor)
        btn_box.add_widget(self.btn_outdoor)
        card_act.add_widget(btn_box)
        content.add_widget(card_act)
        
        # 4. Cuisines
        card_food = CustomMDCard(title="Cuisines")
        self.cuisines = ['Italian', 'French', 'Japanese', 'Mexican', 'Burgers', 'Cafe', 'Seafood']
        self.cuisine_checks = {}
        
        grid = MDGridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        for c in self.cuisines:
            row = MDBoxLayout(size_hint_y=None, height=dp(40))
            chk = MDCheckbox(size_hint=(None, None), size=(dp(40), dp(40)))
            if c == 'French': chk.active = True
            self.cuisine_checks[c] = chk
            row.add_widget(chk)
            row.add_widget(MDLabel(text=c, theme_text_color="Primary"))
            grid.add_widget(row)
            
        card_food.add_widget(grid)
        content.add_widget(card_food)
        
        # Save Button
        save_btn = MDRaisedButton(
            text="SAVE & CONTINUE",
            size_hint_x=1,
            height=dp(50),
            md_bg_color=(0, 0.7, 0, 1),
            on_release=self.save_prefs_thread
        )
        content.add_widget(save_btn)
        content.add_widget(MDWidget(size_hint_y=None, height=dp(50)))
        
        scroll.add_widget(content)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def set_activity(self, mode):
        self.activity_type = mode
        theme = MDApp.get_running_app().theme_cls
        if mode == "indoor":
            self.btn_indoor.md_bg_color = theme.primary_color
            self.btn_indoor.text_color = (1, 1, 1, 1)
            self.btn_outdoor.md_bg_color = (0,0,0,0)
            self.btn_outdoor.text_color = theme.primary_color
        else:
            self.btn_outdoor.md_bg_color = theme.primary_color
            self.btn_outdoor.text_color = (1, 1, 1, 1)
            self.btn_indoor.md_bg_color = (0,0,0,0)
            self.btn_indoor.text_color = theme.primary_color

    def go_back(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'welcome'

    def save_prefs_thread(self, instance):
        if not self.user_id_input.text.strip():
            MDDialog(title="Error", text="User ID cannot be empty", buttons=[MDRectangleFlatButton(text="OK", on_release=lambda x: x.parent.parent.dismiss())]).open()
            return
        
        self.show_loading()
        threading.Thread(target=self.save_prefs_api, daemon=True).start()

    def save_prefs_api(self):
        user_id = self.user_id_input.text.strip()
        
        # Validate time format (Basic check)
        meal_times = {
            "breakfast": self.input_breakfast.text.strip(),
            "lunch": self.input_lunch.text.strip(),
            "dinner": self.input_dinner.text.strip()
        }
        
        # Construct payload
        payload = {
            "user_id": user_id,
            "activity_type": self.activity_type,
            "preferred_cuisines": [k for k, v in self.cuisine_checks.items() if v.active],
            "meal_times": meal_times
        }
        
        app = App.get_running_app()
        app.user_id = user_id
        app.preferences = payload # Store locally
        
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
    """Dashboard showing Context and Recommendations with Real-Time Notifications."""
    
    notification_count = NumericProperty(0)
    ws_connected = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.notification_client = None
        self.current_banner = None
        self.notification_history = []
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Header with Notification Badge
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
            height=dp(30),
            md_bg_color=(0.9, 0.9, 0.9, 1),
            padding=(dp(10), 0)
        )
        self.status_label = MDLabel(
            text="● Disconnected",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=(0.7, 0.2, 0.2, 1),
            valign='center'
        )
        self.status_bar.add_widget(self.status_label)
        layout.add_widget(self.status_bar)
        
        # Content
        self.scroll = MDScrollView()
        self.content = MDBoxLayout(orientation='vertical', spacing=dp(15), padding=dp(15), size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter('height'))
        
        # Context Card
        self.context_card = CustomMDCard(title="Current Vibe")
        self.context_label = MDLabel(text="Loading context...", theme_text_color="Secondary", size_hint_y=None, height=dp(60))
        self.context_card.add_widget(self.context_label)
        self.content.add_widget(self.context_card)
        
        # Recs Label
        self.content.add_widget(MDLabel(text="Recommended for You", font_style="H6", size_hint_y=None, height=dp(40)))
        
        # Recs Container
        self.recs_box = MDBoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None)
        self.recs_box.bind(minimum_height=self.recs_box.setter('height'))
        self.content.add_widget(self.recs_box)
        
        self.scroll.add_widget(self.content)
        layout.add_widget(self.scroll)
        self.add_widget(layout)

    def on_enter(self):
        """Called when screen is displayed."""
        app = App.get_running_app()
        
        # Start WebSocket connection if not already connected
        if app.user_id and WEBSOCKET_AVAILABLE:
            self.start_notification_client()
        
        # Start periodic context updates (for location/time changes)
        self.context_update_event = Clock.schedule_interval(self.send_context_update, 60)  # Every 60 seconds
        
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
            self.status_label.text = "● Connected (Live Updates)"
            self.status_label.text_color = (0.2, 0.7, 0.2, 1)
            self.status_bar.md_bg_color = (0.9, 1, 0.9, 1)
        else:
            self.status_label.text = "● Disconnected"
            self.status_label.text_color = (0.7, 0.2, 0.2, 1)
            self.status_bar.md_bg_color = (1, 0.9, 0.9, 1)
    
    def handle_notification(self, notification):
        """Handle incoming notification from WebSocket."""
        notif_type = notification.get('type', 'info')
        title = notification.get('title', 'Notification')
        message = notification.get('message', '')
        
        logger.info(f"Handling notification: {title}")
        
        # Store in history
        self.notification_history.append({
            'type': notif_type,
            'title': title,
            'message': message,
            'timestamp': notification.get('timestamp', datetime.now().isoformat())
        })
        
        # Keep only last 50 notifications
        if len(self.notification_history) > 50:
            self.notification_history = self.notification_history[-50:]
        
        # Update notification count
        self.notification_count = len(self.notification_history)
        self.update_bell_icon()
        
        # Show banner notification (except for connection established)
        if notif_type != 'connection_established' and notif_type != 'pong':
            self.show_notification_banner(title, message, notif_type)
            
            # Auto-refresh recommendations for certain notification types
            if notif_type in ['location_change', 'weather_change', 'preferences_updated', 'meal_time']:
                Clock.schedule_once(lambda dt: self.refresh_data(), 1)
    
    def show_notification_banner(self, title, message, notif_type="info"):
        """Display a notification banner at the top of the screen."""
        # Remove existing banner if any
        if self.current_banner and self.current_banner.parent:
            self.current_banner.parent.remove_widget(self.current_banner)
        
        # Create new banner
        self.current_banner = NotificationBanner(
            title=title,
            message=message,
            notif_type=notif_type,
            on_dismiss=lambda: setattr(self, 'current_banner', None)
        )
        
        # Add to screen
        self.add_widget(self.current_banner)
        
        # Auto-dismiss after 5 seconds
        Clock.schedule_once(lambda dt: self.current_banner.dismiss() if self.current_banner else None, 5)
    
    def update_bell_icon(self):
        """Update the bell icon to show notification count."""
        if self.notification_count > 0:
            # Change to filled bell with badge effect
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
                    # Notifications will be delivered via WebSocket
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
        
        # Redirect if no user_id
        if not app.user_id:
            def redirect_to_prefs(dt):
                self.manager.current = 'preferences'
            
            self.show_toast("Please sign in first")
            Clock.schedule_once(redirect_to_prefs, 1)
            return

        # Threading for API to prevent UI freeze
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
        
        self.context_label.text = f"{weather} ({temp}°C) | {period}\nLocation: {app.latitude:.3f}, {app.longitude:.3f}"
        
        self.recs_box.clear_widgets()
        
        if not recs:
             self.recs_box.add_widget(MDLabel(text="No recommendations found for this area/time.", halign="center", theme_text_color="Secondary"))
        
        for r in recs:
            card = MDCard(
                orientation='vertical',
                padding=dp(15),
                spacing=dp(5),
                size_hint_y=None,
                height=dp(140),
                radius=[dp(10)],
                elevation=1
            )
            
            header = MDBoxLayout(size_hint_y=None, height=dp(30))
            header.add_widget(MDLabel(text=r.get('name', 'Unknown'), font_style="Subtitle1", bold=True))
            if r.get('rating'):
                header.add_widget(MDLabel(text=f"⭐ {r['rating']}", halign='right', theme_text_color="Secondary"))
            card.add_widget(header)
            
            desc = r.get('description', '')
            if not desc: desc = r.get('type', '')
            card.add_widget(MDLabel(text=desc, theme_text_color="Secondary", font_style="Caption", size_hint_y=None, height=dp(20)))
            
            card.add_widget(MDLabel(text=f"💡 {r.get('reason', '')}", theme_text_color="Primary", font_style="Caption", size_hint_y=None, height=dp(20)))
            
            row = MDBoxLayout(size_hint_y=None, height=dp(40))
            dist = r.get('distance', 0)
            if dist > 1000:
                dist_str = f"{dist/1000:.1f}km"
            else:
                dist_str = f"{dist}m"
                
            row.add_widget(MDLabel(text=f"📍 {dist_str}", theme_text_color="Hint", font_style="Caption", valign='center'))
            row.add_widget(MDRectangleFlatButton(text="NAVIGATE", line_color=MDApp.get_running_app().theme_cls.primary_color))
            card.add_widget(row)
            
            self.recs_box.add_widget(card)

    def show_error(self, msg):
        self.toolbar.title = "Explore Montreal"
        self.show_toast(f"Error: {msg}")

    def show_notification_history(self):
        """Show notification history screen."""
        self.manager.transition.direction = 'left'
        self.manager.current = 'notifications'

    def show_toast(self, text):
        d = MDDialog(title="Info", text=text, buttons=[MDRectangleFlatButton(text="OK", on_release=lambda x: d.dismiss())])
        d.open()


class NotificationHistoryScreen(MDScreen):
    """Screen showing notification history."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
            spacing=dp(5),
            padding=dp(10),
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
        
        # Get notifications from MainScreen
        main_screen = self.manager.get_screen('main')
        notifications = main_screen.notification_history
        
        if not notifications:
            empty_card = MDCard(
                orientation='vertical',
                padding=dp(20),
                size_hint_y=None,
                height=dp(100),
                radius=[dp(10)]
            )
            empty_card.add_widget(MDLabel(
                text="No notifications yet",
                halign='center',
                theme_text_color='Secondary',
                font_style='H6'
            ))
            empty_card.add_widget(MDLabel(
                text="Context changes will appear here",
                halign='center',
                theme_text_color='Hint',
                font_style='Caption'
            ))
            self.list_container.add_widget(empty_card)
            return
        
        # Emoji/icon mapping for notification types
        icon_map = {
            "location_change": "📍",
            "weather_change": "🌤️",
            "time_period_change": "🕐",
            "meal_time": "🍽️",
            "temperature_change": "🌡️",
            "preferences_updated": "⚙️",
            "connection_established": "✅",
        }
        
        # Color mapping for notification types
        color_map = {
            "location_change": (0.9, 0.95, 1, 1),      # Light Blue
            "weather_change": (1, 0.97, 0.9, 1),       # Light Orange
            "time_period_change": (0.95, 0.9, 1, 1),   # Light Purple
            "meal_time": (0.9, 1, 0.92, 1),            # Light Green
            "temperature_change": (1, 0.92, 0.9, 1),   # Light Red
            "preferences_updated": (0.92, 0.97, 1, 1), # Light Blue
            "connection_established": (0.9, 1, 0.92, 1), # Light Green
        }
        
        # Show notifications in reverse order (newest first)
        for notif in reversed(notifications):
            notif_type = notif.get('type', 'info')
            icon = icon_map.get(notif_type, "🔔")
            bg_color = color_map.get(notif_type, (0.95, 0.95, 0.95, 1))
            
            # Parse timestamp
            try:
                ts = datetime.fromisoformat(notif['timestamp'].replace('Z', '+00:00'))
                time_str = ts.strftime("%H:%M - %b %d")
            except:
                time_str = ""
            
            # Create notification card
            card = MDCard(
                orientation='vertical',
                padding=dp(12),
                spacing=dp(5),
                size_hint_y=None,
                height=dp(90),
                radius=[dp(8)],
                md_bg_color=bg_color,
                elevation=1
            )
            
            # Header row with icon and title
            header = MDBoxLayout(size_hint_y=None, height=dp(25))
            header.add_widget(MDLabel(
                text=f"{icon}  {notif['title']}",
                font_style='Subtitle1',
                bold=True,
                theme_text_color='Primary'
            ))
            header.add_widget(MDLabel(
                text=time_str,
                font_style='Caption',
                halign='right',
                theme_text_color='Hint',
                size_hint_x=0.4
            ))
            card.add_widget(header)
            
            # Message
            message = notif['message']
            if len(message) > 80:
                message = message[:80] + "..."
            card.add_widget(MDLabel(
                text=message,
                font_style='Body2',
                theme_text_color='Secondary',
                size_hint_y=None,
                height=dp(40)
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


# --- 7. App Entry Point ---

class MontrealCompanionApp(MDApp):
    user_id = StringProperty(None)
    preferences = DictProperty({})
    latitude = NumericProperty(45.5017)  # Default Montreal Lat
    longitude = NumericProperty(-73.5673)  # Default Montreal Lon

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
        # Disconnect WebSocket
        try:
            main_screen = self.root.get_screen('main')
            if main_screen.notification_client:
                main_screen.notification_client.disconnect()
        except:
            pass


if __name__ == '__main__':
    MontrealCompanionApp().run()
